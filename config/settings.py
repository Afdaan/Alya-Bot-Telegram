"""Settings Configuration for Alya Bot."""

import os
from typing import Optional, Dict, Any, List

def get_env_var(key: str, required: bool = True) -> str:
    """Get environment variable with validation."""
    value = os.getenv(key)
    if value is None and required:
        raise ValueError(f"Required environment variable missing: {key}")
    return value

# =========================
# Bot Configuration
# =========================

# Credentials from .env
TELEGRAM_BOT_TOKEN = get_env_var('TELEGRAM_BOT_TOKEN', required=True)
DEVELOPER_IDS = [int(id) for id in get_env_var('DEVELOPER_IDS').split(',')]
GEMINI_API_KEY = get_env_var('GEMINI_API_KEY', required=True)
GOOGLE_SEARCH_API_KEY = get_env_var('GOOGLE_SEARCH_API_KEY', required=True)
GOOGLE_SEARCH_ENGINE_ID = get_env_var('GOOGLE_SEARCH_ENGINE_ID', required=True)
SAUCENAO_API_KEY = get_env_var('SAUCENAO_API_KEY', required=True)

# Model & Config Settings (hardcoded in codebase)
DEFAULT_MODEL = "gemini-2.0-flash-exp"
IMAGE_MODEL = "gemini-2.0-flash-exp"

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
    "temperature": 0.9,  # Increased for more personality
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
}

# Safety settings - adjusted for roleplay
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
DEVELOPER_IDS = [int(id) for id in get_env_var('DEVELOPER_IDS').split(',')]

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