#!/usr/bin/env python3
"""
Enterprise-grade database initialization script for Alya Bot.
This script creates the MySQL database, tables, and performs initial setup.
"""
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config.settings import DATABASE_URL, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME
    from database.session import engine, Base, initialize_database, health_check, get_connection_info
    from database.models import User, Conversation, ConversationSummary, ApiUsage
    import mysql.connector
    from mysql.connector import Error
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_database() -> bool:
    """
    Create the database if it doesn't exist.
    
    Returns:
        bool: True if database exists or was created successfully
    """
    try:
        # Connect without specifying database
        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        cursor = connection.cursor()
        
        # Create database with proper charset
        cursor.execute(f"""
            CREATE DATABASE IF NOT EXISTS `{DB_NAME}` 
            CHARACTER SET utf8mb4 
            COLLATE utf8mb4_unicode_ci
        """)
        
        logger.info(f"✅ Database '{DB_NAME}' created or already exists")
        
        # Verify charset and collation
        cursor.execute(f"""
            SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME 
            FROM information_schema.SCHEMATA 
            WHERE SCHEMA_NAME = '{DB_NAME}'
        """)
        
        result = cursor.fetchone()
        if result:
            charset, collation = result
            logger.info(f"📝 Database charset: {charset}, collation: {collation}")
            
            if charset != 'utf8mb4':
                logger.warning("⚠️  Database charset is not utf8mb4. This may cause issues with emoji support.")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        logger.error(f"❌ Error creating database: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def create_tables() -> bool:
    """
    Create all tables using SQLAlchemy models.
    
    Returns:
        bool: True if tables were created successfully
    """
    try:
        logger.info("🔨 Creating database tables...")
        
        # Initialize database schema
        initialize_database()
        
        # Verify tables were created
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = :db_name
                ORDER BY TABLE_NAME
            """), {"db_name": DB_NAME})
            
            tables = [row[0] for row in result.fetchall()]
            
        if tables:
            logger.info(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
            return True
        else:
            logger.error("❌ No tables were created")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        return False


def verify_connection() -> bool:
    """
    Verify database connection and setup.
    
    Returns:
        bool: True if connection is working properly
    """
    try:
        logger.info("🔍 Verifying database connection...")
        
        # Perform health check
        if not health_check():
            logger.error("❌ Database health check failed")
            return False
        
        # Get connection info
        conn_info = get_connection_info()
        logger.info(f"📊 Connection pool stats:")
        logger.info(f"   - Pool size: {conn_info['pool_size']}")
        logger.info(f"   - Checked out: {conn_info['checked_out']}")
        logger.info(f"   - Database URL: {conn_info['url']}")
        
        logger.info("✅ Database connection verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying connection: {e}")
        return False


def show_usage_instructions():
    """Show usage instructions for the database."""
    print("\n" + "="*60)
    print("🌸 Alya Bot Database Setup Complete! 🌸")
    print("="*60)
    print()
    print("📝 Environment Variables Required:")
    print(f"   DB_HOST={DB_HOST}")
    print(f"   DB_PORT={DB_PORT}")
    print(f"   DB_USERNAME={DB_USERNAME}")
    print(f"   DB_PASSWORD=***")
    print(f"   DB_NAME={DB_NAME}")
    print()
    print("🔧 Usage Examples:")
    print("   # Start the bot")
    print("   python main.py")
    print()
    print("   # Reset user conversation")
    print("   python -c \"from database.database_manager import db_manager; db_manager.reset_conversation(USER_ID)\"")
    print()
    print("   # Get database stats")
    print("   python -c \"from database.database_manager import db_manager; print(db_manager.get_database_stats())\"")
    print()
    print("🚀 Ready to deploy Alya Bot!")
    print("="*60)


def main():
    """Main initialization function."""
    print("🌸 Initializing Alya Bot Database 🌸")
    print()
    
    # Step 1: Validate configuration
    logger.info("🔧 Validating configuration...")
    
    if not all([DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME]):
        logger.error("❌ Missing required database configuration")
        logger.error("Please check your .env file for: DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME")
        sys.exit(1)
    
    logger.info(f"📡 Connecting to MySQL at {DB_HOST}:{DB_PORT}")
    
    # Step 2: Create database
    if not create_database():
        logger.error("❌ Failed to create database")
        sys.exit(1)
    
    # Step 3: Create tables
    if not create_tables():
        logger.error("❌ Failed to create tables")
        sys.exit(1)
    
    # Step 4: Verify connection
    if not verify_connection():
        logger.error("❌ Failed to verify connection")
        sys.exit(1)
    
    # Step 5: Show success message
    show_usage_instructions()


if __name__ == "__main__":
    main()
