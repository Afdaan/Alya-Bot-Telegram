"""
Configuration settings for Alya Bot.
"""
import os
from typing import Dict, List, Any, Optional, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Settings
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
BOT_NAME: str = "Alya"
COMMAND_PREFIX: str = "!ai"
SAUCENAO_PREFIX: str = "!sauce"
DEFAULT_LANGUAGE: str = "id"  # Options: "id", "en"

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
MAX_OUTPUT_TOKENS: int = 8098
TEMPERATURE: float = 0.7
TOP_K: int = 40
TOP_P: float = 0.95

# SauceNAO API KEY
SAUCENAO_API_KEY: Optional[str] = os.getenv("SAUCENAO_API_KEY", True)

# Database Settings
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/alya.db")
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/alya.db")

# Memory Settings
MAX_MEMORY_ITEMS: int = 30
SLIDING_WINDOW_SIZE: int = 25  # Number of messages before sliding the window
MEMORY_EXPIRY_DAYS: int = 7
RAG_CHUNK_SIZE: int = 3000
RAG_CHUNK_OVERLAP: int = 300

# Memory management settings
MEMORY_EXPIRY_DAYS: int = 7  # How long to keep raw conversation history
MAX_CONTEXT_MESSAGES: int = 10  # Max messages to include in context window
SUMMARY_INTERVAL: int = 3  # Days between conversation summarizations

# Logging Settings
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")  # Changed to WARNING
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Persona Settings
PERSONA_DIR: str = "config/persona"
DEFAULT_PERSONA: str = "waifu"

# Relationship Levels - Configurable thresholds
RELATIONSHIP_LEVELS: Dict[int, str] = {
    0: "Stranger",
    1: "Acquaintance", 
    2: "Friend",
    3: "Close Friend"
}

# Relationship level progression thresholds
RELATIONSHIP_THRESHOLDS = {
    "interaction_count": {  # Messages exchanged to reach each level
        1: 10,   # Stranger → Acquaintance: 10 messages
        2: 50,   # Acquaintance → Friend: 50 messages
        3: 150,  # Friend → Close Friend: 150 messages
    },
    "affection_points": {  # Affection points to reach each level
        1: 50,   # Stranger → Acquaintance: 50 points
        2: 200,  # Acquaintance → Friend: 200 points
        3: 500,  # Friend → Close Friend: 500 points
    }
}

# Points awarded for different interactions
AFFECTION_POINTS = {
    "greeting": 2,
    "gratitude": 5,
    "compliment": 10,
    "meaningful_conversation": 8,
    "asking_about_alya": 7,
    "remembering_details": 15,
    "rudeness": -10,
    "ignoring": -5,
    "inappropriate": -20
}

# RAG Settings
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # SentenceTransformers model for embeddings
VECTOR_DIMENSION: int = 384
RAG_RELEVANCE_THRESHOLD: float = 0.75
RAG_MAX_RESULTS: int = 5

# NLP Settings
# Path configurations for model files
NLP_MODELS_DIR: str = os.getenv("NLP_MODELS_DIR", "data/models")
EMOTION_DETECTION_MODEL: str = os.getenv(
    "EMOTION_DETECTION_MODEL", 
    "j-hartmann/emotion-english-distilroberta-base"  # HuggingFace hosted model
)
SENTIMENT_MODEL: str = os.getenv(
    "SENTIMENT_MODEL",
    "cardiffnlp/twitter-roberta-base-sentiment"  # HuggingFace hosted #distilbert-base-uncased-finetuned-sst-2-english
)
# If you want to use local models, set these env vars to paths like:
# NLP_MODELS_DIR/emotion-model or NLP_MODELS_DIR/sentiment-model

SUPPORTED_EMOTIONS: List[str] = ["joy", "sadness", "anger", "fear", "surprise", "neutral"]
EMOTION_CONFIDENCE_THRESHOLD: float = 0.4  # Minimum confidence to assign an emotion

# Response Formatting
FORMAT_ROLEPLAY: bool = True
FORMAT_EMOTION: bool = True
FORMAT_RUSSIAN: bool = True
MAX_EMOJI_PER_RESPONSE: int = 15
RESPONSE_BREVITY: float = 0.7  # 0.0 = very verbose, 1.0 = extremely brief

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

# PTB Settings - Fixed for python-telegram-bot v20.7
PTB_DEFAULTS = {
    'parse_mode': 'HTML',
}

# Feature Flags
FEATURES: Dict[str, bool] = {
    "memory": True,
    "rag": True,
    "emotion_detection": True,
    "roleplay": True,
    "russian_expressions": True,
    "relationship_levels": True
}

# Security
MAX_MESSAGE_LENGTH: int = 4096  # Telegram limit
