"""
Context Queue Manager for Alya Bot.

This module handles sliding window context management using a queue system
to maintain conversation history within defined limits.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import deque
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import (
    CONTEXT_MAX_HISTORY,
    CONTEXT_DB_PATH,
    CONTEXT_RELEVANCE_WINDOW
)

logger = logging.getLogger(__name__)

class ContextQueue:
    """Manages conversation context using a sliding window approach."""
    
    def __init__(self, max_size: int = CONTEXT_MAX_HISTORY):
        """Initialize context queue manager."""
        self.max_size = max_size
        self.queues: Dict[int, deque] = {}
        self.db_path = CONTEXT_DB_PATH
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS context_queue (
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        message_id INTEGER NOT NULL,
                        timestamp INTEGER NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata TEXT,
                        PRIMARY KEY (user_id, chat_id, message_id)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_context_user_chat ON context_queue(user_id, chat_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_context_timestamp ON context_queue(timestamp)")
        except Exception as e:
            logger.error(f"Error initializing context queue db: {e}")
    
    def add_message(self, 
                    user_id: int,
                    chat_id: int,
                    message_id: int,
                    role: str,
                    content: str,
                    metadata: Optional[Dict] = None) -> None:
        """
        Add message to context queue with sliding window.
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            message_id: Message ID
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata
        """
        try:
            # Add to database
            with sqlite3.connect(self.db_path) as conn:
                # Remove oldest message if queue full
                count = conn.execute(
                    "SELECT COUNT(*) FROM context_queue WHERE user_id = ? AND chat_id = ?",
                    (user_id, chat_id)
                ).fetchone()[0]
                
                if count >= self.max_size:
                    # Remove oldest message
                    conn.execute("""
                        DELETE FROM context_queue 
                        WHERE user_id = ? AND chat_id = ?
                        AND message_id = (
                            SELECT message_id FROM context_queue 
                            WHERE user_id = ? AND chat_id = ?
                            ORDER BY timestamp ASC LIMIT 1
                        )
                    """, (user_id, chat_id, user_id, chat_id))
                
                # Add new message
                conn.execute(
                    """INSERT INTO context_queue 
                       (user_id, chat_id, message_id, timestamp, role, content, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, chat_id, message_id, int(datetime.now().timestamp()),
                     role, content, str(metadata or {}))
                )
                
        except Exception as e:
            logger.error(f"Error adding message to context queue: {e}")
    
    def get_context(self, 
                    user_id: int,
                    chat_id: int,
                    window_size: Optional[int] = None,
                    time_window: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get context messages within window.
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            window_size: Optional max messages to return
            time_window: Optional time window in seconds
            
        Returns:
            List of context messages
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT message_id, timestamp, role, content, metadata
                    FROM context_queue
                    WHERE user_id = ? AND chat_id = ?
                """
                params = [user_id, chat_id]
                
                if time_window:
                    min_time = int((datetime.now() - timedelta(seconds=time_window)).timestamp())
                    query += " AND timestamp >= ?"
                    params.append(min_time)
                    
                query += " ORDER BY timestamp DESC"
                
                if window_size:
                    query += " LIMIT ?"
                    params.append(window_size)
                    
                rows = conn.execute(query, params).fetchall()
                
                return [{
                    'message_id': row[0],
                    'timestamp': row[1],
                    'role': row[2],
                    'content': row[3],
                    'metadata': eval(row[4]) if row[4] else {}
                } for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []
    
    def clear_context(self, user_id: int, chat_id: Optional[int] = None) -> None:
        """Clear context for user/chat."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if chat_id is not None:
                    conn.execute(
                        "DELETE FROM context_queue WHERE user_id = ? AND chat_id = ?",
                        (user_id, chat_id)
                    )
                else:
                    conn.execute(
                        "DELETE FROM context_queue WHERE user_id = ?",
                        (user_id,)
                    )
        except Exception as e:
            logger.error(f"Error clearing context: {e}")

    def cleanup_old_contexts(self, max_age: int = CONTEXT_RELEVANCE_WINDOW) -> None:
        """Remove contexts older than max_age seconds."""
        try:
            min_time = int((datetime.now() - timedelta(seconds=max_age)).timestamp())
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM context_queue WHERE timestamp < ?",
                    (min_time,)
                )
        except Exception as e:
            logger.error(f"Error cleaning up old contexts: {e}")

# Create singleton instance
context_queue = ContextQueue()
