"""
Database migration: Add voice_enabled column to users table.

This migration adds the voice_enabled column to track which users
have access to the voice/TTS feature.
"""
import logging
from sqlalchemy import Boolean, Column
from database.session import db_session_context, engine
from database.models import User

logger = logging.getLogger(__name__)


def migrate_add_voice_enabled():
    """Add voice_enabled column to users table."""
    try:
        # Check if column already exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'voice_enabled' in columns:
            logger.info("✅ voice_enabled column already exists, skipping migration")
            return True
        
        logger.info("🔄 Adding voice_enabled column to users table...")
        
        # Add column using raw SQL
        with engine.connect() as conn:
            conn.execute(
                "ALTER TABLE users ADD COLUMN voice_enabled BOOLEAN DEFAULT FALSE"
            )
            conn.execute(
                "CREATE INDEX idx_users_voice_enabled ON users(voice_enabled)"
            )
            conn.commit()
        
        logger.info("✅ Successfully added voice_enabled column")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding voice_enabled column: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎤 Voice Feature Migration")
    print("=" * 50)
    print("This will add the voice_enabled column to the users table.")
    print()
    
    success = migrate_add_voice_enabled()
    
    if success:
        print()
        print("✅ Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Use /voiceadd <user_id> to grant voice access")
        print("  2. Use /voicelist to see all whitelisted users")
        print("  3. Use /voiceremove <user_id> to revoke access")
    else:
        print()
        print("❌ Migration failed! Check the logs for details.")
