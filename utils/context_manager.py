"""
Context Manager for Alya Telegram Bot.

This module handles persistent context for commands and chat history
using SQLite database to store data for 1 week.
"""
import os
import sqlite3
import json
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class ContextManager:
    """Manager for chat and command context using SQLite."""
    
    def __init__(self, db_path="data/context/alya_context.db", ttl=7776000):  # 90 days
        """
        Initialize context manager.
        
        Args:
            db_path: Path to SQLite database file
            ttl: Time-to-live in seconds (default: 1 week)
        """
        self.db_path = db_path
        self.ttl = ttl
        self._conn = None
        self._lock = threading.RLock()
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # Setup database and tables
        self._init_db()
        
    def _get_conn(self):
        """Get thread-local database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            # Enable foreign keys and return dict rows
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.row_factory = sqlite3.Row
        return self._conn
        
    def _init_db(self):
        """Initialize database tables if they don't exist."""
        conn = self._get_conn()
        with conn:
            # Check if user_context table exists and has chat_id column
            table_info = conn.execute("PRAGMA table_info(user_context)").fetchall()
            if table_info:  # Table exists
                # Check if chat_id column exists
                has_chat_id = any(row['name'] == 'chat_id' for row in table_info)
                
                if not has_chat_id:
                    # Add chat_id column to existing table
                    logger.info("Upgrading database: Adding chat_id column to user_context table")
                    try:
                        conn.execute('ALTER TABLE user_context ADD COLUMN chat_id INTEGER DEFAULT 0')
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Cannot add chat_id column: {e} - will use default chat_id=0")
            else:
                # Create new table with chat_id column
                conn.execute('''
                CREATE TABLE IF NOT EXISTS user_context (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL DEFAULT 0,
                    command_type TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    PRIMARY KEY (user_id, chat_id, command_type)
                )
                ''')
            
            # Create index for quick cleanup if needed
            conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON user_context(timestamp)
            ''')
            
            # Table for chat history
            conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                PRIMARY KEY (user_id, chat_id, message_id)
            )
            ''')
            
            conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_timestamp 
            ON chat_history(timestamp)
            ''')
            
            # Table for personal facts (long-term memory)
            conn.execute('''
            CREATE TABLE IF NOT EXISTS user_facts (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                fact_type TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                importance INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, chat_id, fact_type)
            )
            ''')
    
    def _check_and_rotate_db(self):
        """Check database size and rotate if needed."""
        # Check if current DB exists
        if os.path.exists(self.db_path):
            # Calculate size in MB
            size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            
            # If DB is too large, rotate it
            if size_mb > self.max_db_size_mb:
                self._rotate_database()
    
    def _rotate_database(self):
        """Rotate database by creating a date-based backup and starting fresh."""
        try:
            # Close any existing connection
            if self._conn:
                self._conn.close()
                self._conn = None
            
            # Create backup with date
            current_date = datetime.now().strftime("%Y%m%d")
            backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filename with date
            backup_path = os.path.join(
                backup_dir, 
                f"alya_context_{current_date}.db"
            )
            
            # If backup already exists for today, add hour-minute
            if os.path.exists(backup_path):
                current_time = datetime.now().strftime("%H%M")
                backup_path = os.path.join(
                    backup_dir, 
                    f"alya_context_{current_date}_{current_time}.db"
                )
            
            # Copy the existing database to backup
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database rotated: Backup created at {backup_path}")
            
            # Remove the old database to start fresh
            os.remove(self.db_path)
            
            # Clean up old backups (keep last 5)
            self._cleanup_old_backups(backup_dir, keep=5)
            
        except Exception as e:
            logger.error(f"Error rotating database: {e}")
    
    def _cleanup_old_backups(self, backup_dir, keep=5):
        """Remove old database backups, keeping only the most recent ones."""
        try:
            # Get all backup files
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith("alya_context_")]
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
            
            # Remove older backups beyond the keep limit
            if len(backup_files) > keep:
                for old_file in backup_files[keep:]:
                    os.remove(os.path.join(backup_dir, old_file))
                    logger.info(f"Removed old backup: {old_file}")
        
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def save_context(self, user_id: int, chat_id: int, command_type: str, 
                   context_data: Dict[str, Any]) -> bool:
        """
        Save command context to database.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            command_type: Command type ('trace', 'sauce', 'search', etc.)
            context_data: Context data dictionary
            
        Returns:
            True if successful, False if failed
        """
        try:
            conn = self._get_conn()
            with conn:
                try:
                    # Try with chat_id first
                    conn.execute(
                        '''
                        INSERT OR REPLACE INTO user_context 
                        (user_id, chat_id, command_type, context_data, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (user_id, chat_id, command_type, json.dumps(context_data), int(time.time()))
                    )
                except sqlite3.OperationalError:
                    # Fallback to old schema without chat_id
                    logger.info("Falling back to old schema without chat_id")
                    conn.execute(
                        '''
                        INSERT OR REPLACE INTO user_context 
                        (user_id, command_type, context_data, timestamp)
                        VALUES (?, ?, ?, ?)
                        ''',
                        (user_id, command_type, json.dumps(context_data), int(time.time()))
                    )
            return True
        except Exception as e:
            logger.error(f"Error saving context: {e}")
            return False
    
    def get_context(self, user_id: int, chat_id: int, command_type: str = None) -> Optional[Dict]:
        """
        Retrieve context from database.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            command_type: Command type. If None, returns all user context
            
        Returns:
            Context data dictionary or None if not found
        """
        try:
            conn = self._get_conn()
            with conn:
                # Check if chat_id column exists
                try:
                    if command_type:
                        # First try with chat_id
                        try:
                            row = conn.execute(
                                '''
                                SELECT context_data, timestamp FROM user_context
                                WHERE user_id = ? AND chat_id = ? AND command_type = ?
                                ''',
                                (user_id, chat_id, command_type)
                            ).fetchone()
                        except sqlite3.OperationalError:
                            # Fallback to old schema
                            row = conn.execute(
                                '''
                                SELECT context_data, timestamp FROM user_context
                                WHERE user_id = ? AND command_type = ?
                                ''',
                                (user_id, command_type)
                            ).fetchone()
                        
                        if not row:
                            return None
                            
                        # Check if expired
                        now = int(time.time())
                        if now - row['timestamp'] > self.ttl:
                            self._delete_context(user_id, chat_id, command_type)
                            return None
                            
                        return json.loads(row['context_data'])
                    else:
                        # Get all contexts for user
                        try:
                            rows = conn.execute(
                                '''
                                SELECT command_type, context_data, timestamp FROM user_context
                                WHERE user_id = ? AND chat_id = ?
                                ''',
                                (user_id, chat_id)
                            ).fetchall()
                        except sqlite3.OperationalError:
                            # Fallback to old schema
                            rows = conn.execute(
                                '''
                                SELECT command_type, context_data, timestamp FROM user_context
                                WHERE user_id = ?
                                ''',
                                (user_id,)
                            ).fetchall()
                        
                        contexts = {}
                        now = int(time.time())
                        for row in rows:
                            if now - row['timestamp'] <= self.ttl:
                                contexts[row['command_type']] = json.loads(row['context_data'])
                            else:
                                self._delete_context(user_id, chat_id, row['command_type'])
                        
                        return contexts if contexts else None
                except Exception as inner_error:
                    logger.error(f"Error in database query: {inner_error}")
                    return None
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return None

    def _delete_context(self, user_id: int, chat_id: int, command_type: str) -> bool:
        """Delete specific context."""
        try:
            conn = self._get_conn()
            with conn:
                try:
                    conn.execute(
                        '''
                        DELETE FROM user_context
                        WHERE user_id = ? AND chat_id = ? AND command_type = ?
                        ''',
                        (user_id, chat_id, command_type)
                    )
                except sqlite3.OperationalError:
                    # Fallback to old schema
                    conn.execute(
                        '''
                        DELETE FROM user_context
                        WHERE user_id = ? AND command_type = ?
                        ''',
                        (user_id, command_type)
                    )
            return True
        except Exception as e:
            logger.error(f"Error deleting context: {e}")
            return False
    
    def add_chat_message(self, user_id: int, chat_id: int, message_id: int, 
                        role: str, content: str) -> bool:
        """
        Add message to chat history.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            message_id: Telegram message ID (0 for bot responses)
            role: Message role ('user' or 'assistant')
            content: Message content
            
        Returns:
            True if successful, False if failed
        """
        try:
            conn = self._get_conn()
            with conn:
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO chat_history
                    (user_id, chat_id, message_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (user_id, chat_id, message_id, role, content, int(time.time()))
                )
            return True
        except Exception as e:
            logger.error(f"Error adding chat message: {e}")
            return False
    
    def get_chat_history(self, user_id: int, chat_id: int, limit: int = 10) -> List[Dict]:
        """
        Get user chat history.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            limit: Maximum number of messages
            
        Returns:
            List of chat history entries
        """
        try:
            conn = self._get_conn()
            with conn:
                rows = conn.execute(
                    '''
                    SELECT message_id, role, content, timestamp FROM chat_history
                    WHERE user_id = ? AND chat_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    ''',
                    (user_id, chat_id, limit)
                ).fetchall()
                
                # Convert to list and filter expired ones
                history = []
                now = int(time.time())
                for row in rows:
                    if now - row['timestamp'] <= self.ttl:
                        history.append({
                            'message_id': row['message_id'],
                            'role': row['role'],
                            'content': row['content'],
                            'timestamp': row['timestamp']
                        })
                        
                # Sort chronologically (oldest first)
                return list(reversed(history))
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
    
    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Delete expired entries.
        
        Returns:
            Tuple (context_count, history_count) number of deleted items
        """
        try:
            conn = self._get_conn()
            with conn:
                expire_time = int(time.time()) - self.ttl
                
                # Delete expired contexts
                cursor = conn.execute(
                    'DELETE FROM user_context WHERE timestamp < ?',
                    (expire_time,)
                )
                context_count = cursor.rowcount
                
                # Delete expired chat history
                cursor = conn.execute(
                    'DELETE FROM chat_history WHERE timestamp < ?',
                    (expire_time,)
                )
                history_count = cursor.rowcount
                
                return (context_count, history_count)
        except Exception as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return (0, 0)
    
    def save_personal_fact(self, user_id: int, chat_id: int, fact_type: str, fact_value: str, importance: int = 1) -> bool:
        """
        Save important personal facts about users (longer TTL than context).
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            fact_type: Type of fact (birthday, name, hobby, etc.)
            fact_value: Value of the fact
            importance: Importance level (1-5, higher = more important)
            
        Returns:
            True if successful, False if failed
        """
        try:
            conn = self._get_conn()
            with conn:
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO user_facts
                    (user_id, chat_id, fact_type, fact_value, timestamp, importance)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (user_id, chat_id, fact_type, fact_value, int(time.time()), importance)
                )
            return True
        except Exception as e:
            logger.error(f"Error saving personal fact: {e}")
            return False
    
    def get_personal_facts(self, user_id: int, chat_id: int) -> Dict[str, str]:
        """
        Get all personal facts about a user.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            
        Returns:
            Dictionary of fact_type -> fact_value
        """
        try:
            conn = self._get_conn()
            with conn:
                rows = conn.execute(
                    '''
                    SELECT fact_type, fact_value FROM user_facts
                    WHERE user_id = ? AND chat_id = ?
                    ''',
                    (user_id, chat_id)
                ).fetchall()
                
                facts = {}
                for row in rows:
                    facts[row['fact_type']] = row['fact_value']
                
                return facts
        except Exception as e:
            logger.error(f"Error getting personal facts: {e}")
            return {}
    
    def get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {
                'db_size_mb': 0,
                'user_context_count': 0,
                'chat_history_count': 0,
                'user_facts_count': 0,
                'oldest_record_days': 0,
                'newest_record_days': 0,
            }
            
            if os.path.exists(self.db_path):
                stats['db_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            conn = self._get_conn()
            with conn:
                # Count records in each table
                cursor = conn.execute("SELECT COUNT(*) FROM user_context")
                stats['user_context_count'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM chat_history")
                stats['chat_history_count'] = cursor.fetchone()[0]
                
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM user_facts")
                    stats['user_facts_count'] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    # Table might not exist
                    stats['user_facts_count'] = 0
                
                # Get oldest and newest records
                now = int(time.time())
                
                try:
                    cursor = conn.execute("""
                    SELECT MIN(timestamp) FROM (
                        SELECT timestamp FROM user_context
                        UNION 
                        SELECT timestamp FROM chat_history
                    )
                    """)
                    oldest = cursor.fetchone()[0]
                    if oldest:
                        stats['oldest_record_days'] = (now - oldest) / (24 * 3600)
                except:
                    pass
                
                try:
                    cursor = conn.execute("""
                    SELECT MAX(timestamp) FROM (
                        SELECT timestamp FROM user_context
                        UNION 
                        SELECT timestamp FROM chat_history
                    )
                    """)
                    newest = cursor.fetchone()[0]
                    if newest:
                        stats['newest_record_days'] = (now - newest) / (24 * 3600)
                except:
                    pass
                
            return stats
        except Exception as e:
            logger.error(f"Error getting DB stats: {e}")
            return {}

class ShardedContextManager:
    """Sharded context manager that splits users across multiple database files."""
    
    def __init__(self, base_path="data/context", ttl=7776000, shards=10):
        self.base_path = base_path
        self.ttl = ttl
        self.shards = shards
        self.managers = {}
        
        # Create directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        
        # Initialize shard managers
        for i in range(shards):
            db_path = os.path.join(base_path, f"alya_context_shard_{i}.db")
            self.managers[i] = ContextManager(db_path=db_path, ttl=ttl)
    
    def _get_shard(self, user_id):
        """Determine which shard to use based on user_id."""
        return user_id % self.shards
        
    def save_context(self, user_id, chat_id, command_type, context_data):
        """Save context to appropriate shard."""
        shard = self._get_shard(user_id)
        return self.managers[shard].save_context(user_id, chat_id, command_type, context_data)
    
    def get_context(self, user_id, chat_id, command_type=None):
        """Get context from appropriate shard."""
        shard = self._get_shard(user_id)
        return self.managers[shard].get_context(user_id, chat_id, command_type)
        
    # ...implement other methods that delegate to the appropriate shard...
    
    def cleanup_expired(self):
        """Run cleanup on all shards."""
        total_context = 0
        total_history = 0
        
        for manager in self.managers.values():
            context_count, history_count = manager.cleanup_expired()
            total_context += context_count
            total_history += history_count
            
        return total_context, total_history

# Singleton instance
context_manager = ContextManager()