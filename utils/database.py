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

from config.settings import (
    MAIN_DB_PURGE_DAYS,
    CONTEXT_DB_PURGE_DAYS,
    USER_HISTORY_PURGE_DAYS,
    INACTIVE_USER_PURGE_DAYS,
    DB_BACKUP_INTERVAL_DAYS,
    DB_MAX_BACKUPS,
    DB_VACUUM_INTERVAL_DAYS
)

logger = logging.getLogger(__name__)

# Database paths
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "data", "alya.db")

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

    def purge_old_records(self) -> Dict[str, int]:
        """
        Purge old records from database according to settings.
        
        Returns:
            Dictionary of counts of purged records by table
        """
        result = {"user_context": 0, "chat_history": 0, "personal_facts": 0, "inactive_users": 0}
        
        try:
            conn = self.get_connection()
            try:
                with conn:
                    current_time = time.time()
                    
                    # Purge old user context (using CONTEXT_DB_PURGE_DAYS)
                    context_cutoff = current_time - (CONTEXT_DB_PURGE_DAYS * 86400)
                    cursor = conn.execute(
                        "DELETE FROM user_context WHERE created_at < ?", 
                        (context_cutoff,)
                    )
                    result["user_context"] = cursor.rowcount
                    
                    # Purge old chat history (using USER_HISTORY_PURGE_DAYS)
                    history_cutoff = current_time - (USER_HISTORY_PURGE_DAYS * 86400)
                    cursor = conn.execute(
                        "DELETE FROM chat_history WHERE timestamp < ?", 
                        (history_cutoff,)
                    )
                    result["chat_history"] = cursor.rowcount
                    
                    # Purge old personal facts (using CONTEXT_DB_PURGE_DAYS)
                    facts_cutoff = current_time - (CONTEXT_DB_PURGE_DAYS * 86400)
                    cursor = conn.execute(
                        "DELETE FROM personal_facts WHERE created_at < ? AND expires_at < ?", 
                        (facts_cutoff, current_time)
                    )
                    result["personal_facts"] = cursor.rowcount
                    
                    # Purge inactive users (using INACTIVE_USER_PURGE_DAYS)
                    if "users" in self._get_table_names(conn):
                        inactive_cutoff = current_time - (INACTIVE_USER_PURGE_DAYS * 86400)
                        cursor = conn.execute(
                            "DELETE FROM users WHERE last_activity < ?", 
                            (inactive_cutoff,)
                        )
                        result["inactive_users"] = cursor.rowcount
                    
                    logger.info(f"Database purged: {result}")
            finally:
                conn.close()
                
            # Run VACUUM to reclaim space (expensive operation)
            self._vacuum_if_needed()
                
            return result
                
        except Exception as e:
            logger.error(f"Error purging old records: {e}")
            return result
    
    def _get_table_names(self, conn: sqlite3.Connection) -> List[str]:
        """
        Get list of table names in database.
        
        Args:
            conn: Active database connection
            
        Returns:
            List of table names
        """
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
    
    def _vacuum_if_needed(self) -> bool:
        """
        Run VACUUM on database to reclaim space if it's time to do so.
        
        Returns:
            True if VACUUM was run
        """
        # Check if we should vacuum now
        last_vacuum_file = f"{self.db_path}.last_vacuum"
        current_time = time.time()
        
        # Check when we last vacuumed
        try:
            if os.path.exists(last_vacuum_file):
                with open(last_vacuum_file, 'r') as f:
                    last_vacuum_time = float(f.read().strip())
                    
                # If it's not time yet, skip
                if current_time - last_vacuum_time < (DB_VACUUM_INTERVAL_DAYS * 86400):
                    return False
        except Exception:
            # If any error, assume we need to vacuum
            pass
            
        # Run VACUUM
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()
            
            # Update last vacuum time
            os.makedirs(os.path.dirname(last_vacuum_file), exist_ok=True)
            with open(last_vacuum_file, 'w') as f:
                f.write(str(current_time))
                
            logger.info(f"Database VACUUM completed for {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error running VACUUM: {e}")
            return False
    
    def maintenance(self) -> Dict[str, Any]:
        """
        Run all database maintenance tasks.
        
        Returns:
            Dictionary with maintenance results
        """
        results = {
            "purge": None,
            "vacuum": False,
            "backup": None,
            "integrity_check": True
        }
        
        try:
            # 1. Purge old records
            results["purge"] = self.purge_old_records()
            
            # 2. Create backup if needed
            backup_file = self._create_backup_if_needed()
            results["backup"] = backup_file if backup_file else None
            
            # 3. Check if VACUUM needed (already called in purge)
            results["vacuum"] = self._vacuum_if_needed()
            
            # 4. Run integrity check
            conn = self.get_connection()
            try:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                results["integrity_check"] = integrity == "ok"
            finally:
                conn.close()
                
            return results
            
        except Exception as e:
            logger.error(f"Error running database maintenance: {e}")
            return results
    
    def _create_backup_if_needed(self) -> Optional[str]:
        """
        Create backup if it's time to do so.
        
        Returns:
            Backup file path if created, None otherwise
        """
        # Check if we should backup now
        last_backup_file = f"{self.db_path}.last_backup"
        current_time = time.time()
        
        # Check when we last backed up
        try:
            if os.path.exists(last_backup_file):
                with open(last_backup_file, 'r') as f:
                    last_backup_time = float(f.read().strip())
                    
                # If it's not time yet, skip
                if current_time - last_backup_time < (DB_BACKUP_INTERVAL_DAYS * 86400):
                    return None
        except Exception:
            # If any error, assume we need to backup
            pass
            
        # Do the backup
        backup_path = self.create_backup("scheduled")
        
        if backup_path:
            # Update last backup time
            os.makedirs(os.path.dirname(last_backup_file), exist_ok=True)
            with open(last_backup_file, 'w') as f:
                f.write(str(current_time))
            
            # Remove old backups if we have too many
            self._prune_old_backups()
            
        return backup_path
    
    def _prune_old_backups(self) -> int:
        """
        Remove old backups to maintain max backups limit.
        
        Returns:
            Number of backups removed
        """
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        if not os.path.exists(backup_dir):
            return 0
            
        # Get list of backup files
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith("alya_backup_") and filename.endswith(".db"):
                full_path = os.path.join(backup_dir, filename)
                backup_files.append((full_path, os.path.getmtime(full_path)))
                
        # Sort by modification time (oldest first)
        backup_files.sort(key=lambda x: x[1])
        
        # Remove oldest backups if we have too many
        removed = 0
        while len(backup_files) > DB_MAX_BACKUPS:
            oldest = backup_files.pop(0)
            try:
                os.remove(oldest[0])
                removed += 1
                logger.debug(f"Removed old backup: {oldest[0]}")
            except Exception as e:
                logger.error(f"Error removing old backup {oldest[0]}: {e}")
                
        return removed

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

# Add convenience function for database maintenance
def run_database_maintenance() -> Dict[str, Any]:
    """
    Run maintenance on all databases.
    
    Returns:
        Dictionary with maintenance results
    """
    results = {}
    
    # Maintain main database
    main_db_manager = DatabaseManager(DEFAULT_DB_PATH)
    results["main_db"] = main_db_manager.maintenance()
    
    # Maintain context database
    context_db_manager = DatabaseManager(CONTEXT_DB_PATH)
    results["context_db"] = context_db_manager.maintenance()
    
    return results
