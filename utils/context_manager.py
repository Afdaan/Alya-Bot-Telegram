"""
Context Management for Alya Bot.

This module handles storage and retrieval of conversation context
to enable more natural and continuous conversations.
"""

import sqlite3
import json
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union
import os
from pathlib import Path
from datetime import datetime, timedelta
import re

from config.settings import (
    CONTEXT_TTL,
    CONTEXT_DB_PATH,
    CONTEXT_MAX_HISTORY,
    MEMORY_IMPORTANCE_THRESHOLD,
    PERSONAL_FACTS_TTL,
    MEMORY_MAX_TOKENS
)

from utils.database import get_connection, init_database

logger = logging.getLogger(__name__)

class ContextManager:
    """Manager for conversation context persistence."""
    
    def __init__(self, db_path: str = CONTEXT_DB_PATH):
        """Initialize the context manager with a database path."""
        self.db_path = db_path
        self._ensure_db()
        
    def _ensure_db(self):
        """Ensure database and required tables exist."""
        # Use the init_database function from database.py
        init_database()
        
    def _get_connection(self):
        """Get a connection to the SQLite database."""
        return get_connection()
    
    def get_context(self, user_id: int, chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the context for a user in a specific chat.
        
        Args:
            user_id: Telegram user ID
            chat_id: Optional chat ID for group chat contexts
            
        Returns:
            User context dictionary or empty dict if none exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Ensure IDs are integers
            user_id = int(user_id)
            chat_id = int(chat_id) if chat_id is not None else user_id
            
            cursor.execute(
                "SELECT context FROM contexts WHERE user_id=? AND chat_id=?", 
                (user_id, chat_id)
            )
            
            result = cursor.fetchone()
            
            if result:
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in context for user {user_id}")
                    return {}
            return {}
        except sqlite3.Error as e:
            logger.error(f"SQLite error in get_context: {e}, user_id: {user_id}, chat_id: {chat_id}")
            return {}
        finally:
            conn.close()
    
    def set_context(self, user_id: int, context: Dict[str, Any], chat_id: Optional[int] = None) -> None:
        """
        Set the context for a user in a specific chat.
        
        Args:
            user_id: Telegram user ID
            context: Context dictionary to store
            chat_id: Optional chat ID for group chat contexts
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Ensure IDs are integers - this is the critical fix for datatype mismatch
            user_id = int(user_id)
            chat_id = int(chat_id) if chat_id is not None else user_id
            
            # Validate and sanitize context before serialization
            try:
                # Ensure context is a dictionary
                if not isinstance(context, dict):
                    context = {"data": str(context)}
                    
                # Try serialization for early problem detection
                json_context = json.dumps(context)
            except (TypeError, OverflowError, ValueError) as e:
                logger.error(f"Context serialization error: {e}, cleaning context")
                # Clean non-serializable objects
                cleaned_context = {}
                for k, v in context.items():
                    try:
                        # Test serialization per key
                        json.dumps({k: v})
                        cleaned_context[k] = v
                    except (TypeError, OverflowError, ValueError):
                        # Convert problematic values to strings
                        cleaned_context[k] = str(v)
                json_context = json.dumps(cleaned_context)
            
            # Execute query with integer IDs
            cursor.execute(
                "INSERT OR REPLACE INTO contexts (user_id, chat_id, context, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, chat_id, json_context, int(time.time()))
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"SQLite error in set_context: {e}, user_id: {user_id}, chat_id: {chat_id}")
        finally:
            conn.close()
    
    def add_message_to_history(self, 
                              user_id: int, 
                              role: str, 
                              content: str,
                              chat_id: Optional[int] = None,
                              message_id: Optional[int] = None,
                              importance: float = 1.0, 
                              metadata: Optional[Dict] = None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            user_id: Telegram user ID
            role: Message role (user/assistant)
            content: Message content
            chat_id: Optional chat ID for group chat contexts
            message_id: Optional message ID from Telegram
            importance: Importance score (higher = more important to remember)
            metadata: Additional message metadata
        """
        token_count = self._estimate_token_count(content)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Store message in history
        cursor.execute(
            """INSERT INTO history 
               (user_id, chat_id, message_id, role, content, timestamp, importance, token_count, metadata) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                chat_id,
                message_id, 
                role, 
                content, 
                int(time.time()),
                importance, 
                token_count,
                json.dumps(metadata or {})
            )
        )
        conn.commit()
        
        # Check if we have exceeded the max history and need to prune
        self._prune_history_if_needed(user_id, cursor)
        
        conn.close()
    
    def add_chat_message(self, user_id: int, chat_id: Optional[int], message_id: Optional[int], 
                        role: str, content: str, importance: float = 1.0,
                        metadata: Optional[Dict] = None) -> None:
        """
        Add a message to chat history (alias for add_message_to_history).
        
        Args:
            user_id: Telegram user ID
            chat_id: Chat ID for group chats
            message_id: Message ID
            role: Message role (user/assistant)
            content: Message content
            importance: Importance score (higher = more important to remember)
            metadata: Additional message metadata
        """
        # Call the main implementation
        self.add_message_to_history(
            user_id=user_id,
            role=role,
            content=content,
            chat_id=chat_id,
            message_id=message_id,
            importance=importance,
            metadata=metadata
        )
    
    def _prune_history_if_needed(self, user_id: int, cursor) -> None:
        """
        Prune history if it exceeds the maximum allowed size.
        Keeps more important messages longer.
        
        Args:
            user_id: Telegram user ID
            cursor: Database cursor
        """
        # Get total token count
        cursor.execute(
            "SELECT COUNT(*), SUM(token_count) FROM history WHERE user_id=?", 
            (user_id,)
        )
        count, total_tokens = cursor.fetchone()
        
        # If we have a valid count and exceeded max tokens
        if count and total_tokens and total_tokens > MEMORY_MAX_TOKENS:
            # Get oldest, least important messages first (balanced by importance)
            cursor.execute(
                """SELECT id FROM history 
                   WHERE user_id=? 
                   ORDER BY importance ASC, timestamp ASC""",
                (user_id,)
            )
            
            # Delete messages until we're under the token limit
            rows_to_delete = []
            deleted_tokens = 0
            target_tokens = total_tokens - MEMORY_MAX_TOKENS + (MEMORY_MAX_TOKENS * 0.2)  # Delete extra 20% for buffer
            
            for row in cursor.fetchall():
                cursor.execute("SELECT token_count FROM history WHERE id=?", (row[0],))
                token_count = cursor.fetchone()[0]
                rows_to_delete.append(row[0])
                deleted_tokens += token_count
                if deleted_tokens >= target_tokens:
                    break
            
            # Delete the selected messages
            if rows_to_delete:
                placeholders = ', '.join('?' for _ in rows_to_delete)
                cursor.execute(
                    f"DELETE FROM history WHERE id IN ({placeholders})",
                    rows_to_delete
                )
                logger.info(f"Pruned {len(rows_to_delete)} messages for user {user_id}, freed {deleted_tokens} tokens")
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a piece of text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        # Very simple estimation: ~4 chars per token on average
        # For a more accurate count, you'd use the actual tokenizer
        if not text:
            return 0
        return len(text) // 4 + 1
    
    def get_conversation_history(self, 
                               user_id: int, 
                               limit: int = CONTEXT_MAX_HISTORY,
                               include_metadata: bool = False) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for a user.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to retrieve
            include_metadata: Whether to include message metadata
            
        Returns:
            List of message dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if include_metadata:
            cursor.execute(
                """SELECT role, content, timestamp, importance, metadata 
                   FROM history 
                   WHERE user_id=? 
                   ORDER BY timestamp DESC LIMIT ?""",
                (user_id, limit)
            )
            messages = [
                {
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "importance": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {}
                }
                for row in cursor.fetchall()
            ]
        else:
            cursor.execute(
                """SELECT role, content 
                   FROM history 
                   WHERE user_id=? 
                   ORDER BY timestamp DESC LIMIT ?""",
                (user_id, limit)
            )
            messages = [
                {
                    "role": row[0],
                    "content": row[1]
                }
                for row in cursor.fetchall()
            ]
        
        conn.close()
        
        # Return in chronological order (oldest first)
        return list(reversed(messages))
    
    def get_chat_history(self, user_id: int, chat_id: int, limit: int = CONTEXT_MAX_HISTORY) -> List[Dict[str, Any]]:
        """
        Get chat history specific to a chat, filtering out messages that should not be referenced.
        
        Args:
            user_id: Telegram user ID
            chat_id: Chat ID for group chat contexts
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of chat message dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Improved query with better filters for roast and messages to ignore
        query = """
            SELECT role, content
            FROM history 
            WHERE user_id=? AND chat_id=? 
            AND (
                metadata IS NULL 
                OR JSON_EXTRACT(metadata, '$.type') != 'roast'
                AND JSON_EXTRACT(metadata, '$.do_not_reference') IS NOT 'true'
                AND JSON_EXTRACT(metadata, '$.ignore_in_memory') IS NOT 'true'
            )
            ORDER BY timestamp DESC LIMIT ?
        """
        
        try:
            cursor.execute(query, (user_id, chat_id, limit))
            
            messages = [
                {
                    "role": row[0],
                    "content": row[1]
                }
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
        except sqlite3.Error as e:
            # SQLite might not support JSON_EXTRACT, fall back to simpler filter
            logger.warning(f"Advanced SQLite filtering failed: {e}, using fallback")
            
            # Fallback to simpler filtering
            cursor.execute(
                """SELECT role, content, metadata
                   FROM history 
                   WHERE user_id=? AND chat_id=?
                   ORDER BY timestamp DESC LIMIT ?""",
                (user_id, chat_id, limit * 2)  # Get more results then filter
            )
            
            # Filter in Python code instead
            filtered_messages = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row[2]) if row[2] else {}
                    if (metadata.get("type") != "roast" and
                        not metadata.get("do_not_reference") and
                        not metadata.get("ignore_in_memory")):
                        filtered_messages.append({
                            "role": row[0],
                            "content": row[1]
                        })
                        if len(filtered_messages) >= limit:
                            break
                except (json.JSONDecodeError, TypeError):
                    # If metadata can't be parsed, include the message
                    filtered_messages.append({
                        "role": row[0],
                        "content": row[1]
                    })
                    if len(filtered_messages) >= limit:
                        break
            
            conn.close()
            
            # Return in chronological order (oldest first)
            return list(reversed(filtered_messages[:limit]))
    
    def search_memory(self, 
                     user_id: int, 
                     query: str, 
                     limit: int = 5, 
                     min_importance: float = MEMORY_IMPORTANCE_THRESHOLD) -> List[Dict[str, Any]]:
        """
        Search user's memory for relevant messages.
        
        Args:
            user_id: Telegram user ID
            query: Search query
            limit: Maximum number of results
            min_importance: Minimum importance threshold
            
        Returns:
            List of relevant messages
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Extract keywords (3+ letter words)
        keywords = re.findall(r'\b\w{3,}\b', query)
        if not keywords:
            # If no substantial keywords, return recent important messages
            cursor.execute(
                """SELECT role, content, timestamp 
                   FROM history 
                   WHERE user_id=? AND importance >= ? 
                   ORDER BY timestamp DESC LIMIT ?""",
                (user_id, min_importance, limit)
            )
        else:
            # Build query with keywords
            like_conditions = []
            params = []
            for keyword in keywords:
                like_conditions.append("LOWER(content) LIKE ?")
                params.append(f"%{keyword}%")
            
            # Add user_id and importance threshold
            where_clause = " OR ".join(like_conditions)
            params = [user_id, min_importance] + params
            query = f"""
                SELECT role, content, timestamp 
                FROM history 
                WHERE user_id=? AND importance >= ? AND ({where_clause})
                ORDER BY timestamp DESC LIMIT ?
            """
            params.append(limit)
            cursor.execute(query, params)
        
        results = [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": datetime.fromtimestamp(row[2]).strftime("%Y-%m-%d %H:%M:%S")
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return results
    
    def extract_and_store_personal_facts(self, user_id: int, messages: List[Dict[str, str]]) -> None:
        """
        Extract and store personal facts from conversation.
        
        Args:
            user_id: Telegram user ID
            messages: Recent conversation messages
        """
        # This would ideally use NLP to extract facts, but for simplicity,
        # we'll just look for simple patterns like "Nama saya X", "Saya suka Y"
        fact_patterns = [
            (r"(?:nama\s(?:saya|aku|gw|gue))[^\w]+([\w\s]+)", "name"),
            (r"(?:umur\s(?:saya|aku|gw|gue))[^\w]+(\d+)", "age"),
            (r"(?:(?:saya|aku|gw|gue)\s(?:suka|senang|hobi))[^\w]+([\w\s]+)", "likes"),
            (r"(?:(?:saya|aku|gw|gue)\s(?:dari|tinggal))[^\w]+([\w\s]+)", "location")
        ]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for message in messages:
            if message["role"] != "user":
                continue
            content = message["content"].lower()
            
            for pattern, fact_key in fact_patterns:
                matches = re.search(pattern, content, re.IGNORECASE)
                if matches:
                    fact_value = matches.group(1).strip()
                    confidence = 0.8  # Simple confidence score
                    # Store or update the fact
                    cursor.execute(
                        """INSERT OR REPLACE INTO personal_facts 
                           (user_id, fact_key, fact_value, confidence, source, created_at, expires_at) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            user_id, 
                            fact_key, 
                            fact_value,
                            confidence, 
                            "conversation", 
                            int(time.time()),
                            int(time.time()) + PERSONAL_FACTS_TTL
                        )
                    )
        
        conn.commit()
        conn.close()
    
    def get_personal_facts(self, user_id: int) -> Dict[str, str]:
        """
        Get stored personal facts about a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary of fact_key: fact_value
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        current_time = int(time.time())
        cursor.execute(
            """SELECT fact_key, fact_value 
               FROM personal_facts 
               WHERE user_id=? AND expires_at > ?
               ORDER BY confidence DESC""",
            (user_id, current_time)
        )
        facts = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return facts
        
    def recall_relevant_context(self, user_id: int, current_message: str, chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Recall relevant context based on the current message.
        
        Args:
            user_id: Telegram user ID
            current_message: Current message content
            chat_id: Optional chat ID for group chat contexts
            
        Returns:
            Dictionary with context information
        """
        # Get recent conversation history
        history = self.get_conversation_history(user_id, limit=CONTEXT_MAX_HISTORY)
        
        # If chat_id is provided, also get chat-specific history
        if chat_id is not None:
            chat_history = self.get_chat_history(user_id, chat_id, limit=CONTEXT_MAX_HISTORY)
            # Merge histories, prioritizing chat-specific messages
            if chat_history:
                history = chat_history
        
        # Check if we should reset memory state (after roast)
        memory_state = self.get_context(user_id, chat_id).get('memory_state', {})
        if memory_state.get('should_reset_memory_state') and (time.time() - memory_state.get('timestamp', 0) < 60):
            # Clear the reset flag
            memory_state['should_reset_memory_state'] = False
            self.save_context(user_id, chat_id, 'memory_state', memory_state)
            
            # Add a note to history to help model transition
            history.append({
                "role": "system",
                "content": "Note: Previous conversation was a roast sequence. Please ignore it and start fresh."
            })
        
        # Get personal facts
        personal_facts = self.get_personal_facts(user_id)
        
        # Find relevant past messages based on the current message
        relevant_messages = self.search_memory(user_id, current_message)
        
        # Format the context for the AI
        context = {
            "history": history,
            "personal_facts": personal_facts,
            "relevant_past": relevant_messages
        }
        
        # Extract and store new facts from conversation
        self.extract_and_store_personal_facts(user_id, history)
        
        return context
        
    def mark_message_important(self, user_id: int, query: str, importance: float = 2.0) -> bool:
        """
        Mark a message as important for better recall.
        
        Args:
            user_id: Telegram user ID
            query: Text to match in message content
            importance: Importance score multiplier
            
        Returns:
            True if message was found and marked, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Find message with partial content match
        cursor.execute(
            "SELECT id, importance FROM history WHERE user_id=? AND content LIKE ? ORDER BY timestamp DESC LIMIT 1",
            (user_id, f"%{query}%")
        )
        result = cursor.fetchone()
        
        if result:
            message_id, current_importance = result
            new_importance = min(5.0, current_importance * importance)  # Cap at 5.0
            cursor.execute(
                "UPDATE history SET importance=? WHERE id=?",
                (new_importance, message_id)
            )
            conn.commit()
            conn.close()
            return True
            
        conn.close()
        return False
    
    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Clean up expired context entries and low-importance history.
        
        Returns:
            Tuple containing (context_count, history_count) of removed items
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Clean up outdated contexts (older than TTL)
            expiry_time = int(time.time()) - CONTEXT_TTL
            cursor.execute("DELETE FROM contexts WHERE updated_at < ?", (expiry_time,))
            context_count = cursor.rowcount
            
            # Clean up outdated personal facts
            current_time = int(time.time())
            cursor.execute("DELETE FROM personal_facts WHERE expires_at < ?", (current_time,))
            
            # Clean up history based on importance and age
            # Keep important messages longer, delete unimportant old ones
            three_months_ago = int(time.time()) - (90 * 24 * 60 * 60)
            one_month_ago = int(time.time()) - (30 * 24 * 60 * 60)
            one_week_ago = int(time.time()) - (7 * 24 * 60 * 60)
            
            # Execute cleanup queries with proper error handling
            try:
                # Delete old, unimportant messages completely
                cursor.execute(
                    "DELETE FROM history WHERE timestamp < ? AND importance < 0.8",
                    (three_months_ago,)
                )
                
                # Delete medium-aged, low importance messages
                cursor.execute(
                    "DELETE FROM history WHERE timestamp < ? AND importance < 1.2",
                    (one_month_ago,)
                )
                
                # Delete recent, very low importance messages
                cursor.execute(
                    "DELETE FROM history WHERE timestamp < ? AND importance < 0.5",
                    (one_week_ago,)
                )
                
                history_count = cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Error during history cleanup: {e}")
                history_count = 0
                
            conn.commit()
            return context_count, history_count
        except sqlite3.Error as e:
            logger.error(f"Database error in cleanup_expired: {e}")
            return 0, 0
        finally:
            conn.close()
    
    def get_memory_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about a user's memory.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with memory statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get message counts
        cursor.execute(
            "SELECT COUNT(*) FROM history WHERE user_id=? AND role='user'",
            (user_id,)
        )
        user_messages = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM history WHERE user_id=? AND role='assistant'",
            (user_id,)
        )
        bot_messages = cursor.fetchone()[0]
        
        # Get token usage
        cursor.execute(
            "SELECT SUM(token_count) FROM history WHERE user_id=?",
            (user_id,)
        )
        token_usage = cursor.fetchone()[0] or 0
        
        # Get oldest message time
        cursor.execute(
            "SELECT MIN(timestamp) FROM history WHERE user_id=?",
            (user_id,)
        )
        oldest_timestamp = cursor.fetchone()[0]
        memory_age = "Belum ada riwayat"
        
        if oldest_timestamp:
            days_ago = (time.time() - oldest_timestamp) / (24 * 60 * 60)
            memory_age = f"{int(days_ago)} hari"
        
        # Get personal fact counts
        cursor.execute(
            "SELECT COUNT(*) FROM personal_facts WHERE user_id=?",
            (user_id,)
        )
        fact_count = cursor.fetchone()[0]
        
        conn.close()
        return {
            "user_messages": user_messages,
            "bot_messages": bot_messages,
            "total_messages": user_messages + bot_messages,
            "token_usage": token_usage,
            "memory_age": memory_age,
            "personal_facts": fact_count,
            "memory_usage_percent": min(100, int((token_usage / MEMORY_MAX_TOKENS) * 100)) if MEMORY_MAX_TOKENS > 0 else 0
        }
    
    def save_context(self, user_id: int, chat_id: int, key: str, context_data: Dict[str, Any]) -> None:
        """
        Save context data with specific key (compatibility method for handlers).
        
        Args:
            user_id: Telegram user ID
            chat_id: Chat ID
            key: Context identifier key
            context_data: Context data to save
        """
        try:
            # Ensure proper integer conversion
            user_id = int(user_id) 
            chat_id = int(chat_id)
            
            # Get current context and update
            current_context = self.get_context(user_id, chat_id) or {}
            
            # Add new data under specified key
            current_context[key] = context_data
            
            # Update timestamp to avoid early pruning
            current_context['last_updated'] = int(time.time())
            
            # Save updated context with proper integers
            self.set_context(user_id, current_context, chat_id)
        except Exception as e:
            logger.error(f"Error in save_context: {e}, user_id: {user_id}, chat_id: {chat_id}, key: {key}")
            # Don't reraise exception to prevent handler crashes
        
        # Make important context items more persistent in memory
        if key in ['personal_info', 'preferences', 'important_facts']:
            importance = 2.0  # Higher importance for personal facts
            # Store the key data as a separate message for better recall
            message = f"User context data for key '{key}': {json.dumps(context_data)[:100]}"
            self.add_message_to_history(
                user_id, 
                'system',
                message,
                chat_id=chat_id,
                importance=importance
            )

# Create a singleton instance
context_manager = ContextManager()