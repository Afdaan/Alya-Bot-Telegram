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

# Language-specific persona settings
LANGUAGE_PERSONA_MAP = {
    "id": {
        "greeting": "Halo {username}-kun! Apa yang bisa Alya bantu?",
        "farewell": "Sampai jumpa lagi, {username}-kun!",
        "error": "Maaf, terjadi kesalahan."
    },
    "en": {
        "greeting": "Hello {username}-kun! How can Alya assist you?",
        "farewell": "See you later, {username}-kun!",
        "error": "Sorry, an error occurred."
    }
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
    "max_output_tokens": 8192,  # Increased from 2048 to allow longer responses like lyrics
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
# Context Persistence Settings
# =========================

# Time-to-live untuk context persistence (dalam detik)
CONTEXT_TTL = 7776000  # 90 days (3 bulan)

# TTL untuk personal facts (dalam detik)
PERSONAL_FACTS_TTL = 31536000  # 1 tahun

# Path ke SQLite database untuk context storage
CONTEXT_DB_PATH = "data/context/alya_context.db"

# Maximum max messages to keep in context
CONTEXT_MAX_HISTORY = 5  # Reduced from 15 to 5 for better performance

# Time window (dalam detik) untuk consider recent commands sebagai context yang relevan
CONTEXT_RELEVANCE_WINDOW = 3600  # Reduced to 1 hour

# Maximum response length
MAX_RESPONSE_LENGTH = 8192  # Increased from 2048 to allow more detailed responses for lyrics and content
MAX_EMOJI_PER_RESPONSE = 10  # Limit emoji usage

# =========================
# New Memory Settings
# =========================

# Maximum token untuk disimpan dalam memory (untuk memory management)
MEMORY_MAX_TOKENS = 10000  # ~40K characters of memory per user

# Threshold importance untuk mengingat pesan lama
MEMORY_IMPORTANCE_THRESHOLD = 0.7

# Automatic importance boosting untuk topik tertentu
MEMORY_IMPORTANT_TOPICS = [
    "nama", "umur", "hobi", "suka", "benci", 
    "kerja", "pekerjaan", "kuliah", "sekolah",
    "keluarga", "pacar", "gebetan", "alamat", "rumah"
]

# Elephant memory settings
MEMORY_USE_ELEPHANT = True  # Enable "elephant memory" feature
MEMORY_REFERENCE_STYLE = "natural"  # Options: "natural", "exact", "minimal"
MEMORY_MAX_REFERENCES = 3  # Max past messages to reference in a response

# =========================
# Response Style Configuration
# =========================

# Verbosity level affects how detailed Alya's responses will be
# 1: Minimal (just core response)
# 2: Normal (core response with some personality)
# 3: Detailed (more explanation and personality)
# 4: Verbose (full detailed explanations with strong personality)
RESPONSE_VERBOSITY = 3  # Default to detailed responses

# Personality strength (0.0-1.0) - affects how much tsundere/personality is added
PERSONALITY_STRENGTH = 1.0

# Response extension ratios (how much each component contributes to response)
RESPONSE_CONFIG = {
    "context_ratio": 0.3,     # How much context from previous messages to include
    "detail_ratio": 0.4,      # How much additional detail to add to responses
    "personality_ratio": 0.3  # How much personality/character traits to add
}

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