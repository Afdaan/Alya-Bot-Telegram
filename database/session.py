"""
Enterprise-grade SQLAlchemy session management for MySQL database operations.
Handles connection pooling, transaction management, and error recovery.
"""
import logging
from contextlib import contextmanager
from typing import Generator, Any, Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError, OperationalError

from config.settings import (
    DATABASE_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_POOL_RECYCLE,
    DB_ECHO
)

logger = logging.getLogger(__name__)

# Create engine with production-ready configuration
engine = create_engine(
    DATABASE_URL,
    # Connection Pool Settings
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,        # Test connections before using
    
    # MySQL-specific optimizations
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "use_unicode": True
    },
    
    # Logging and debugging
    echo=DB_ECHO,
    
    # Connection handling
    isolation_level="READ_COMMITTED"
)

# Add connection event listener for better MySQL compatibility
@event.listens_for(engine, "connect")
def set_mysql_mode(dbapi_connection, connection_record):
    """Set MySQL session variables for optimal performance."""
    try:
        with dbapi_connection.cursor() as cursor:
            # Set timezone to UTC for consistency
            cursor.execute("SET time_zone = '+00:00'")
            # Ensure proper character set
            cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            # Set transaction isolation level
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    except Exception as e:
        logger.warning(f"Failed to set MySQL session variables: {e}")

# Create sessionmaker with enterprise configurations
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False      # Don't expire objects after commit
)

# Base class for all SQLAlchemy model classes
Base = declarative_base()

def get_db_session() -> Generator[Session, None, None]:
    """
    Create and yield a SQLAlchemy session with proper error handling.
    
    Yields:
        Session: SQLAlchemy session for database operations
        
    Raises:
        Exception: Database connection or operation errors
    """
    session = SessionLocal()
    try:
        yield session
    except (DisconnectionError, OperationalError) as e:
        logger.error(f"Database connection error: {str(e)}")
        session.rollback()
        # Try to reconnect
        session.close()
        session = SessionLocal()
        raise
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_session_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic transaction handling.
    
    Provides enterprise-grade session management with proper rollback,
    connection recovery, and resource cleanup.
    
    Yields:
        Session: SQLAlchemy session for database operations
    
    Example:
        with db_session_context() as session:
            user = session.query(User).filter(User.id == user_id).first()
            session.add(new_conversation)
            # Auto-commit on success, auto-rollback on error
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except (DisconnectionError, OperationalError) as e:
        session.rollback()
        logger.error(f"Database connection lost: {str(e)}")
        # Connection will be recreated on next request
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed: {str(e)}")
        raise
    finally:
        session.close()


def execute_with_session(operation: callable, *args: Any, **kwargs: Any) -> Any:
    """
    Execute a database operation with proper session management.
    
    Args:
        operation: Callable that takes a session as first argument
        *args: Additional arguments for the operation
        **kwargs: Additional keyword arguments for the operation
        
    Returns:
        Any: Result from the operation
        
    Example:
        def get_user(session, user_id):
            return session.query(User).filter(User.id == user_id).first()
            
        user = execute_with_session(get_user, user_id=123)
    """
    with db_session_context() as session:
        return operation(session, *args, **kwargs)
    

def initialize_database() -> None:
    """
    Initialize database schema and verify connection.
    
    Creates all tables defined in SQLAlchemy models and tests
    the database connection for proper MySQL setup.
    """
    try:
        # Test connection first
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully")
        
        # Verify charset and collation
        with engine.connect() as connection:
            charset_result = connection.execute(text(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = DATABASE()"
            )).fetchone()
            
            if charset_result:
                charset, collation = charset_result
                logger.info(f"Database charset: {charset}, collation: {collation}")
                
                if charset != 'utf8mb4':
                    logger.warning("Database charset is not utf8mb4. Consider changing for emoji support.")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


def health_check() -> bool:
    """
    Perform database health check.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


def get_connection_info() -> dict:
    """
    Get current database connection information.
    
    Returns:
        dict: Connection pool statistics and database info
    """
    try:
        pool = engine.pool
        info = {
            "url": str(engine.url).replace(f":{engine.url.password}@", ":***@")
        }
        
        # Try to get pool stats, fallback gracefully if methods don't exist
        try:
            info["pool_size"] = pool.size()
        except (AttributeError, Exception):
            info["pool_size"] = "unknown"
        
        try:
            info["checked_in"] = pool.checkedin()
        except (AttributeError, Exception):
            info["checked_in"] = "unknown"
            
        try:
            info["checked_out"] = pool.checkedout()
        except (AttributeError, Exception):
            info["checked_out"] = "unknown"
            
        try:
            info["overflow"] = pool.overflow()
        except (AttributeError, Exception):
            info["overflow"] = "unknown"
        
        return info
        
    except Exception as e:
        return {
            "error": str(e),
            "url": "unknown"
        }


# For backward compatibility - alias the old function name
ensure_database_schema = initialize_database