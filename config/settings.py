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

# This for group chats
GROUP_CHAT_REQUIRES_PREFIX = True  # Wajib pakai prefix (!ai) di grup
ADDITIONAL_PREFIXES = ["!alya", "@alya"]  # Prefix alternatif yang bisa dipake juga

# =========================
# Language Settings
# =========================

DEFAULT_LANGUAGE = "id"  # Options: "id" (Indonesian), "en" (English)
SUPPORTED_LANGUAGES = {
    "id": "Indonesian",
    "en": "English"
}

# Mapping ISO code to filename
LANGUAGE_FILE_MAPPING = {
    "id": "indonesian",
    "en": "english"
}

# Path to locale files (updated)
LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

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

# API key rotation
GEMINI_API_KEY = get_env_var('GEMINI_API_KEY', required=True)
GEMINI_BACKUP_API_KEYS = get_env_var('GEMINI_BACKUP_API_KEYS', required=False)
if GEMINI_BACKUP_API_KEYS:
    GEMINI_BACKUP_API_KEYS = [key.strip() for key in GEMINI_BACKUP_API_KEYS.split(',') if key.strip()]
else:
    GEMINI_BACKUP_API_KEYS = []

# Generation settings optimized for free plan model
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

# Time-to-live for context persistence (in seconds)
CONTEXT_TTL = 7776000  # 90 days (3 months)

# TTL for personal facts (in seconds)
PERSONAL_FACTS_TTL = 31536000  # 1 year

# Path to SQLite database for context storage
CONTEXT_DB_PATH = "data/context/alya_context.db"

# Maximum number of messages to keep in context
CONTEXT_MAX_HISTORY = 5  # Reduced from 15 to 5 for better performance

# Time window (in seconds) to consider recent commands as relevant context
CONTEXT_RELEVANCE_WINDOW = 3600  # Reduced to 1 hour

# Maximum response length
MAX_RESPONSE_LENGTH = 8192  # Increased from 2048 to allow more detailed responses for lyrics and content
MAX_EMOJI_PER_RESPONSE = 10  # Limit emoji usage

# =========================
# Database Purge & Maintenance
# =========================

# Settings for database purging (in days)
MAIN_DB_PURGE_DAYS = 30  # Purge main database records after 30 days
CONTEXT_DB_PURGE_DAYS = 60  # Purge context database records after 60 days
USER_HISTORY_PURGE_DAYS = 14  # Purge user chat history after 14 days
INACTIVE_USER_PURGE_DAYS = 90  # Purge inactive users after 90 days of inactivity

# Settings for database operations
DB_BACKUP_INTERVAL_DAYS = 7  # Create automatic backup every 7 days
DB_MAX_BACKUPS = 5  # Maximum number of backups to keep
DB_VACUUM_INTERVAL_DAYS = 14  # Run VACUUM on database every 14 days
DB_WAL_CHECKPOINT_INTERVAL = 24  # Run WAL checkpoint every 24 hours (in hours)

# =========================
# New Memory Settings
# =========================

# Maximum tokens for memory storage
MEMORY_MAX_TOKENS = 10000  # ~40K characters of memory per user

# Threshold importance for remembering old messages
MEMORY_IMPORTANCE_THRESHOLD = 0.7

# Automatic importance boosting for certain topics
MEMORY_IMPORTANT_TOPICS = [
    # Personal identification
    "nama", "name", "nickname", "username", "call me",
    # Age related 
    "umur", "age", "birthday", "lahir", "born",
    # Interests
    "hobi", "hobby", "interest", "passion", "like doing",
    # Preferences
    "suka", "like", "love", "favorite", "prefer",
    "benci", "hate", "dislike", "can't stand",
    # Occupation
    "kerja", "pekerjaan", "work", "job", "profession", "career",
    # Education
    "kuliah", "sekolah", "university", "college", "school", "study", "major",
    # Relationships
    "keluarga", "family", "siblings", "parents", "children",
    "pacar", "gebetan", "partner", "girlfriend", "boyfriend", "crush", "relationship",
    # Location
    "alamat", "rumah", "address", "home", "live in", "location", "stay"
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
RESPONSE_VERBOSITY = 2  # UPDATED: Downgraded from 3 to 2 for more subtle responses

# Personality strength (0.0-1.0) - affects how much tsundere/personality is added
PERSONALITY_STRENGTH = 0.7  # UPDATED: Reduced from 1.0 to 0.7 for more subtle personality

# Response extension ratios (how much each component contributes to response)
RESPONSE_CONFIG = {
    "context_ratio": 0.4,     # How much context from previous messages to include
    "detail_ratio": 0.4,      # How much additional detail to add to responses
    "personality_ratio": 0.2  # UPDATED: Down from 0.3 to 0.2 for less personality in responses
}

# Max emoji per responses for limiting
MAX_EMOJI_PER_RESPONSE = 10  

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

# Media processing settings
MAX_IMAGE_SIZE = 1024  # Maximum dimension for image processing
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB max document size
OCR_LANGUAGE = "eng+ind"  # Default OCR languages
ALLOWED_DOCUMENT_TYPES = [
    'text/plain', 'application/pdf', 'application/msword', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]
MAX_OCR_PAGES = 5  # Maximum number of pages to OCR from PDFs

# Image compression settings
IMAGE_COMPRESS_QUALITY = 85  # JPEG quality (0-100)
IMAGE_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB max upload size
IMAGE_FORMATS = ['jpeg', 'jpg', 'png', 'webp']  # Supported image formats
DEFAULT_IMAGE_FORMAT = 'JPEG'  # Default format for compressed images
DEFAULT_THUMB_SIZE = 320  # Default thumbnail size
IMAGE_ANALYSIS_ENABLED = True  # Enable image analysis features

# Document processing settings
DOCUMENT_ANALYSIS_ENABLED = True  # Enable document analysis
DOCUMENT_EXTRACT_TEXT = True  # Extract text from documents
DOCUMENT_EXTRACT_IMAGES = True  # Extract images from documents
TEMP_DIR = "data/temp"  # Directory for temporary files