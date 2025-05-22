"""
Settings Configuration for Alya Bot.

This module provides centralized configuration settings for the Alya Telegram Bot,
including API keys, model parameters, and operational settings.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

# =========================
# Configuration Helpers
# =========================

def get_env_var(key: str, default: str = "", required: bool = True) -> str:
    """
    Get environment variable with validation and fallback.
    
    Args:
        key: Name of the environment variable
        default: Default value if not found and not required
        required: Whether the variable is required
        
    Returns:
        Value of the environment variable or default
        
    Raises:
        ValueError: If required variable is missing
    """
    value = os.getenv(key, default)
    if not value and required:
        # Improved error message with setup instructions
        raise ValueError(
            f"Required environment variable missing: {key}\n"
            f"Please create a .env file or set the environment variable.\n"
            f"Example: export {key}=your_value_here"
        )
    return value

def load_env_file(env_path: str = ".env") -> None:
    """
    Load environment variables from .env file if exists.
    
    Args:
        env_path: Path to .env file
    """
    # Only attempt to load if dotenv is installed
    try:
        from dotenv import load_dotenv
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logging.info(f"Loaded environment variables from {env_path}")
        else:
            logging.warning(f".env file not found at {env_path}. Using system environment variables.")
    except ImportError:
        logging.warning("python-dotenv not installed. Using system environment variables.")

# Try to load environment variables from .env file
load_env_file()

# =========================
# Bot Configuration
# =========================

# Credentials from .env with proper fallbacks for development
TELEGRAM_BOT_TOKEN = get_env_var('TELEGRAM_BOT_TOKEN', required=True)
DEVELOPER_IDS_STR = get_env_var('DEVELOPER_IDS', default="", required=False)
DEVELOPER_IDS = [int(id.strip()) for id in DEVELOPER_IDS_STR.split(',') if id.strip()] if DEVELOPER_IDS_STR else []

# API Keys
GEMINI_API_KEY = get_env_var('GEMINI_API_KEY', required=True)
GOOGLE_SEARCH_API_KEY = get_env_var('GOOGLE_SEARCH_API_KEY', required=True)
GOOGLE_SEARCH_ENGINE_ID = get_env_var('GOOGLE_SEARCH_ENGINE_ID', required=True)
SAUCENAO_API_KEY = get_env_var('SAUCENAO_API_KEY', required=True)

# Model Configuration
DEFAULT_MODEL = "gemini-2.0-flash-exp"
IMAGE_MODEL = "gemini-2.0-flash-exp"

# =========================
# Command Configuration
# =========================

# Command prefixes
CHAT_PREFIX = "!ai"  # Main prefix for group chats
ANALYZE_PREFIX = "!trace"  # For document/image analysis
SAUCE_PREFIX = "!sauce"  # For reverse image search
ROAST_PREFIX = "!roast"  # For roasting mode
GITHUB_ROAST_PREFIXES = ["!gitroast", "/gitroast", "!github", "/github"]  # For GitHub roasting

# Group chat behavior
GROUP_CHAT_REQUIRES_PREFIX = True  # Requires prefix in group chats
ADDITIONAL_PREFIXES = ["!alya", "@alya"]  # Alternative prefixes
GROUP_DISABLE_IMAGES = False  # If True, will not process any images in groups

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

# Path to locale files
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

# API key rotation
GEMINI_BACKUP_API_KEYS_STR = get_env_var('GEMINI_BACKUP_API_KEYS', default="", required=False)
GEMINI_BACKUP_API_KEYS = [key.strip() for key in GEMINI_BACKUP_API_KEYS_STR.split(',') if key.strip()] if GEMINI_BACKUP_API_KEYS_STR else []

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

MAX_HISTORY = 25  # Maximum number of messages to keep in history
HISTORY_EXPIRE = 10800  # History expiration in seconds (3 hour)
GITHUB_CACHE_DURATION = 3600  # Cache GitHub data for 1 hour

# =========================
# Context Persistence Settings
# =========================

# Time-to-live for context persistence (in seconds)
CONTEXT_TTL = 604800  # 7 days in seconds

# TTL for personal facts (in seconds)
PERSONAL_FACTS_TTL = 7776000  # 90 days

# Base data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Context directory
CONTEXT_DIR = DATA_DIR / "context"
CONTEXT_DIR.mkdir(exist_ok=True)

# Path to SQLite database for context storage
CONTEXT_DB_PATH = str(Path(__file__).parent.parent / "data" / "context.db")

# Maximum number of messages to keep in context
CONTEXT_MAX_HISTORY = 25  # Increased from 10 to allow more context

# Time window (in seconds) to consider recent commands as relevant context
CONTEXT_RELEVANCE_WINDOW = 3600  # Reduced to 1 hour

# Maximum response length
MAX_RESPONSE_LENGTH = 8192  # Increased from 2048 to allow more detailed responses
MAX_EMOJI_PER_RESPONSE = 10  # Limit emoji usage

# =========================
# Database Purge & Maintenance
# =========================

# Settings for database purging (in days)
MAIN_DB_PURGE_DAYS = 30  # Purge main database records after 30 days
CONTEXT_DB_PURGE_DAYS = 60  # Purge context database records after 60 days
USER_HISTORY_PURGE_DAYS = 14  # Purge user chat history after 14 days
INACTIVE_USER_PURGE_DAYS = 90  # Purge inactive users after 90 days of inactivity

# Settings for database operations (in days)
DB_BACKUP_INTERVAL_DAYS = 7  # Create automatic backup every (in days)
DB_MAX_BACKUPS = 5  # Maximum number of backups to keep (in days)
DB_VACUUM_INTERVAL_DAYS = 8  # Run VACUUM on database (in days)
DB_WAL_CHECKPOINT_INTERVAL = 24  # Run WAL checkpoint (in hours)

# =========================
# Memory Settings
# =========================

# Maximum tokens for memory storage
MEMORY_MAX_TOKENS = 15000  # Batas token for memory management

# Threshold importance for remembering old messages
MEMORY_IMPORTANCE_THRESHOLD = 0.5

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
    "alamat", "rumah", "address", "home", "live in", "location", "stay",
    "senang", "happy", "glad", "excited", 
    "sedih", "sad", "upset", "down",
    "marah", "angry", "upset", "mad",
    "karakter", "character", "role", "peran",
    "cerita", "story", "plot", "setting", "universe",
    "hubungan", "relationship", "develop", "progress",
    "teman", "friend", "sahabat", "bestie",
    "cinta", "love", "suka", "crush", "perasaan", "feelings"
]

# Elephant memory settings
MEMORY_USE_ELEPHANT = True  # Enable "elephant memory" feature
MEMORY_REFERENCE_STYLE = "natural"  # Options: "natural", "exact", "minimal"
MEMORY_MAX_REFERENCES = 25  # Max past messages to reference in a response

MEMORY_RELATIONSHIP_BOOST = 1.5  # Booster untuk ingatan terkait hubungan

# =========================
# Response Style Configuration
# =========================

# Verbosity level affects how detailed Alya's responses will be
# 1: Minimal (just core response)
# 2: Normal (core response with some personality)
# 3: Detailed (more explanation and personality)
# 4: Verbose (full detailed explanations with strong personality)
RESPONSE_VERBOSITY = 3  # Normal verbosity with some personality

# Personality strength (0.0-1.0) - affects how much tsundere/personality is added
PERSONALITY_STRENGTH = 0.8  # Moderate personality strength

# Response extension ratios (how much each component contributes to response)
RESPONSE_CONFIG = {
    "context_ratio": 0.3,     # How much context from previous messages to include
    "detail_ratio": 0.3,      # How much additional detail to add to responses
    "personality_ratio": 0.4  # Personality contribution to responses
}

# === Personality and Roleplay Settings ===
PERSONALITY_STRENGTH = 0.8  # Response expressiveness level
RESPONSE_VERBOSITY = 3  # Response detail level

RESPONSE_CONFIG = {
    "context_ratio": 0.3,     # Context proportion in responses
    "detail_ratio": 0.3,      # Detail proportion in responses
    "personality_ratio": 0.4  # Personality proportion in responses
}

# === Response & Emoji Settings ===
MAX_RESPONSE_LENGTH = 8192
MAX_EMOJI_PER_RESPONSE = 25  # Increased from 10 to allow more emoji expressions
MIN_EMOJI_PER_RESPONSE = 4   # New setting to ensure minimum emoji usage

# Emoji categories for different moods
EMOJI_CATEGORIES = {
    "happy": ["✨", "💫", "💕", "🌸", "💝", "💖", "💗", "🤗", "☺️", "😊"],
    "tsundere": ["😤", "😳", "💢", "😒", "🙄", "😠", "😑", "😌", "😏", "🤨"],
    "embarrassed": ["😳", "🙈", "😖", "💓", "😵", "❤️", "🫣", "😅", "😶", "🥺"],
    "sad": ["😔", "🥺", "💔", "😢", "😭", "😿", "😓", "😥", "😞", "😟"],
    "angry": ["😠", "😤", "💢", "😑", "😒", "👊", "😡", "🔥", "💥", "⚡"]
}

# Note: Mood & Emotion settings are now in config/moods.yaml

# =========================
# Developer Settings
# =========================

# Developer command configuration
DEV_COMMANDS = {
    'update': {'enabled': True, 'description': 'Pull latest changes and restart bot'},
    'stats': {'enabled': True, 'description': 'Get detailed bot statistics'},
    'debug': {'enabled': True, 'description': 'Toggle debug mode'},
    'shell': {'enabled': True, 'description': 'Execute shell commands'},
    'lang': {'enabled': True, 'description': 'Change bot language'}
}

# Command prefixes
CHAT_PREFIX = "!ai"  # Main prefix for group chats
ANALYZE_PREFIX = "!trace"  # For document/image analysis
SAUCE_PREFIX = "!sauce"  # For reverse image search
ROAST_PREFIX = "!roast"  # For roasting mode
GITHUB_ROAST_PREFIXES = ["!gitroast", "/gitroast", "!github", "/github"]  # For GitHub roasting

# Group chat behavior
GROUP_CHAT_REQUIRES_PREFIX = True  # Requires prefix in group chats
ADDITIONAL_PREFIXES = ["!alya", "@alya"]  # Alternative prefixes

# =========================
# Logging Configuration
# =========================

LOGGING_CONFIG = {
    'SHOW_HTTP_SUCCESS': False,  # Don't show successful HTTP requests
    'LOG_LEVEL': 'INFO',
    'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# =========================
# Media Processing Settings
# =========================

# Create temp directory if it doesn't exist
TEMP_DIR = DATA_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Image settings
MAX_IMAGE_SIZE = 1024  # Maximum dimension for image processing
IMAGE_COMPRESS_QUALITY = 85  # JPEG quality (0-100)
IMAGE_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB max upload size
IMAGE_FORMATS = ['jpeg', 'jpg', 'png', 'webp']  # Supported image formats
DEFAULT_IMAGE_FORMAT = 'JPEG'  # Default format for compressed images
DEFAULT_THUMB_SIZE = 320  # Default thumbnail size
IMAGE_ANALYSIS_ENABLED = True  # Enable image analysis features

# Document settings
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB max document size
DOCUMENT_ANALYSIS_ENABLED = True  # Enable document analysis
DOCUMENT_EXTRACT_TEXT = True  # Extract text from documents
DOCUMENT_EXTRACT_IMAGES = True  # Extract images from documents

# OCR settings
OCR_LANGUAGE = "eng+ind"  # Default OCR languages (English + Indonesian)
MAX_OCR_PAGES = 6  # Maximum number of pages to OCR from PDFs

# Allowed document mime types
ALLOWED_DOCUMENT_TYPES = [
    'text/plain',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

# Roast settings
MAX_ROAST_LENGTH = 1000