"""
Logging Configuration for Alya Bot.

This module configures logging for Alya Bot, including custom formatters,
log levels, and handlers for different components.
"""
import logging
import logging.config
import os
import sys
import functools
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union

# Define log directory relative to project
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "alya-bot.log"

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

# Default log level - can be overridden via environment variable
DEFAULT_LOG_LEVEL = os.getenv("ALYA_LOG_LEVEL", "INFO")

# Suppress specific loggers that are too verbose
SUPPRESSED_LOGGERS = [
    "httpx",                       # HTTP client logs 
    "telegram",                    # Telegram library logs
    "PIL.Image",                   # Pillow image library logs
    "matplotlib",                  # Matplotlib logs
    "sentence_transformers",       # Sentence transformers model logs
    "transformers",                # Transformers library logs
    "transitions",                 # State machine transitions logs
    "urllib3.connectionpool"       # HTTP connection pool logs
]

# Configure console logging format
CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
CONSOLE_DATE_FORMAT = "%H:%M:%S"

class NoTransformersWarningsFilter(logging.Filter):
    """Filter to remove common transformer library warnings."""
    
    def filter(self, record):
        # Skip common transformers warnings about model weights
        if "Some weights of the model checkpoint" in record.getMessage():
            return False
        # Skip truncation warnings
        if "Asking to truncate to max_length" in record.getMessage():
            return False
        # Skip batch progress
        if "Batches:" in record.getMessage():
            return False
        return True

def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Optional log level override
    """
    log_level = level or DEFAULT_LOG_LEVEL
    
    # Basic configuration dictionary
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': CONSOLE_FORMAT,
                'datefmt': CONSOLE_DATE_FORMAT
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'filters': {
            'no_transformers_warnings': {
                '()': NoTransformersWarningsFilter
            }
        },
        'handlers': {
            'console': {
                'level': log_level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'filters': ['no_transformers_warnings']
            },
            'file': {
                'level': 'DEBUG',
                'formatter': 'detailed',
                'class': 'logging.FileHandler',
                'filename': str(LOG_FILE),
                'mode': 'a',
                'filters': ['no_transformers_warnings']
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': True
            },
            # Set specific loggers to higher level to reduce noise
            **{logger: {'level': 'WARNING'} for logger in SUPPRESSED_LOGGERS}
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Additional suppressions for specific messages after basic config
    suppress_specific_warnings()
    
    # Log system information
    root_logger = logging.getLogger()
    root_logger.debug(f"Logging initialized at level {log_level}")
    root_logger.debug(f"Log file: {LOG_FILE}")

def suppress_specific_warnings():
    """Suppress specific warning patterns from external libraries."""
    # Suppress transformers specific warnings
    logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
    logging.getLogger("transformers.tokenization_utils").setLevel(logging.ERROR)
    
    # Suppress sentence-transformers batch warnings
    logging.getLogger("sentence_transformers.SentenceTransformer").setLevel(logging.WARNING)
    
    # Hide the tqdm progress bars in logs
    logging.getLogger("transformers.trainer").setLevel(logging.WARNING)

def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name and level.
    
    Args:
        name: Logger name, typically __name__
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(getattr(logging, level))
    return logger

def log_command(logger: logging.Logger) -> Callable:
    """
    Decorator to log command execution with username and timing information.
    
    Args:
        logger: Logger instance to use for logging
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            # Get user information
            user = update.effective_user
            user_id = user.id if user else "Unknown"
            username = user.username or user.first_name if user else "Unknown"
            
            # Get command information
            command = update.message.text if update.message else "Unknown command"
            
            start_time = time.time()
            logger.info(f"Command '{command}' executed by {username} (ID: {user_id})")
            
            try:
                # Execute the command handler
                result = await func(update, context, *args, **kwargs)
                
                # Log execution time
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                logger.debug(f"Command '{command}' completed in {execution_time:.2f}ms")
                
                return result
            except Exception as e:
                # Log exceptions
                logger.error(f"Error executing command '{command}': {str(e)}", exc_info=True)
                # Re-raise to allow proper error handling
                raise
        
        return wrapper
    return decorator
