"""
Session management for database connections using SQLAlchemy.
"""
import logging
import os
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config.settings import SQLITE_DB_PATH

logger = logging.getLogger(__name__)

# Create base class for SQLAlchemy models
Base = declarative_base()

# Create engine based on DB path from settings
db_path = SQLITE_DB_PATH
if not db_path:
    db_path = os.path.join("data", "alya.db")

db_url = f"sqlite:///{db_path}"
engine = create_engine(
    db_url, 
    connect_args={"check_same_thread": False},  # Needed for SQLite
    pool_pre_ping=True,  # Check connection before using from pool
    echo=False  # Set to True for SQL query logging
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Generator[Session, None, None]:
    """Get a database session.
    
    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Initialize database with tables."""
    try:
        # Import models to ensure they're registered with Base
        from database.models import User, Conversation, ConversationSummary, BotConfig
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
