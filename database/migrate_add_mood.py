"""Database migration script for adding mood system columns."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_add_mood_columns():
    migration_sql = """
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS current_mood VARCHAR(20) DEFAULT 'neutral',
    ADD COLUMN IF NOT EXISTS mood_intensity SMALLINT DEFAULT 50,
    ADD COLUMN IF NOT EXISTS last_mood_change DATETIME DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS mood_history JSON;
    """
    
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_user_mood ON users(current_mood, mood_intensity);
    """
    
    try:
        with engine.connect() as conn:
            logger.info("Adding mood columns to users table...")
            conn.execute(text(migration_sql))
            conn.commit()
            
            logger.info("Creating mood index...")
            conn.execute(text(index_sql))
            conn.commit()
            
            logger.info("Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("MOOD SYSTEM DATABASE MIGRATION")
    if input("Continue with migration? (yes/no): ").lower() in ['yes', 'y']:
        migrate_add_mood_columns()
    else:
        print("Migration cancelled.")
