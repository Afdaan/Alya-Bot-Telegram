"""
Database schema manager for Alya Bot.

This module manages database schema migrations and optimizations.
"""

import os
import re
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manages database schema and migrations for Alya Bot."""
    
    def __init__(self, db_path: str, migrations_dir: str):
        """
        Initialize the schema manager.
        
        Args:
            db_path: Path to SQLite database file
            migrations_dir: Directory containing SQL migration files
        """
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self._ensure_dirs()
    
    def _ensure_dirs(self) -> None:
        """Ensure database and migration directories exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.migrations_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection to the database."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Create migrations tracking table if it doesn't exist."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at INTEGER NOT NULL
            )
        """)
        conn.commit()
    
    def _get_applied_migrations(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of already applied migrations."""
        self._create_migrations_table(conn)
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    
    def _get_migration_files(self) -> List[Tuple[str, str]]:
        """Get sorted list of migration files from migrations directory."""
        if not os.path.exists(self.migrations_dir):
            return []
            
        migration_pattern = r'^(\d+)_(.+)\.sql$'
        migrations = []
        
        for filename in os.listdir(self.migrations_dir):
            match = re.match(migration_pattern, filename)
            if match:
                version = match.group(1)
                migrations.append((version, os.path.join(self.migrations_dir, filename)))
                
        # Sort by version number
        migrations.sort(key=lambda x: int(x[0]))
        return migrations
    
    def _apply_migration(self, conn: sqlite3.Connection, version: str, file_path: str) -> bool:
        """
        Apply a single migration file.
        
        Args:
            conn: Database connection
            version: Migration version
            file_path: Path to SQL file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
                
            # Execute migration in a transaction
            conn.executescript(sql)
            
            # Record migration
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, int(datetime.now().timestamp()))
            )
            
            conn.commit()
            logger.info(f"Applied migration: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Migration {version} failed: {e}")
            conn.rollback()
            return False
    
    def migrate(self) -> bool:
        """
        Apply pending migrations.
        
        Returns:
            True if all migrations were applied successfully
        """
        conn = self._get_connection()
        try:
            # Get already applied migrations
            applied = self._get_applied_migrations(conn)
            
            # Get migration files
            migrations = self._get_migration_files()
            
            # Apply pending migrations
            for version, file_path in migrations:
                if version not in applied:
                    logger.info(f"Applying migration {version}: {file_path}")
                    if not self._apply_migration(conn, version, file_path):
                        return False
            
            # Create optimized indexes for better query performance
            self._create_optimized_indexes(conn)
            
            # Apply any schema fixes
            self._apply_schema_fixes(conn)
            
            return True
        finally:
            conn.close()
    
    def _create_optimized_indexes(self, conn: sqlite3.Connection) -> None:
        """Create optimized indexes for better query performance."""
        try:
            # First check which indexes already exist to avoid re-creating
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            existing_indexes = {row[0] for row in cursor.fetchall()}
            
            # Create missing indexes
            indexes = [
                ("idx_contexts_user_chat", "CREATE INDEX IF NOT EXISTS idx_contexts_user_chat ON contexts(user_id, chat_id)"),
                ("idx_history_user_chat", "CREATE INDEX IF NOT EXISTS idx_history_user_chat ON history(user_id, chat_id)"),
                ("idx_history_user_timestamp", "CREATE INDEX IF NOT EXISTS idx_history_user_timestamp ON history(user_id, timestamp)"),
                ("idx_history_importance", "CREATE INDEX IF NOT EXISTS idx_history_importance ON history(importance)"),
                ("idx_facts_user_key", "CREATE INDEX IF NOT EXISTS idx_facts_user_key ON personal_facts(user_id, fact_key)"),
                ("idx_facts_expiry", "CREATE INDEX IF NOT EXISTS idx_facts_expiry ON personal_facts(expires_at)")
            ]
            
            for idx_name, idx_query in indexes:
                if idx_name not in existing_indexes:
                    conn.execute(idx_query)
                    logger.debug(f"Created index: {idx_name}")
            
            # Add COVERING indexes for most common queries to speed them up dramatically
            covering_indexes = [
                ("idx_history_recall_covering", 
                 "CREATE INDEX IF NOT EXISTS idx_history_recall_covering ON history(user_id, chat_id, timestamp) INCLUDE(role, content)")
            ]
            
            for idx_name, idx_query in covering_indexes:
                try:
                    if idx_name not in existing_indexes:
                        conn.execute(idx_query)
                        logger.debug(f"Created covering index: {idx_name}")
                except sqlite3.OperationalError:
                    # Older SQLite might not support INCLUDE syntax
                    logger.debug(f"SQLite version doesn't support covering indexes")
                    pass
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    def _apply_schema_fixes(self, conn: sqlite3.Connection) -> None:
        """Apply schema fixes for compatibility."""
        try:
            # Check for context_data column in contexts table
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(contexts)")
            columns = {row[1] for row in cursor.fetchall()}
            
            # Fix schema if context_data missing but context exists
            if 'context_data' not in columns and 'context' in columns:
                logger.info("Fixing contexts table schema - renaming context to context_data")
                conn.executescript("""
                    CREATE TABLE contexts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        context_key TEXT NOT NULL,
                        context_data TEXT NOT NULL,
                        updated_at INTEGER NOT NULL,
                        UNIQUE(user_id, chat_id, context_key)
                    );
                    INSERT INTO contexts_new(id, user_id, chat_id, context_key, context_data, updated_at)
                    SELECT id, user_id, chat_id, 'default', context, updated_at FROM contexts;
                    DROP TABLE contexts;
                    ALTER TABLE contexts_new RENAME TO contexts;
                    CREATE INDEX idx_contexts_user_chat ON contexts(user_id, chat_id);
                """)
        except Exception as e:
            logger.error(f"Error applying schema fixes: {e}")
    
    def create_migration(self, name: str, content: Optional[str] = None) -> str:
        """
        Create a new migration file.
        
        Args:
            name: Migration name (will be sanitized)
            content: Optional SQL content
            
        Returns:
            Path to created migration file
        """
        # Get current migrations to determine next version
        migrations = self._get_migration_files()
        if migrations:
            next_version = int(migrations[-1][0]) + 1
        else:
            next_version = 1
            
        # Sanitize name
        safe_name = re.sub(r'[^a-z0-9_]', '_', name.lower())
        
        # Create filename
        version_str = f"{next_version:03d}"
        filename = f"{version_str}_{safe_name}.sql"
        file_path = os.path.join(self.migrations_dir, filename)
        
        # Create migration file
        with open(file_path, 'w', encoding='utf-8') as f:
            if content:
                f.write(content)
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"-- Migration: {safe_name}\n")
                f.write(f"-- Version: {version_str}\n")
                f.write(f"-- Created: {timestamp}\n\n")
                f.write("-- Write your SQL migration here\n\n")
        
        logger.info(f"Created migration file: {file_path}")
        return file_path
    
    def reset_database(self) -> bool:
        """
        Reset database by dropping all tables and reapplying migrations.
        
        Returns:
            True if reset was successful
        """
        # Create backup
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup.{int(datetime.now().timestamp())}"
            try:
                import shutil
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"Created database backup at {backup_path}")
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")
        
        # Remove existing database
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception as e:
            logger.error(f"Failed to remove database file: {e}")
            return False
            
        # Apply migrations to new database
        return self.migrate()

# Create a singleton instance with config
from config.settings import CONTEXT_DB_PATH

# Set migrations directory
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "database", "migrations")

# Create schema manager instance
schema_manager = SchemaManager(CONTEXT_DB_PATH, MIGRATIONS_DIR)
