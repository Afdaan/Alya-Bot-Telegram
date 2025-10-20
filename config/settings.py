"""
Configuration settings for Alya Bot.
"""
import os
from typing import Dict, List, Any, Optional, Set
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Settings
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
BOT_NAME: str = "Alya"
COMMAND_PREFIX: str = "!ai"
SAUCENAO_PREFIX: str = "!sauce"
DEFAULT_LANGUAGE: str = "id"  # Options: "id", "en"

# Database Settings
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_USERNAME: str = os.getenv("DB_USERNAME", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_NAME: str = os.getenv("DB_NAME", "alya_bot")

# Database Connection Pool Settings
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

# Database URL construction with proper URL encoding
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", 
    f"mysql+pymysql://{quote_plus(DB_USERNAME)}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# Admin Settings
# Load from environment variable, comma separated list of IDs
ADMIN_IDS: Set[int] = set()
admin_id_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(id_str.strip()) for id_str in admin_id_str.split(',') if id_str.strip()}


# Gemini API Settings
GEMINI_API_KEYS: List[str] = [
    key.strip() for key in os.getenv("GEMINI_API_KEYS", "").split(",") if key.strip()
]
GEMINI_MODEL: str = "gemini-2.0-flash"
MAX_OUTPUT_TOKENS: int = 8192
TEMPERATURE: float = 0.7
TOP_K: int = 40
TOP_P: float = 0.95

# SauceNAO API KEY
SAUCENAO_API_KEY: Optional[str] = os.getenv("SAUCENAO_API_KEY", True)

# Memory Settings
MAX_MEMORY_ITEMS: int = 80
SLIDING_WINDOW_SIZE: int = 85  # Number of messages before sliding the window
MEMORY_EXPIRY_DAYS: int = 7
RAG_CHUNK_SIZE: int = 3000
RAG_CHUNK_OVERLAP: int = 300
MAX_CONTEXT_MESSAGES: int = 80  # Max messages to include in context window
SUMMARY_INTERVAL: int = 3  # Days between conversation summarizations

# Persona Settings
PERSONA_DIR: str = "config/persona"
DEFAULT_PERSONA: str = "waifu"

# Relationship Levels - Configurable thresholds
RELATIONSHIP_LEVELS: Dict[int, str] = {
    0: "Stranger",
    1: "Acquaintance",
    2: "Friend",
    3: "Close Friend",
    4: "Soulmate"
}

# Relationship Role Names (for roleplay/handler mapping)
RELATIONSHIP_ROLE_NAMES: Dict[int, str] = {
    0: "Outsider",
    1: "Acquaintance",
    2: "Companion",
    3: "Confidant",
    4: "Heartbound"
}

# Relationship level progression thresholds
# NOTE: User gets whichever level is HIGHER between interaction-based and affection-based
# This allows both frequent chatters and emotionally positive users to progress
RELATIONSHIP_THRESHOLDS = {
    "interaction_count": {  # Messages exchanged to reach each level
        1: 50,       # Stranger → Acquaintance (easier to reach via chat frequency)
        2: 120,      # Acquaintance → Friend
        3: 250,      # Friend → Close Friend
        4: 500       # Close Friend → Soulmate (requires long-term engagement)
    },
    "affection_points": {  # Affection points to reach each level
        1: 80,       # Stranger → Acquaintance (easier to reach via positive behavior)
        2: 250,      # Acquaintance → Friend
        3: 500,      # Friend → Close Friend
        4: 1000      # Close Friend → Soulmate (requires deep emotional connection) 
    }
}

# Affection Points (all configurable for handler logic)
AFFECTION_POINTS: Dict[str, int] = {
    "greeting": 2,
    "gratitude": 5,
    "compliment": 10,
    "meaningful_conversation": 8,
    "asking_about_alya": 7,
    "remembering_details": 15,
    "affection": 5,
    "apology": 2,
    "question": 1,
    "friendliness": 6,
    "romantic_interest": 10,
    "conflict": -3,
    "insult": -10,
    "anger": -3,
    "toxic": -3,
    "toxic_behavior": -10,
    "rudeness": -10,
    "ignoring": -5,
    "inappropriate": -20,
    "bullying": -15,
    "positive_emotion": 2,
    "mild_positive_emotion": 1,
    "conversation": 1,  # Base affection for normal messages
    "min_penalty": -4
}

SUPPORTED_EMOTIONS: List[str] = ["joy", "sadness", "anger", "fear", "surprise", "neutral"]
EMOTION_CONFIDENCE_THRESHOLD: float = 0.4  # Minimum confidence to assign an emotion

# NLP Model Names (explicit for emotion classifier selection)
EMOTION_MODEL_ID: str = os.getenv(
    "EMOTION_MODEL_ID",
    "Aardiiiiy/EmoSense-ID-Indonesian-Emotion-Classifier"
)
EMOTION_MODEL_EN: str = os.getenv(
    "EMOTION_MODEL_EN",
    "AnasAlokla/multilingual_go_emotions"
)

# Feature Flags
FEATURES: Dict[str, bool] = {
    "memory": True,
    "rag": True,
    "emotion_detection": True,
    "roleplay": True,
    "russian_expressions": True,
    "relationship_levels": True,
    "use_huggingface_models": os.getenv("USE_HUGGINGFACE_MODELS", "true").lower() == "true"  # Toggle between HF models and custom NLP
}

# Response Formatting
FORMAT_ROLEPLAY: bool = True
FORMAT_EMOTION: bool = True
FORMAT_RUSSIAN: bool = True
MAX_EMOJI_PER_RESPONSE: int = 8

# Russian Expressions
RUSSIAN_EXPRESSIONS: Dict[str, Dict[str, List[str]]] = {
    "happy": {
        "expressions": ["счастливый", "рада", "хорошо"],
        "romaji": ["schastlivy", "rada", "khorosho"]
    },
    "angry": {
        "expressions": ["бака", "дурак", "что ты делаешь"],
        "romaji": ["baka", "durak", "chto ty delayesh"]
    },
    "sad": {
        "expressions": ["грустный", "печально", "извини"],
        "romaji": ["grustnyy", "pechal'no", "izvini"]
    },
    "surprised": {
        "expressions": ["что", "вау", "неужели"],
        "romaji": ["chto", "vau", "neuzheli"]
    }
}

# RAG Settings
RAG_MAX_RESULTS: int = 25

# Security
MAX_MESSAGE_LENGTH: int = 4096  # Telegram limit

# Logging Settings
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# PTB Settings - python-telegram-bot defaults
PTB_DEFAULTS = {
    'parse_mode': 'HTML',
}