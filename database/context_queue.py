"""
Context Queue Manager for Alya Bot.

This module handles sliding window context management using a queue system
to maintain conversation history within defined limits.
"""

import logging
import sqlite3
import time
from typing import List, Dict, Any, Optional
from collections import deque
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import (
    SLIDING_WINDOW_ENABLED,
    SLIDING_WINDOW_SIZE,
    SLIDING_WINDOW_STORAGE,
    CONTEXT_MIN_IMPORTANCE,
    CONTEXT_OPTIMAL_SIZE,
    MESSAGE_IMPORTANCE_WEIGHTS,
    CONTEXT_DB_PATH,
    CONTEXT_RELEVANCE_WINDOW
)

logger = logging.getLogger(__name__)

class ContextQueue:
    """Manages conversation context using a sliding window approach."""
    
    def __init__(self):
        """Initialize context queue manager with settings."""
        self.enabled = SLIDING_WINDOW_ENABLED
        self.max_size = SLIDING_WINDOW_SIZE
        self.min_importance = CONTEXT_MIN_IMPORTANCE
        self.optimal_size = CONTEXT_OPTIMAL_SIZE
        self.storage_type = SLIDING_WINDOW_STORAGE
        self.importance_weights = MESSAGE_IMPORTANCE_WEIGHTS
        self.db_path = CONTEXT_DB_PATH
        
        # Initialize database if using permanent storage
        if self.storage_type == "permanent":
            self._init_db()
        else:
            # Use in-memory queue for temporary storage
            self.queues: Dict[int, deque] = {}
        
    def _init_db(self) -> None:
        """Initialize database tables with safe migrations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if table exists
                table_check = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='context_queue'"
                ).fetchone()
                
                if not table_check:
                    # New database - create full schema
                    migration_path = Path(__file__).parent / "migrations" / "001_initial_schema.sql"
                    with open(migration_path) as f:
                        conn.executescript(f.read())
                    logger.info("Created new database with full schema")
                else:
                    # Existing database - check and add missing columns
                    cursor = conn.execute("PRAGMA table_info(context_queue)")
                    existing_columns = [col[1] for col in cursor.fetchall()]
                    
                    # Add any missing columns
                    if 'relevancy' not in existing_columns:
                        conn.execute("ALTER TABLE context_queue ADD COLUMN relevancy REAL DEFAULT 0.0")
                        logger.info("Added relevancy column")
                    
                    if 'reference_count' not in existing_columns:
                        conn.execute("ALTER TABLE context_queue ADD COLUMN reference_count INTEGER DEFAULT 0")
                        logger.info("Added reference_count column")
                        
                    if 'last_referenced' not in existing_columns:
                        conn.execute("ALTER TABLE context_queue ADD COLUMN last_referenced INTEGER")
                        logger.info("Added last_referenced column")
                    
                    # Create indexes if they don't exist
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_context_relevancy ON context_queue(relevancy)")
                    
                logger.info("Database schema initialization complete")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def add_message(self, 
                    user_id: int,
                    chat_id: int,
                    message_id: int,
                    role: str,
                    content: str,
                    metadata: Optional[Dict] = None) -> None:
        """Add message to context queue with sliding window."""
        # Early return if disabled
        if not self.enabled:
            return
            
        try:
            importance = self._calculate_importance(content, role, metadata)
            
            if self.storage_type == "permanent":
                self._add_message_permanent(
                    user_id, chat_id, message_id, role, content, metadata, importance
                )
            else:
                self._add_message_temporary(
                    user_id, chat_id, message_id, role, content, metadata, importance
                )
                
        except Exception as e:
            logger.error(f"Error adding message to context queue: {e}")

    def _calculate_importance(self, content: str, role: str, metadata: Optional[Dict]) -> float:
        """Calculate message importance using configured weights."""
        score = 1.0
        
        # Use importance weights from settings
        if role == "user":
            score *= self.importance_weights.get("user", 1.2)
        elif role == "assistant":
            score *= self.importance_weights.get("assistant", 1.1)
        elif role == "system":
            score *= self.importance_weights.get("system", 1.0)
            
        # Apply type-specific weights
        if metadata and "type" in metadata:
            msg_type = metadata["type"]
            score *= self.importance_weights.get(msg_type, 1.0)
        
        # Recent messages are more important
        time_decay = 1.0 - (time.time() - metadata.get("timestamp", time.time())) / (24 * 3600)
        score *= max(0.5, time_decay)
        
        return min(2.0, max(0.5, score))  # Clamp between 0.5 and 2.0

    def _is_queue_full(self, conn: sqlite3.Connection, user_id: int, chat_id: int) -> bool:
        """Check if the context queue is full for a user/chat."""
        count = conn.execute(
            "SELECT COUNT(*) FROM context_queue WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        ).fetchone()[0]
        return count >= self.max_size

    def _prune_context(self, conn: sqlite3.Connection, user_id: int, chat_id: int) -> None:
        """Smart context pruning based on importance and relevancy."""
        try:
            target_size = self.optimal_size
            
            # Get messages with combined score (importance + relevancy)
            cursor = conn.execute("""
                SELECT 
                    message_id,
                    importance,
                    relevancy,
                    timestamp,
                    reference_count,
                    last_referenced
                FROM context_queue 
                WHERE user_id = ? AND chat_id = ?
                ORDER BY (importance * 0.6 + relevancy * 0.4) DESC, timestamp DESC
                LIMIT 30
            """, (user_id, chat_id))
            
            messages = cursor.fetchall()
            if len(messages) > target_size:
                # Keep messages with high combined score
                to_keep = sorted(
                    messages,
                    key=lambda m: (
                        m[1] * 0.6 +  # Importance weight
                        m[2] * 0.4 +  # Relevancy weight
                        (0.2 if time.time() - m[5] < 86400 else 0.0)  # Bonus for recent references
                    ),
                    reverse=True
                )[:target_size]
                
                keep_ids = [m[0] for m in to_keep]
                
                # Delete messages not in keep list
                cursor.execute(
                    f"""DELETE FROM context_queue 
                        WHERE user_id = ? AND chat_id = ?
                        AND message_id NOT IN ({','.join('?' * len(keep_ids))})""",
                    [user_id, chat_id] + keep_ids
                )
                
        except Exception as e:
            logger.error(f"Error pruning context: {e}")

    def get_context(self, 
                    user_id: int,
                    chat_id: int,
                    window_size: Optional[int] = None,
                    time_window: Optional[int] = None,
                    min_importance: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get context messages within window."""
        # Return empty list if disabled
        if not self.enabled:
            return []
            
        try:
            if self.storage_type == "permanent":
                return self._get_context_permanent(
                    user_id, chat_id, window_size, time_window, min_importance
                )
            else:
                return self._get_context_temporary(
                    user_id, chat_id, window_size, time_window, min_importance
                )
                
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    def _get_context_permanent(self, 
                               user_id: int,
                               chat_id: int,
                               window_size: Optional[int] = None,
                               time_window: Optional[int] = None,
                               min_importance: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get context messages from permanent storage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT message_id, timestamp, role, content, metadata, importance
                    FROM context_queue
                    WHERE user_id = ? AND chat_id = ?
                    AND importance >= ?
                """
                params = [user_id, chat_id, min_importance or self.min_importance]
                
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
                    'metadata': eval(row[4]) if row[4] else {},
                    'importance': row[5]
                } for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    def _get_context_temporary(self, 
                               user_id: int,
                               chat_id: int,
                               window_size: Optional[int] = None,
                               time_window: Optional[int] = None,
                               min_importance: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get context messages from temporary storage."""
        queue_key = (user_id, chat_id)
        
        if queue_key not in self.queues:
            return []
        
        messages = list(self.queues[queue_key])
        
        if min_importance is None:
            min_importance = self.min_importance
        
        # Filter by importance
        messages = [msg for msg in messages if msg['importance'] >= min_importance]
        
        # Filter by time window
        if time_window:
            min_time = int((datetime.now() - timedelta(seconds=time_window)).timestamp())
            messages = [msg for msg in messages if msg['timestamp'] >= min_time]
        
        # Sort by timestamp descending
        messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        if window_size:
            messages = messages[:window_size]
        
        return messages

    def _add_message_permanent(self, *args) -> None:
        """Add message to permanent storage."""
        with sqlite3.connect(self.db_path) as conn:
            # When queue is full, remove least important messages first
            if self._is_queue_full(conn, args[0], args[1]):
                self._prune_context(conn, args[0], args[1])
                
            # Add new message
            conn.execute(
                """INSERT INTO context_queue 
                   (user_id, chat_id, message_id, timestamp, role, content, metadata, importance)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (args[0], args[1], args[2], int(time.time()),
                 args[3], args[4], str(args[5] or {}), args[6])
            )

    def _add_message_temporary(self, *args) -> None:
        """Add message to temporary storage."""
        queue_key = (args[0], args[1])  # user_id, chat_id
        
        if queue_key not in self.queues:
            self.queues[queue_key] = deque(maxlen=self.max_size)
            
        self.queues[queue_key].append({
            'message_id': args[2],
            'timestamp': int(time.time()),
            'role': args[3],
            'content': args[4],
            'metadata': args[5],
            'importance': args[6]
        })

    def clear_context(self, user_id: int, chat_id: Optional[int] = None) -> None:
        """Clear context for user/chat."""
        try:
            if self.storage_type == "permanent":
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
            else:
                queue_key = (user_id, chat_id)
                if chat_id is not None:
                    if queue_key in self.queues:
                        del self.queues[queue_key]
                else:
                    self.queues = {k: v for k, v in self.queues.items() if k[0] != user_id}
        except Exception as e:
            logger.error(f"Error clearing context: {e}")

    def cleanup_old_contexts(self, max_age: int = CONTEXT_RELEVANCE_WINDOW) -> None:
        """Remove contexts older than max_age seconds."""
        try:
            min_time = int((datetime.now() - timedelta(seconds=max_age)).timestamp())
            if self.storage_type == "permanent":
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "DELETE FROM context_queue WHERE timestamp < ?",
                        (min_time,)
                    )
            else:
                for queue in self.queues.values():
                    while queue and queue[0]['timestamp'] < min_time:
                        queue.popleft()
        except Exception as e:
            logger.error(f"Error cleaning up old contexts: {e}")

    def toggle_sliding_window(self, enabled: bool) -> None:
        """Enable or disable sliding window."""
        self.enabled = enabled
        logger.info(f"Sliding window {'enabled' if enabled else 'disabled'}")

    def change_storage_type(self, storage_type: str) -> None:
        """Change storage type between permanent and temporary."""
        if storage_type not in ["permanent", "temporary"]:
            raise ValueError("Invalid storage type")
            
        if storage_type != self.storage_type:
            self.storage_type = storage_type
            
            # Re-initialize storage
            if storage_type == "permanent":
                self._init_db()
            else:
                self.queues = {}
                
            logger.info(f"Changed storage type to: {storage_type}")

    def update_message_relevancy(self, 
                               user_id: int,
                               chat_id: int, 
                               message_id: int,
                               relevancy_score: float) -> None:
        """Update relevancy score for a message."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE context_queue
                    SET relevancy = ?,
                        reference_count = reference_count + 1,
                        last_referenced = ?
                    WHERE user_id = ? AND chat_id = ? AND message_id = ?
                """, (
                    relevancy_score,
                    int(time.time()),
                    user_id, chat_id, message_id
                ))
        except Exception as e:
            logger.error(f"Error updating message relevancy: {e}")

# Create singleton instance
context_queue = ContextQueue()
