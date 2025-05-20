"""
Logging configuration for Alya Telegram Bot.

This module sets up logging configuration with appropriate handlers and filters.
"""
import logging
import os
import sys
from typing import Dict, Optional
from functools import wraps

# Default log level if not specified in settings
DEFAULT_LOG_LEVEL = "INFO"

class ColorFormatter(logging.Formatter):
    """Custom color formatter for prettier logging"""
    
    COLORS = {
        'DEBUG': '\x1b[38;21m',     # Grey
        'INFO': '\x1b[34;21m',      # Blue 
        'WARNING': '\x1b[33;21m',   # Yellow
        'ERROR': '\x1b[31;21m',     # Red
        'CRITICAL': '\x1b[31;1m'    # Bold Red
    }
    RESET = '\x1b[0m'
    FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['INFO'])
        formatter = logging.Formatter(
            f'{color}{self.FORMAT}{self.RESET}',
            datefmt='%H:%M:%S'
        )
        return formatter.format(record)

def log_command(logger):
    """Decorator untuk logging command execution & error tracking"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get command & function info
            command = func.__name__.replace('_command', '').replace('handle_', '')
            module = func.__module__
            
            # Log command start with module path
            logger.info(f"Command: !{command}")
            logger.info(f"↳ Handler: {module}.{func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                logger.info(f"↳ Status: Success ✓")
                return result
            except Exception as e:
                # Log detailed error info
                logger.error(
                    f"↳ Error in {module}.{func.__name__}:\n"
                    f"  Type: {type(e).__name__}\n"
                    f"  Message: {str(e)}\n"
                    f"  Args: {args}\n"
                    f"  Kwargs: {kwargs}"
                )
                raise
            
        return wrapper
    return decorator

def setup_logger(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Setup custom logger with colored output
    
    Args:
        name: Logger name (optional)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()
    
    # Setup stdout handler with color formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)

    return logger

def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure logging with custom filters.
    
    Args:
        log_level: Optional override for log level (default: from settings or INFO)
    """
    # If log_level not provided, try to get from environment or use default
    if not log_level:
        log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=numeric_level
    )
    
    # Add custom filter to hide successful HTTP request logs
    class HTTPFilter(logging.Filter):
        """Filter to remove successful HTTP request logs."""
        def filter(self, record):
            return not (
                'HTTP Request:' in record.getMessage() and 
                'HTTP/1.1 200' in record.getMessage()
            )
    
    # Add filter to root logger
    logging.getLogger().addFilter(HTTPFilter())
    
    # Reduce verbosity for HTTP-related logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Reduce verbosity for other libraries
    logging.getLogger("core.models").setLevel(logging.WARNING)
    logging.getLogger("utils.database").setLevel(logging.ERROR)
    logging.getLogger("utils.context_manager").setLevel(logging.ERROR)
    
    # Remove spammy logs from telegram and asyncio
    logging.getLogger("telegram").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log setup completion
    logging.info(f"Logging initialized with level: {log_level}")
