"""
Logging configuration for Alya Telegram Bot.

Provides clean, minimal logging focused on application events and errors.
"""
import logging
import os
import sys
from typing import Optional, Dict, Any, Callable, Type
from functools import wraps

# Custom log levels
VERBOSE = 15  # Between DEBUG and INFO
logging.addLevelName(VERBOSE, "VERBOSE")

class MinimalFormatter(logging.Formatter):
    """
    Minimal formatter that removes unnecessary information for cleaner logs.
    """
    # Mapping for module prefix shortenings
    MODULE_PREFIX_MAP = {
        'telegram.': 'tg.',
        'handlers.': 'handlers.',
        'utils.': 'utils.',
        'core.': 'core.',
    }
    
    def __init__(self):
        super().__init__('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                         datefmt='%H:%M:%S')
    
    def format(self, record):
        # Simplify logger names but keep enough context for readability
        for prefix, short_prefix in self.MODULE_PREFIX_MAP.items():
            if record.name.startswith(prefix):
                parts = record.name.split('.')
                if len(parts) > 1:
                    # Keep module name but shorten the prefix
                    module_name = parts[1] if len(parts) > 1 else ''
                    record.name = f"{short_prefix}{module_name}"
                break
        
        # Return formatted record
        return super().format(record)

class HTTPFilter(logging.Filter):
    """
    Filter out HTTP logs except errors.
    """
    # HTTP-related terms to filter
    HTTP_TERMS = ['HTTP Request:', 'https://', 'http://']
    
    def filter(self, record):
        # Get message (safely)
        message = getattr(record, 'getMessage', lambda: '')()
        
        # Allow if not HTTP-related
        if not any(term in message for term in self.HTTP_TERMS):
            return True
            
        # For HTTP logs, only allow ERROR+ level
        return record.levelno >= logging.ERROR

def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Override log level (debug, info, warning, error)
    """
    # Determine log level from environment or parameter
    level_name = log_level or os.environ.get("LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(level_name, logging.INFO)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setFormatter(MinimalFormatter())
    
    # Configure root logger
    _configure_root_logger(level, handler)
    
    # Configure library loggers - avoid noisy logs from certain modules
    _configure_library_loggers(level)
    
    # Disable prefix detection logs - avoid spammy logs for common operations
    logging.getLogger('core.bot').setLevel(logging.WARNING)  # Set to WARNING to suppress INFO logs
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level {level_name}")

def _configure_root_logger(level: int, handler: logging.Handler) -> None:
    """Configure root logger with custom handler and level."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
        
    # Add our custom handler
    root_logger.addHandler(handler)
    
    # Add HTTP filter
    root_logger.addFilter(HTTPFilter())

def _configure_library_loggers(app_level: int) -> None:
    """Configure specific loggers for various libraries and modules."""
    # 1. HTTP-related libraries - completely disabled except errors
    http_libraries = ['httpx', 'urllib3', 'aiohttp', 'requests']
    for name in http_libraries:
        logging.getLogger(name).setLevel(logging.ERROR)
    
    # 2. Telegram-related libraries - only show errors
    telegram_libraries = ['telegram', 'telegram.ext', 'telegram.bot']
    for name in telegram_libraries:
        logging.getLogger(name).setLevel(logging.ERROR)
    
    # 3. Background libraries - only show warnings
    background_libraries = ['asyncio', 'apscheduler', 'PIL']
    for name in background_libraries:
        logging.getLogger(name).setLevel(logging.WARNING)
    
    # 4. App components - use app level
    app_components = ['handlers', 'core', 'utils']
    for name in app_components:
        logging.getLogger(name).setLevel(app_level)

def log_command(logger: logging.Logger) -> Callable:
    """
    Decorator for logging command execution with minimal output.
    
    Args:
        logger: Logger instance to use
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract command metadata
            command_name = func.__name__.replace('_command', '').replace('handle_', '')
            user_id = _extract_user_id_from_args(args)
            
            # Log with or without user ID
            if user_id:
                logger.info(f"Cmd: !{command_name} (uid: {user_id})")
            else:
                logger.info(f"Cmd: !{command_name}")
            
            try:
                # Execute command
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                # Log error with minimal details
                logger.error(f"Err in !{command_name}: {type(e).__name__} - {str(e)}")
                # Re-raise to allow proper error handling
                raise
            
        return wrapper
    return decorator

def _extract_user_id_from_args(args) -> Optional[int]:
    """Extract user ID from handler function arguments if available."""
    if args and hasattr(args[0], 'effective_user') and args[0].effective_user:
        return args[0].effective_user.id
    return None
