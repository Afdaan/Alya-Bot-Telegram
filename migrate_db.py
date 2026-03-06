
import sys
import os
from sqlalchemy import text
from database.session import engine, initialize_database
from config.settings import DEFAULT_LANGUAGE

def migrate():
    print("Checking database schema...")
    try:
        # Initialize database (creates tables if they don't exist)
        initialize_database()
        
        with engine.connect() as connection:
            # Check if voice_language column exists
            result = connection.execute(text("SHOW COLUMNS FROM users LIKE 'voice_language'"))
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                print(f"Adding 'voice_language' column to 'users' table...")
                connection.execute(text(f"ALTER TABLE users ADD COLUMN voice_language VARCHAR(10) DEFAULT '{DEFAULT_LANGUAGE}' AFTER language_code"))
                connection.execute(text("CREATE INDEX idx_users_voice_language ON users (voice_language)"))
                connection.commit()
                print("Successfully added 'voice_language' column.")
            else:
                print("'voice_language' column already exists.")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
