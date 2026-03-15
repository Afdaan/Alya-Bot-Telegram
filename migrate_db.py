
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
            # list of columns to check in 'users' table and their definitions
            # using a list of tuples (name, definition)
            user_columns = [
                ("voice_language", f"VARCHAR(10) DEFAULT '{DEFAULT_LANGUAGE}' AFTER language_code"),
                ("voice_enabled", "BOOLEAN DEFAULT FALSE AFTER topics_discussed"),
                ("current_mood", "VARCHAR(20) DEFAULT 'neutral' AFTER voice_enabled"),
                ("mood_intensity", "SMALLINT DEFAULT 50 AFTER current_mood"),
                ("last_mood_change", "DATETIME AFTER mood_intensity"),
                ("mood_history", "JSON AFTER last_mood_change")
            ]
            
            # Get existing columns
            result = connection.execute(text("SHOW COLUMNS FROM users"))
            existing_columns = [row[0] for row in result.fetchall()]
            
            for col_name, col_def in user_columns:
                if col_name not in existing_columns:
                    print(f"Adding '{col_name}' column to 'users' table...")
                    try:
                        connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        print(f"Successfully added '{col_name}' column.")
                    except Exception as col_err:
                        print(f"Error adding column {col_name}: {col_err}")
                else:
                    print(f"'{col_name}' column already exists.")
            
            # Add indexes for new columns if they don't exist
            # This is a bit more complex to check exactly, so we'll just try/except
            indexes = [
                ("idx_users_voice_language", "voice_language"),
                ("idx_users_voice_enabled", "voice_enabled"),
                ("idx_users_current_mood", "current_mood")
            ]
            
            # Get existing indexes
            idx_result = connection.execute(text("SHOW INDEX FROM users"))
            existing_indexes = [row[2] for row in idx_result.fetchall()]
            
            for idx_name, col_name in indexes:
                if idx_name not in existing_indexes:
                    print(f"Creating index {idx_name}...")
                    try:
                        connection.execute(text(f"CREATE INDEX {idx_name} ON users ({col_name})"))
                        print(f"Successfully created index {idx_name}.")
                    except Exception as idx_err:
                        print(f"Error creating index {idx_name}: {idx_err}")

            connection.commit()
            print("Migration completed successfully.")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
