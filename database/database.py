"""
Database Utilities for Alya Bot.

This module provides centralized database functions including connections,
error handling, backup, and rotation for SQLite databases.
"""

import os
import sqlite3
import logging
import time
import shutil
import datetime
from typing import Optional, Dict, Any, List, Tuple, Union

logger = logging.getLogger(__name__)

# Database paths
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "data", "alya.db")
CONTEXT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "context", "alya_context.db")

class DatabaseManager:
    """
    Manager for database connections and operations.
    
    This class provides centralized database management including
    connections, error handling, and maintenance operations.
    """
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure data directory exists
        data_dir = os.path.dirname(db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        # Initialize database
        self._init_db()
        
    def _init_db(self) -> None:
        """Initialize database schema if not exists."""
        conn = self.get_connection()
        try:
            with conn:
                # Basic user data table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT,
                    first_seen INTEGER,
                    last_activity INTEGER,
                    interaction_count INTEGER DEFAULT 0
                )
                """)
                
                # User context table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS user_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    context_type TEXT,
                    context_data TEXT,
                    created_at INTEGER,
                    expires_at INTEGER,
                    UNIQUE(user_id, chat_id, context_type)
                )
                """)
                
                # Chat history table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    role TEXT,
                    content TEXT,
                    message_id INTEGER,
                    timestamp INTEGER,
                    importance REAL DEFAULT 1.0
                )
                """)
                
                # Personal facts table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS personal_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    fact_key TEXT,
                    fact_value TEXT,
                    confidence REAL,
                    source TEXT,
                    created_at INTEGER,
                    expires_at INTEGER,
                    UNIQUE(user_id, fact_key)
                )
                """)
                
                # Fix missing columns in chat_history table
                try:
                    # Check if columns exist
                    check_result = conn.execute("PRAGMA table_info(chat_history)").fetchall()
                    columns = [col[1] for col in check_result]
                    
                    # Add metadata column if missing
                    if "metadata" not in columns:
                        logger.info("Adding 'metadata' column to chat_history table")
                        conn.execute("ALTER TABLE chat_history ADD COLUMN metadata TEXT")
                    
                    # Add token_count column if missing
                    if "token_count" not in columns:
                        logger.info("Adding 'token_count' column to chat_history table")
                        conn.execute("ALTER TABLE chat_history ADD COLUMN token_count INTEGER DEFAULT 0")
                except sqlite3.Error as e:
                    logger.error(f"Error checking/adding columns: {e}")
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_context_user_id ON user_context(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_personal_facts_user_id ON personal_facts(user_id)")
                
                logger.debug("Database schema initialized")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
        finally:
            conn.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with proper settings.
        
        Returns:
            SQLite connection object
        """
        try:
            # Connect with foreign keys and row factory
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
            
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as dictionaries.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.execute(query, params or ())
                # Convert results to dict
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Query execution error: {e}")
            return []
        finally:
            conn.close()
            
    def execute_write(self, query: str, params: Optional[Tuple] = None) -> bool:
        """
        Execute a write query (INSERT/UPDATE/DELETE).
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(query, params or ())
                return True
        except sqlite3.Error as e:
            logger.error(f"Write operation error: {e}")
            return False
        finally:
            conn.close()
            
    def create_backup(self, backup_suffix: Optional[str] = None) -> str:
        """
        Create a backup of the database.
        
        Args:
            backup_suffix: Optional suffix for backup filename
            
        Returns:
            Path to backup file
        """
        if not os.path.exists(self.db_path):
            logger.warning("Database file doesn't exist, nothing to back up")
            return ""
            
        # Generate backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{backup_suffix}" if backup_suffix else ""
        backup_filename = f"alya_backup_{timestamp}{suffix}.db"
        
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return ""
            
    def rotate_database(self) -> bool:
        """
        Rotate database (create backup and initialize new).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup
            self.create_backup("rotation")
            
            # Close any existing connections (best effort)
            conn = sqlite3.connect(self.db_path)
            conn.close()
            
            # Rename current database
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = f"{self.db_path}.{timestamp}"
            os.rename(self.db_path, archive_path)
            
            # Initialize new database
            self._init_db()
            
            logger.info(f"Database rotated successfully, old db at: {archive_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error during database rotation: {e}")
            return False
            
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with database statistics
        """
        stats = {
            "db_size_mb": 0,
            "tables": {},
            "user_count": 0,
            "oldest_record_days": 0,
            "newest_record_days": 0
        }
        
        try:
            # Get database file size
            if os.path.exists(self.db_path):
                size_bytes = os.path.getsize(self.db_path)
                stats["db_size_mb"] = size_bytes / (1024 * 1024)
            
            # Get table counts
            conn = self.get_connection()
            try:
                with conn:
                    # Get list of tables
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    
                    for table in tables:
                        table_name = table[0]
                        if table_name.startswith('sqlite_'):
                            continue
                            
                        # Get row count
                        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                        stats["tables"][table_name] = count
                        
                    # Get user count
                    stats["user_count"] = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_context").fetchone()[0]
                    
                    # Get age of oldest and newest records
                    current_time = time.time()
                    
                    # Oldest record
                    oldest_query = """
                    SELECT MIN(created_at) as oldest_time 
                    FROM (
                        SELECT MIN(created_at) as created_at FROM user_context WHERE created_at > 0
                        UNION
                        SELECT MIN(timestamp) as created_at FROM chat_history WHERE timestamp > 0
                    )
                    """
                    oldest_result = conn.execute(oldest_query).fetchone()
                    if oldest_result and oldest_result[0]:
                        days_old = (current_time - oldest_result[0]) / 86400
                        stats["oldest_record_days"] = days_old
                    
                    # Newest record
                    newest_query = """
                    SELECT MAX(created_at) as newest_time 
                    FROM (
                        SELECT MAX(created_at) as created_at FROM user_context
                        UNION
                        SELECT MAX(timestamp) as created_at FROM chat_history
                    )
                    """
                    newest_result = conn.execute(newest_query).fetchone()
                    if newest_result and newest_result[0]:
                        days_old = (current_time - newest_result[0]) / 86400
                        stats["newest_record_days"] = days_old
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            
        return stats

# Function to initialize the database with proper schema
def init_database() -> None:
    """
    Initialize the database with proper schema.
    
    This is the main entry point for ensuring the database is ready.
    """
    # Ensure context database directory exists
    context_dir = os.path.dirname(CONTEXT_DB_PATH)
    if not os.path.exists(context_dir):
        os.makedirs(context_dir)
    
    # Initialize the context database with the context manager
    context_db_manager = DatabaseManager(CONTEXT_DB_PATH)
    context_db_manager._init_db()
    logger.info(f"Context database initialized at {CONTEXT_DB_PATH}")
    
    # Also initialize the main database
    main_db_manager = DatabaseManager(DEFAULT_DB_PATH)
    main_db_manager._init_db()
    logger.info(f"Main database initialized at {DEFAULT_DB_PATH}")

# Create a singleton database manager
db_manager = DatabaseManager()

def get_connection() -> sqlite3.Connection:
    """
    Get database connection (convenience function).
    
    Returns:
        SQLite connection object
    """
    return db_manager.get_connection()

def execute_query(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query (convenience function).
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of result rows as dictionaries
    """
    return db_manager.execute_query(query, params)
