"""
Database migration: Add voice_language column to users table.

This migration adds the voice_language column to track user's preferred
voice response language separately from interface language.

Run this from the project root directory:
python database/migrate_add_voice_language.py
"""
import sys
import os
import logging

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, String, text
from database.session import db_session_context, engine
from database.models import User
from config.settings import DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


def migrate_add_voice_language():
    """Add voice_language column to users table."""
    try:
        # Check if column already exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'voice_language' in columns:
            logger.info("✅ voice_language column already exists, skipping migration")
            return True
        
        logger.info("🔄 Adding voice_language column to users table...")
        
        # Add column using raw SQL
        with engine.connect() as conn:
            conn.execute(
                text(f"ALTER TABLE users ADD COLUMN voice_language VARCHAR(10) DEFAULT '{DEFAULT_LANGUAGE}' AFTER language_code")
            )
            conn.execute(
                text("CREATE INDEX idx_users_voice_language ON users(voice_language)")
            )
            conn.commit()
        
        logger.info("✅ Successfully added voice_language column")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding voice_language column: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎙️ Voice Language Migration")
    print("=" * 50)
    print("This will add the voice_language column to the users table.")
    print("This allows separate voice language settings from interface language.")
    print()
    
    success = migrate_add_voice_language()
    
    if success:
        print()
        print("✅ Migration completed successfully!")
        print()
        print("New features available:")
        print("  1. /voicelang en - Set English voice responses")  
        print("  2. /voicelang id - Set Indonesian voice responses")
        print("  3. /voicelang ja - Set Japanese voice responses") 
        print("  4. /lang en/id - Still controls interface language")
        print()
        print("Example: /lang id + /voicelang ja = Indonesian interface + Japanese voice")
    else:
        print()
        print("❌ Migration failed! Check the logs for details.")