#!/usr/bin/env python3
"""
Database initialization script for Alya Bot v2.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from config.settings import settings
from app.infrastructure.database import create_tables, create_database_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize database tables."""
    try:
        logger.info("🗄️  Initializing Alya Bot v2 Database...")
        logger.info(f"Database: {settings.db_name}")
        logger.info(f"Host: {settings.db_host}:{settings.db_port}")
        
        # Test database connection
        engine = create_database_engine()
        with engine.connect() as conn:
            logger.info("✅ Database connection successful")
        
        # Create tables
        create_tables()
        logger.info("✅ Database tables created successfully")
        
        logger.info("🎉 Database initialization completed!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
