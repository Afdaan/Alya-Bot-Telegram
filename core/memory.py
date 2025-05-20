"""
Memory Management System for Alya Bot.

This module provides natural memory recall capabilities, handling both
short-term context and long-term memory storage to make Alya's conversations
feel more human-like and continuous.
"""

import json
import sqlite3
import logging
from typing import Dict, List, Optional, Any, Union
import time
from datetime import datetime

from config.settings import (
    CONTEXT_DB_PATH,
    MEMORY_MAX_TOKENS,
    MEMORY_IMPORTANCE_THRESHOLD
)

from database.database import get_connection
from utils.topic_extractor import extract_key_topics
from core.personas import persona_manager, get_persona_context

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manager for Alya's memory system with natural recall abilities."""
    
    def __init__(self) -> None:
        """Initialize the memory manager."""
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self) -> None:
        """Ensure all required database tables exist."""
        conn = get_connection()
        try:
            with conn:
                # User memory table for persistent memory
                conn.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id INTEGER PRIMARY KEY,
                    nickname TEXT,
                    topics TEXT,
                    summary TEXT,
                    last_updated INTEGER
                )
                """)
                
                # Memory facts table for specific facts about users
                conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    fact_key TEXT,
                    fact_value TEXT,
                    importance REAL,
                    last_accessed INTEGER,
                    created_at INTEGER,
                    UNIQUE(user_id, fact_key)
                )
                """)
                
                logger.debug("Memory tables verified")
        except sqlite3.Error as e:
            logger.error(f"Database error during table creation: {e}")
        finally:
            conn.close()
    
    def get_user_memory(self, user_id: int) -> Dict[str, Any]:
        """
        Get user memory context (topics and summary).
        
        Args:
            user_id: User's Telegram ID
            
        Returns:
            Dictionary with user memory data
        """
        conn = get_connection()
        try:
            with conn:
                row = conn.execute(
                    "SELECT nickname, topics, summary FROM user_memory WHERE user_id = ?", 
                    (user_id,)
                ).fetchone()
                
                if row:
                    nickname, topics_str, summary = row
                    topics = topics_str.split(",") if topics_str else []
                    return {
                        "nickname": nickname,
                        "topics": topics,
                        "summary": summary or ""
                    }
                return {"nickname": None, "topics": [], "summary": ""}
        except sqlite3.Error as e:
            logger.error(f"SQLite error in get_user_memory: {e}")
            return {"nickname": None, "topics": [], "summary": ""}
        finally:
            conn.close()
    
    def update_user_memory(self, 
                          user_id: int, 
                          new_topics: Optional[List[str]] = None, 
                          new_summary: Optional[str] = None, 
                          nickname: Optional[str] = None) -> bool:
        """
        Update user memory with new topics and/or summary.
        
        Args:
            user_id: User's Telegram ID
            new_topics: New topics to add
            new_summary: New or updated summary
            nickname: User's preferred nickname
            
        Returns:
            Boolean indicating success
        """
        if user_id is None:
            logger.warning("Attempted to update memory with None user_id")
            return False
            
        conn = get_connection()
        try:
            with conn:
                # Get current data
                row = conn.execute(
                    "SELECT topics, summary, nickname FROM user_memory WHERE user_id = ?", 
                    (user_id,)
                ).fetchone()
                
                current_topics = []
                current_summary = ""
                current_nickname = None
                
                if row:
                    topics_str, current_summary, current_nickname = row
                    current_topics = topics_str.split(",") if topics_str else []
                
                # Update with new data
                if new_topics:
                    # Merge topics, remove duplicates, keep most recent up to 10
                    all_topics = list(set(new_topics + current_topics))
                    topics_str = ",".join(all_topics[:10])
                else:
                    topics_str = ",".join(current_topics)
                    
                final_summary = new_summary if new_summary else current_summary
                final_nickname = nickname if nickname else current_nickname
                
                # Insert or replace
                conn.execute(
                    """
                    INSERT OR REPLACE INTO user_memory 
                    (user_id, nickname, topics, summary, last_updated) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, final_nickname, topics_str, final_summary, int(time.time()))
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error in update_user_memory: {e}")
            return False
        finally:
            conn.close()
    
    def extract_topics_from_message(self, message: str) -> List[str]:
        """
        Extract important topics from message using simple heuristics.
        
        Args:
            message: User's message text
            
        Returns:
            List of extracted topics
        """
        if not message or len(message.strip()) < 10:
            return []
        
        # Use the dedicated topic extractor instead
        return extract_key_topics(message, max_topics=5)
    
    def store_user_fact(self, user_id: int, fact_key: str, fact_value: str, 
                       importance: float = 1.0) -> bool:
        """
        Store or update a specific fact about a user.
        
        Args:
            user_id: User's Telegram ID
            fact_key: Key/category of the fact (e.g., "hobby", "birthdate")
            fact_value: Value of the fact
            importance: Importance score (higher = more important)
            
        Returns:
            Boolean indicating success
        """
        if not fact_key or not fact_value:
            return False
            
        conn = get_connection()
        try:
            with conn:
                now = int(time.time())
                conn.execute(
                    """
                    INSERT OR REPLACE INTO memory_facts
                    (user_id, fact_key, fact_value, importance, last_accessed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, fact_key, fact_value, importance, now, now)
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error in store_user_fact: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_facts(self, user_id: int, relevant_keys: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Get facts about a user, optionally filtered by relevance.
        
        Args:
            user_id: User's Telegram ID
            relevant_keys: Optional list of keys to filter by
            
        Returns:
            Dictionary of fact_key -> fact_value
        """
        conn = get_connection()
        try:
            with conn:
                query = "SELECT fact_key, fact_value FROM memory_facts WHERE user_id = ?"
                params = [user_id]
                
                if relevant_keys:
                    placeholders = ", ".join(["?"] * len(relevant_keys))
                    query += f" AND fact_key IN ({placeholders})"
                    params.extend(relevant_keys)
                    
                query += " ORDER BY importance DESC, last_accessed DESC"
                
                rows = conn.execute(query, params).fetchall()
                
                # Update last accessed time for retrieved facts
                if rows:
                    now = int(time.time())
                    fact_keys = [row[0] for row in rows]
                    placeholders = ", ".join(["?"] * len(fact_keys))
                    
                    conn.execute(
                        f"UPDATE memory_facts SET last_accessed = ? WHERE user_id = ? AND fact_key IN ({placeholders})",
                        [now, user_id] + fact_keys
                    )
                
                return {row[0]: row[1] for row in rows}
        except sqlite3.Error as e:
            logger.error(f"SQLite error in get_user_facts: {e}")
            return {}
        finally:
            conn.close()
    
    def build_prompt_with_memory(self, 
                               user_id: int, 
                               user_message: str,
                               recent_history: List[Dict[str, str]],
                               persona: str = "tsundere") -> str:
        """
        Build a prompt with memory context for natural conversation.
        
        Args:
            user_id: User's Telegram ID
            user_message: Current message from user
            recent_history: Recent conversation history
            persona: Alya's current persona
            
        Returns:
            Formatted prompt including memory context
        """
        # Get user memory
        memory = self.get_user_memory(user_id)
        nickname = memory.get("nickname") or "User"
        
        # Get relevant user facts based on message content
        topics = self.extract_topics_from_message(user_message)
        facts = self.get_user_facts(user_id, topics)
        
        # Format recent history
        history_text = ""
        for entry in recent_history[-5:]:  # Last 5 messages
            role = "User" if entry.get("role") == "user" else "Alya"
            history_text += f"{role}: {entry.get('content', '')}\n"
        
        # Format topics if any
        topics_str = ", ".join(memory.get("topics", [])) if memory.get("topics") else "belum ada topik"
        
        # Format user facts if any
        facts_text = "\n".join([f"- {key}: {value}" for key, value in facts.items()]) if facts else ""
        facts_section = f"USER FACTS:\n{facts_text}\n" if facts else ""
        
        # Extract new topics from current message and update memory
        if topics:
            self.update_user_memory(user_id, new_topics=topics)
        
        # Get persona context from YAML definitions instead of hardcoded guidelines
        persona_context = get_persona_context(persona)
        
        # Get current mood based on conversation
        try:
            mood = persona_manager.detect_mood(user_id, user_message)
        except Exception as e:
            logger.error(f"Error detecting mood: {e}")
            mood = "default"
        
        # Build the prompt with persona-specific instructions from YAML
        prompt = f"""You are Alya, a half Japanese-Russian high school girl.

{persona_context}

USER INFORMATION:
- User prefers to be called: {nickname}
- Topics previously discussed: {topics_str}
{memory.get('summary', '')}
{facts_section}

RECENT CONVERSATION:
{history_text}

USER'S CURRENT MESSAGE:
{user_message}

Your current mood: {mood}
"""
        
        return prompt

# Create a singleton instance
memory_manager = MemoryManager()
