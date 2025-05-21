"""
Context Management for Alya Bot.

This module handles storage and retrieval of conversation context
to enable more natural and continuous conversations.
"""

import sqlite3
import json
import logging
import time
import os
import re
import random
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from config.settings import (
    CONTEXT_TTL,
    CONTEXT_DB_PATH,
    CONTEXT_MAX_HISTORY,
    MEMORY_IMPORTANCE_THRESHOLD,
    PERSONAL_FACTS_TTL,
    MEMORY_MAX_TOKENS
)

logger = logging.getLogger(__name__)

class ContextManager:
    """Manager for conversation context persistence."""
    
    def __init__(self, db_path: str = CONTEXT_DB_PATH):
        """Initialize the context manager with a database path."""
        self.db_path = db_path
        self._ensure_db()
        
    def _ensure_db(self) -> None:
        """Ensure database and required tables exist."""
        # Import database functions here to avoid circular import
        from database.database import init_database
        init_database()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection to the SQLite database."""
        # Import get_connection here to avoid circular import
        from database.database import get_connection
        return get_connection()
    
    def _safe_execute(self, func_name: str, operation: callable, *args, **kwargs) -> Any:
        """
        Execute database operation safely with proper error handling.
        
        Args:
            func_name: Name of the calling function for logging
            operation: Callable that performs the database operation
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Result of operation or appropriate fallback value
        """
        conn = None
        
        try:
            conn = self._get_connection()
            result = operation(conn, *args, **kwargs)
            return result
            
        except sqlite3.Error as e:
            logger.error(f"SQLite error in {func_name}: {e}")
            # Return appropriate fallback based on expected return type
            if func_name.startswith("get_"):
                return {} if "context" in func_name or "facts" in func_name else []
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error in {func_name}: {e}", exc_info=True)
            # Return appropriate fallback based on expected return type
            if func_name.startswith("get_"):
                return {} if "context" in func_name or "facts" in func_name else []
            return False
            
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection in {func_name}: {e}")
    
    def get_context(self, user_id: int, chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the context for a user in a specific chat.
        
        Args:
            user_id: Telegram user ID
            chat_id: Optional chat ID for group chat contexts
            
        Returns:
            User context dictionary or empty dict if none exists
        """
        def _operation(conn: sqlite3.Connection, user_id: int, chat_id: Optional[int]) -> Dict[str, Any]:
            # Ensure IDs are integers
            user_id = int(user_id)
            chat_id = int(chat_id) if chat_id is not None else user_id
            
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context_data FROM user_context WHERE user_id=? AND chat_id=? AND context_type='default'", 
                (user_id, chat_id)
            )
            
            result = cursor.fetchone()
            
            if result:
                try:
                    context_data = result[0]
                    if context_data:
                        return json.loads(context_data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in context for user {user_id}")
            
            return {}
            
        return self._safe_execute("get_context", _operation, user_id, chat_id)
    
    def save_context(self, user_id: int, chat_id: int, key: str, context_data: Dict[str, Any]) -> bool:
        """
        Save context data with specific key.
        
        Args:
            user_id: Telegram user ID
            chat_id: Chat ID
            key: Context identifier key
            context_data: Context data to save
            
        Returns:
            True if successful, False otherwise
        """
        def _operation(conn: sqlite3.Connection, user_id: int, chat_id: int, 
                      key: str, context_data: Dict[str, Any]) -> bool:
            try:
                # Ensure proper integer conversion
                user_id = int(user_id) 
                chat_id = int(chat_id)
                
                # Get current context
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT context_data FROM user_context WHERE user_id=? AND chat_id=? AND context_type=?", 
                    (user_id, chat_id, "default")
                )
                
                result = cursor.fetchone()
                current_context = {}
                
                if result and result[0]:
                    try:
                        current_context = json.loads(result[0])
                    except json.JSONDecodeError:
                        # Start fresh if existing context is corrupt
                        current_context = {}
                
                # Add new data under specified key
                current_context[key] = context_data
                
                # Update timestamp
                current_context['last_updated'] = int(time.time())
                
                # Serialize for storage
                try:
                    json_context = json.dumps(current_context)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Context serialization error: {e}, cleaning context")
                    # Clean non-serializable objects
                    cleaned_context = {}
                    for k, v in current_context.items():
                        try:
                            json.dumps({k: v})  # Test serialization
                            cleaned_context[k] = v
                        except:
                            cleaned_context[k] = str(v)  # Convert to string
                    json_context = json.dumps(cleaned_context)
                
                # Save with explicit transaction
                cursor.execute("BEGIN IMMEDIATE TRANSACTION")
                
                cursor.execute(
                    """INSERT OR REPLACE INTO user_context 
                       (user_id, chat_id, context_type, context_data, created_at, expires_at) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, 
                        chat_id, 
                        "default", 
                        json_context, 
                        int(time.time()), 
                        int(time.time()) + CONTEXT_TTL
                    )
                )
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error in save_context: {e}")
                conn.rollback()
                return False
                
        return self._safe_execute("save_context", _operation, user_id, chat_id, key, context_data)
    
    def add_message_to_history(self, 
                              user_id: int, 
                              role: str, 
                              content: str,
                              chat_id: Optional[int] = None,
                              message_id: Optional[int] = None,
                              importance: float = 1.0, 
                              metadata: Optional[Dict] = None) -> bool:
        """
        Add a message to the user's conversation history.
        
        Args:
            user_id: Telegram user ID
            role: Message role (user, assistant, system)
            content: Message content
            chat_id: Chat ID for group chats
            message_id: Message ID for reference
            importance: Message importance for memory pruning (higher = more important)
            metadata: Additional message metadata
            
        Returns:
            True if message was added successfully, False otherwise
        """
        if not user_id or not role or not content:
            return False

        def _operation(conn: sqlite3.Connection, user_id: int, role: str, 
                      content: str, chat_id: Optional[int], message_id: Optional[int],
                      importance: float, metadata: Optional[Dict]) -> bool:
            try:
                # Validate and convert data types
                user_id = int(user_id)
                chat_id = int(chat_id) if chat_id is not None else user_id
                
                token_count = self._estimate_token_count(content)
                cursor = conn.cursor()
                
                # Use explicit transaction
                cursor.execute("BEGIN IMMEDIATE TRANSACTION")
                
                # Save message to history
                cursor.execute(
                    """INSERT INTO chat_history 
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
                
                # Prune history occasionally
                if random.random() < 0.3:  # Only ~30% of the time
                    self._prune_history_if_needed(user_id, cursor)
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error adding message to history: {e}")
                conn.rollback()
                return False
                
        return self._safe_execute("add_message_to_history", _operation, 
                                 user_id, role, content, chat_id, message_id, 
                                 importance, metadata)
    
    def add_chat_message(self, user_id: int, chat_id: Optional[int], message_id: Optional[int], 
                        role: str, content: str, importance: float = 1.0,
                        metadata: Optional[Dict] = None) -> bool:
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
            
        Returns:
            True if message was added successfully, False otherwise
        """
        # Call the main implementation
        return self.add_message_to_history(
            user_id=user_id,
            role=role,
            content=content,
            chat_id=chat_id,
            message_id=message_id,
            importance=importance,
            metadata=metadata
        )
    
    def _prune_history_if_needed(self, user_id: int, cursor: sqlite3.Cursor) -> None:
        """
        Prune history if it exceeds the maximum allowed size.
        
        Args:
            user_id: Telegram user ID
            cursor: Database cursor
        """
        try:
            # Get total token count
            cursor.execute(
                "SELECT COUNT(*), SUM(token_count) FROM chat_history WHERE user_id=?", 
                (user_id,)
            )
            count, total_tokens = cursor.fetchone()
            
            # If we have a valid count and exceeded max tokens
            if count and total_tokens and total_tokens > MEMORY_MAX_TOKENS:
                # Get messages to delete, ordered by importance (ascending) and timestamp (ascending)
                cursor.execute(
                    """SELECT id, token_count FROM chat_history 
                       WHERE user_id=? 
                       ORDER BY importance ASC, timestamp ASC""",
                    (user_id,)
                )
                
                # Delete messages until under the token limit
                rows_to_delete = []
                deleted_tokens = 0
                target_tokens = total_tokens - MEMORY_MAX_TOKENS + (MEMORY_MAX_TOKENS * 0.2)  # Delete extra 20% for buffer
                
                for row in cursor.fetchall():
                    rows_to_delete.append(row[0])
                    deleted_tokens += row[1]
                    if deleted_tokens >= target_tokens:
                        break
                
                # Execute delete if needed
                if rows_to_delete:
                    placeholders = ', '.join('?' for _ in rows_to_delete)
                    cursor.execute(
                        f"DELETE FROM chat_history WHERE id IN ({placeholders})",
                        rows_to_delete
                    )
                    logger.info(f"Pruned {len(rows_to_delete)} messages for user {user_id}, freed {deleted_tokens} tokens")
        except Exception as e:
            logger.error(f"Error in prune history: {e}")
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Simple estimation: ~4 chars per token on average
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
            List of message dictionaries in chronological order
        """
        def _operation(conn: sqlite3.Connection, user_id: int, 
                      limit: int, include_metadata: bool) -> List[Dict[str, Any]]:
            cursor = conn.cursor()
            
            if include_metadata:
                cursor.execute(
                    """SELECT role, content, timestamp, importance, metadata 
                       FROM chat_history 
                       WHERE user_id=? 
                       ORDER BY timestamp DESC LIMIT ?""",
                    (user_id, limit)
                )
                messages = []
                for row in cursor.fetchall():
                    try:
                        metadata = json.loads(row[4]) if row[4] else {}
                    except json.JSONDecodeError:
                        metadata = {}
                    
                    messages.append({
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                        "importance": row[3],
                        "metadata": metadata
                    })
            else:
                cursor.execute(
                    """SELECT role, content 
                       FROM chat_history 
                       WHERE user_id=? 
                       ORDER BY timestamp DESC LIMIT ?""",
                    (user_id, limit)
                )
                messages = [
                    {"role": row[0], "content": row[1]} 
                    for row in cursor.fetchall()
                ]
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
            
        return self._safe_execute("get_conversation_history", _operation, 
                                 user_id, limit, include_metadata)
    
    def get_chat_history(self, user_id: int, chat_id: int, 
                        limit: int = CONTEXT_MAX_HISTORY) -> List[Dict[str, Any]]:
        """
        Get chat history specific to a chat.
        
        Args:
            user_id: Telegram user ID
            chat_id: Chat ID for group chat contexts
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of chat message dictionaries in chronological order
        """
        def _operation(conn: sqlite3.Connection, user_id: int, 
                      chat_id: int, limit: int) -> List[Dict[str, Any]]:
            cursor = conn.cursor()
            
            try:
                # Try safer query that works even if metadata column doesn't exist
                try:
                    cursor.execute(
                        """SELECT role, content 
                           FROM chat_history 
                           WHERE user_id=? AND chat_id=?
                           ORDER BY timestamp DESC LIMIT ?""",
                        (user_id, chat_id, limit)
                    )
                    
                    messages = [
                        {"role": row[0], "content": row[1]} 
                        for row in cursor.fetchall()
                    ]
                    
                except sqlite3.OperationalError as e:
                    logger.warning(f"Basic query failed, using more basic version: {e}")
                    # Fallback query without metadata filtering
                    cursor.execute(
                        """SELECT role, content
                           FROM chat_history 
                           WHERE user_id=? AND chat_id=?
                           ORDER BY timestamp DESC LIMIT ?""",
                        (user_id, chat_id, limit)
                    )
                    
                    messages = [
                        {"role": row[0], "content": row[1]} 
                        for row in cursor.fetchall()
                    ]
            
            except sqlite3.Error as e:
                logger.error(f"Error in get_chat_history: {e}")
                messages = []
            
            # Return in chronological order
            return list(reversed(messages))
            
        return self._safe_execute("get_chat_history", _operation, user_id, chat_id, limit)
    
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
        def _operation(conn: sqlite3.Connection, user_id: int, query: str,
                      limit: int, min_importance: float) -> List[Dict[str, Any]]:
            cursor = conn.cursor()
            
            # Extract keywords (3+ letter words)
            keywords = re.findall(r'\b\w{3,}\b', query.lower())
            
            if not keywords:
                # Return recent important messages if no keywords
                cursor.execute(
                    """SELECT role, content, timestamp 
                       FROM chat_history 
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
                search_query = f"""
                    SELECT role, content, timestamp 
                    FROM chat_history 
                    WHERE user_id=? AND importance >= ? AND ({where_clause})
                    ORDER BY timestamp DESC LIMIT ?
                """
                params.append(limit)
                cursor.execute(search_query, params)
            
            results = []
            for row in cursor.fetchall():
                timestamp_str = datetime.fromtimestamp(row[2]).strftime("%Y-%m-%d %H:%M:%S")
                results.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": timestamp_str
                })
                
            return results
            
        return self._safe_execute("search_memory", _operation, 
                                 user_id, query, limit, min_importance)
    
    def extract_and_store_personal_facts(self, user_id: int, messages: List[Dict[str, str]]) -> bool:
        """
        Extract and store personal facts from conversation.
        
        Args:
            user_id: Telegram user ID
            messages: Recent conversation messages
            
        Returns:
            True if facts were extracted and stored, False otherwise
        """
        # Import here to avoid circular imports
        from utils.fact_extractor import fact_extractor
        
        found_facts = {}
        
        # Use fact extractor for each message
        for message in messages:
            if message["role"] != "user":
                continue
                
            facts = fact_extractor.extract_facts_from_text(message["content"])
            found_facts.update(facts)
                
        # Store facts if any found
        if found_facts:
            return fact_extractor.store_facts(user_id, found_facts)
            
        return False
    
    def get_personal_facts(self, user_id: int) -> Dict[str, str]:
        """
        Get stored personal facts about a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary of fact_key: fact_value
        """
        def _operation(conn: sqlite3.Connection, user_id: int) -> Dict[str, str]:
            cursor = conn.cursor()
            current_time = int(time.time())
            
            cursor.execute(
                """SELECT fact_key, fact_value 
                   FROM personal_facts 
                   WHERE user_id=? AND expires_at > ?
                   ORDER BY confidence DESC""",
                (user_id, current_time)
            )
            
            facts = {}
            seen_keys = set()
            
            for row in cursor.fetchall():
                key, value = row[0], row[1]
                if key not in seen_keys:
                    facts[key] = value
                    seen_keys.add(key)
                    
            return facts
            
        return self._safe_execute("get_personal_facts", _operation, user_id)
        
    def recall_relevant_context(self, user_id: int, current_message: str, 
                               chat_id: Optional[int] = None) -> Dict[str, Any]:
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
        def _operation(conn: sqlite3.Connection, user_id: int, 
                      query: str, importance: float) -> bool:
            cursor = conn.cursor()
            
            # Find message with partial content match
            cursor.execute(
                "SELECT id, importance FROM chat_history WHERE user_id=? AND content LIKE ? ORDER BY timestamp DESC LIMIT 1",
                (user_id, f"%{query}%")
            )
            
            result = cursor.fetchone()
            if not result:
                return False
                
            message_id, current_importance = result
            new_importance = min(5.0, current_importance * importance)  # Cap at 5.0
            
            cursor.execute(
                "UPDATE chat_history SET importance=? WHERE id=?",
                (new_importance, message_id)
            )
            
            conn.commit()
            return True
            
        return self._safe_execute("mark_message_important", _operation, 
                                 user_id, query, importance)
    
    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Clean up expired context entries and low-importance history.
        
        Returns:
            Tuple containing (context_count, history_count) of removed items
        """
        def _operation(conn: sqlite3.Connection) -> Tuple[int, int]:
            cursor = conn.cursor()
            context_count = 0
            history_count = 0
            
            # Clean up outdated contexts
            expiry_time = int(time.time()) - CONTEXT_TTL
            cursor.execute("DELETE FROM user_context WHERE expires_at < ?", (expiry_time,))
            context_count = cursor.rowcount
            
            # Clean up outdated personal facts
            current_time = int(time.time())
            cursor.execute("DELETE FROM personal_facts WHERE expires_at < ?", (current_time,))
            
            # Clean old history with different retention based on importance
            three_months_ago = int(time.time()) - (90 * 24 * 60 * 60)
            one_month_ago = int(time.time()) - (30 * 24 * 60 * 60)
            one_week_ago = int(time.time()) - (7 * 24 * 60 * 60)
            
            try:
                # Delete history based on age and importance
                cursor.execute(
                    "DELETE FROM chat_history WHERE timestamp < ? AND importance < 0.8",
                    (three_months_ago,)
                )
                deleted1 = cursor.rowcount
                
                cursor.execute(
                    "DELETE FROM chat_history WHERE timestamp < ? AND importance < 1.2",
                    (one_month_ago,)
                )
                deleted2 = cursor.rowcount
                
                cursor.execute(
                    "DELETE FROM chat_history WHERE timestamp < ? AND importance < 0.5",
                    (one_week_ago,)
                )
                deleted3 = cursor.rowcount
                
                history_count = deleted1 + deleted2 + deleted3
                
            except sqlite3.Error as e:
                logger.error(f"Error during history cleanup: {e}")
                conn.rollback()
                return context_count, 0
                
            conn.commit()
            return context_count, history_count
            
        counts = self._safe_execute("cleanup_expired", _operation)
        return counts if counts else (0, 0)
    
    def get_memory_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about a user's memory.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with memory statistics
        """
        def _operation(conn: sqlite3.Connection, user_id: int) -> Dict[str, Any]:
            cursor = conn.cursor()
            
            # Get message counts
            cursor.execute(
                "SELECT COUNT(*) FROM chat_history WHERE user_id=? AND role='user'",
                (user_id,)
            )
            user_messages = cursor.fetchone()[0] or 0
            
            cursor.execute(
                "SELECT COUNT(*) FROM chat_history WHERE user_id=? AND role='assistant'",
                (user_id,)
            )
            bot_messages = cursor.fetchone()[0] or 0
            
            # Get token usage
            cursor.execute(
                "SELECT SUM(token_count) FROM chat_history WHERE user_id=?",
                (user_id,)
            )
            token_usage = cursor.fetchone()[0] or 0
            
            # Get oldest message time
            cursor.execute(
                "SELECT MIN(timestamp) FROM chat_history WHERE user_id=?",
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
            fact_count = cursor.fetchone()[0] or 0
            
            # Calculate memory usage percentage
            memory_usage_percent = 0
            if MEMORY_MAX_TOKENS > 0:
                memory_usage_percent = min(100, int((token_usage / MEMORY_MAX_TOKENS) * 100))
            
            return {
                "user_messages": user_messages,
                "bot_messages": bot_messages,
                "total_messages": user_messages + bot_messages,
                "token_usage": token_usage,
                "memory_age": memory_age,
                "personal_facts": fact_count,
                "memory_usage_percent": memory_usage_percent
            }
            
        return self._safe_execute("get_memory_stats", _operation, user_id)
    
    def get_db_stats(self) -> Dict[str, Any]:
        """
        Get overall database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        def _operation(conn: sqlite3.Connection) -> Dict[str, Any]:
            cursor = conn.cursor()
            stats = {
                "tables": {},
                "user_count": 0,
                "total_messages": 0,
                "active_users_24h": 0, # Added for new stats
                "db_size_mb": 0
            }
            
            # Get table counts
            for table in ["user_context", "chat_history", "personal_facts"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats["tables"][table] = cursor.fetchone()[0] or 0
                
            # Get unique user counts (overall)
            cursor.execute(
                "SELECT COUNT(DISTINCT user_id) FROM chat_history"
            )
            stats["user_count"] = cursor.fetchone()[0] or 0
            
            # Get total message count
            cursor.execute(
                "SELECT COUNT(*) FROM chat_history"
            )
            stats["total_messages"] = cursor.fetchone()[0] or 0

            # Get active users in the last 24 hours
            one_day_ago = int(time.time()) - (24 * 60 * 60)
            cursor.execute(
                "SELECT COUNT(DISTINCT user_id) FROM chat_history WHERE timestamp >= ?",
                (one_day_ago,)
            )
            stats["active_users_24h"] = cursor.fetchone()[0] or 0
            
            # Calculate database file size
            if os.path.exists(self.db_path):
                stats["db_size_mb"] = os.path.getsize(self.db_path) / (1024 * 1024)
                
            return stats
            
        return self._safe_execute("get_db_stats", _operation)

    def clear_chat_history(self, user_id: int, chat_id: Optional[int] = None) -> bool:
        """
        Clear chat history for a user/chat.
        
        Args:
            user_id: User ID
            chat_id: Optional chat ID (if None, clears all chats for user)
            
        Returns:
            Success status
        """
        try:
            conn = self._get_connection()
            with conn:
                if chat_id:
                    # Clear history for specific chat
                    conn.execute(
                        'DELETE FROM chat_history WHERE user_id = ? AND chat_id = ?',
                        (user_id, chat_id)
                    )
                else:
                    # Clear history across all chats
                    conn.execute(
                        'DELETE FROM chat_history WHERE user_id = ?',
                        (user_id,)
                    )
            
            logger.info(f"Chat history cleared for user {user_id}, chat {chat_id or 'all'}")
            return True
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return False

    def get_unique_user_count(self) -> int:
        """
        Return the number of unique users in chat history.
        """
        def _operation(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM chat_history")
            result = cursor.fetchone()
            return result[0] if result else 0
        return self._safe_execute("get_unique_user_count", _operation)

    def get_active_user_count(self, days: int = 1) -> int:
        """
        Return the number of unique active users in the last N days.

        Args:
            days: Number of past days to consider for activity.

        Returns:
            Count of active users.
        """
        def _operation(conn: sqlite3.Connection, days: int) -> int:
            cursor = conn.cursor()
            since_timestamp = int(time.time()) - (days * 24 * 60 * 60)
            cursor.execute(
                "SELECT COUNT(DISTINCT user_id) FROM chat_history WHERE timestamp >= ?",
                (since_timestamp,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        return self._safe_execute("get_active_user_count", _operation, days=days)

    def get_total_message_count(self) -> int:
        """
        Return the total number of messages in chat history.

        Returns:
            Total count of messages.
        """
        def _operation(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chat_history")
            result = cursor.fetchone()
            return result[0] if result else 0
        return self._safe_execute("get_total_message_count", _operation)

# Create a singleton instance
context_manager = ContextManager()