"""
SQLAlchemy session management for database operations.
"""
import logging
from contextlib import contextmanager
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config.settings import SQLITE_DB_PATH

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with connection to SQLite database
DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create sessionmaker that will produce sessions using this engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy model classes
Base = declarative_base()

def get_db_session() -> Generator[Session, None, None]:
    """
    Create and yield a SQLAlchemy session.
    
    Yields:
        Session: SQLAlchemy session for database operations
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_session_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Provides a more intuitive way to use sessions with 'with' statements.
    
    Yields:
        Session: SQLAlchemy session for database operations
    
    Example:
        with db_session_context() as session:
            user = session.query(User).filter(User.id == user_id).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed: {str(e)}")
        raise
    finally:
        session.close()


def execute_with_session(operation: callable, *args: Any, **kwargs: Any) -> Any:
    """
    Execute a database operation with a session and proper error handling.
    
    Args:
        operation: Callable that accepts a session as its first argument
        *args: Additional positional arguments to pass to the operation
        **kwargs: Additional keyword arguments to pass to the operation
        
    Returns:
        Any: Result of the database operation
        
    Example:
        def get_user(session, user_id):
            return session.query(User).filter(User.id == user_id).first()
        
        user = execute_with_session(get_user, user_id=123)
    """
    with db_session_context() as session:
        return operation(session, *args, **kwargs)
    
def initialize_database() -> None:
    """Initialize database schema with SQLAlchemy models.
    
    This function ensures SQLAlchemy models are synced with the database.
    Low-level column compatibility is handled by DatabaseManager.
    """
    logger.info("Creating tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    logger.info("SQLAlchemy tables created successfully")

# For backward compatibility - alias the old function name
ensure_database_schema = initialize_database