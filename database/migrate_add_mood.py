"""Database migration script for adding mood system columns."""

import sys
import os
import logging
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_add_mood_columns():
    """Add mood columns to users table safely."""
    try:
        inspector = inspect(engine)
        existing_columns = [c['name'] for c in inspector.get_columns('users')]
        
        with engine.connect() as conn:
            # defined columns to add: name, definition
            new_columns = [
                ("current_mood", "VARCHAR(20) DEFAULT 'neutral'"),
                ("mood_intensity", "SMALLINT DEFAULT 50"),
                ("last_mood_change", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ("mood_history", "JSON")
            ]
            
            for col_name, col_def in new_columns:
                if col_name not in existing_columns:
                    logger.info(f"Adding column '{col_name}'...")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                else:
                    logger.info(f"Column '{col_name}' already exists.")
            
            conn.commit()
            
            # Create index if it doesn't exist
            # Note: Checking for index existence is harder across versions, 
            # safe to try/catch or just let it fail if exists if using raw sql without checks
            # But duplicate index usually doesn't break things as hard as syntax error,
            # actually duplicate index name is an error.
            
            indexes = inspector.get_indexes('users')
            index_names = [i['name'] for i in indexes]
            
            if 'idx_user_mood' not in index_names:
                logger.info("Creating mood index...")
                conn.execute(text("CREATE INDEX idx_user_mood ON users(current_mood, mood_intensity)"))
                conn.commit()
            else:
                logger.info("Index 'idx_user_mood' already exists.")

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
