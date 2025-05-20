"""
Fix database schema for Alya Bot.

This script updates the database schema to match the application code expectations.
"""

import os
import sqlite3
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("schema_fix")

# Get path to database - using the same path as the validator
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "context")
DB_PATH = os.path.join(DATA_DIR, "alya_context.db")

def backup_database():
    """Create a backup of the database before modifying."""
    if not os.path.exists(DB_PATH):
        logger.warning("Database file not found, nothing to backup")
        return False
    
    backup_path = f"{DB_PATH}.bak.{int(time.time())}"
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return False

def fix_contexts_table():
    """Fix the contexts table schema to match application expectations."""
    if not os.path.exists(DB_PATH):
        logger.error("Database file not found")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(contexts)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        # Begin transaction for all changes
        conn.execute("BEGIN TRANSACTION")
        
        # Create new correctly structured table
        if 'contexts' in [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
            # Create new table with correct structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contexts_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    context_key TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(user_id, chat_id, context_key)
                )
            """)
            
            # Copy data if the old table exists and has data
            if 'context' in columns:  # Old schema uses 'context' column
                logger.info("Migrating data from old contexts schema...")
                try:
                    # Copy data with mapping old to new columns
                    cursor.execute("""
                        INSERT INTO contexts_new (user_id, chat_id, context_key, context_data, updated_at)
                        SELECT user_id, chat_id, 'default', context, updated_at FROM contexts
                    """)
                    logger.info(f"Migrated {cursor.rowcount} rows from contexts table")
                except Exception as e:
                    logger.error(f"Error migrating data: {e}")
            
            # Replace old table with new one
            cursor.execute("DROP TABLE contexts")
            cursor.execute("ALTER TABLE contexts_new RENAME TO contexts")
            
            # Create necessary indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contexts_user_chat ON contexts(user_id, chat_id)")
            
            conn.commit()
            logger.info("Successfully fixed contexts table schema")
            return True
            
        else:
            # Table doesn't exist, create it fresh
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    context_key TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(user_id, chat_id, context_key)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contexts_user_chat ON contexts(user_id, chat_id)")
            conn.commit()
            logger.info("Created new contexts table with correct schema")
            return True
            
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info(f"Fixing database schema at {DB_PATH}")
    
    # Backup database first
    if backup_database():
        # Fix contexts table schema
        if fix_contexts_table():
            logger.info("✅ Database schema successfully updated")
            sys.exit(0)
        else:
            logger.error("❌ Failed to update database schema")
            sys.exit(1)
    else:
        logger.error("❌ Couldn't backup database, aborting schema update")
        sys.exit(1)
