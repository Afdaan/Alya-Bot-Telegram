"""
Settings Configuration for Alya Telegram Bot.

This module loads and provides access to environment variables and
configurable settings used throughout the application.
"""

import os
from typing import Optional, Dict, Any, List

# =========================
# Environment Utilities
# =========================

def get_env_var(key: str) -> Optional[str]:
    """
    Get environment variable with error handling.
    
    Args:
        key: Environment variable name
    
    Returns:
        Environment variable value or None if not found
    
    Raises:
        ValueError: If the environment variable is missing
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Missing environment variable: {key}")
    return value

def get_env_list(key: str, separator: str = ',', default: List = []) -> List:
    """
    Get environment variable as a list.
    
    Args:
        key: Environment variable name
        separator: Character used to split the value
        default: Default value if environment variable is not set
        
    Returns:
        List of strings from the environment variable
    """
    value = os.getenv(key)
    if not value:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]

def get_env_int_list(key: str, separator: str = ',', default: List[int] = []) -> List[int]:
    """
    Get environment variable as a list of integers.
    
    Args:
        key: Environment variable name
        separator: Character used to split the value
        default: Default value if environment variable is not set
        
    Returns:
        List of integers from the environment variable
    """
    try:
        return [int(item) for item in get_env_list(key, separator)]
    except (ValueError, TypeError):
        return default

# =========================
# Bot Configuration
# =========================

TELEGRAM_TOKEN = get_env_var("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = get_env_var("GEMINI_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")  # Optional

# Command prefixes
CHAT_PREFIX = "!ai"  # Main prefix for group chats
ANALYZE_PREFIX = "!trace"  # For document/image analysis
SAUCE_PREFIX = "!sauce"  # For reverse image search
ROAST_PREFIX = "!roast"  # For roasting mode

# =========================
# Language Settings
# =========================

DEFAULT_LANGUAGE = "id"  # Options: "id" (Indonesian), "en" (English)
SUPPORTED_LANGUAGES = {
    "id": "Indonesian",
    "en": "English"
}

# =========================
# Model Settings
# =========================

DEFAULT_MODEL = "gemini-2.0-flash-exp"
IMAGE_MODEL = "gemini-2.0-flash-exp"

# Generation settings
GENERATION_CONFIG = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
}

# Safety settings - relaxed for roleplay
SAFETY_SETTINGS = {
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE", 
    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE"
}

# =========================
# Chat Settings
# =========================

MAX_HISTORY = 10  # Maximum number of messages to keep in history
HISTORY_EXPIRE = 3600  # History expiration in seconds (1 hour)
GITHUB_CACHE_DURATION = 3600  # Cache GitHub data for 1 hour

# =========================
# Developer Settings
# =========================

# Developer IDs for restricted commands
DEVELOPER_IDS = get_env_int_list('DEVELOPER_IDS')

# Developer command configuration
DEV_COMMANDS = {
    'update': {'enabled': True, 'description': 'Pull latest changes and restart bot'},
    'stats': {'enabled': True, 'description': 'Get detailed bot statistics'},
    'debug': {'enabled': True, 'description': 'Toggle debug mode'},
    'shell': {'enabled': True, 'description': 'Execute shell commands'},
    'lang': {'enabled': True, 'description': 'Change bot language'}
}

# =========================
# Logging Configuration
# =========================

LOGGING_CONFIG = {
    'SHOW_HTTP_SUCCESS': False,  # Don't show successful HTTP requests
    'LOG_LEVEL': 'INFO',
    'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}