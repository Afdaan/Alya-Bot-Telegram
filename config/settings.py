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
GEMINI_MODEL: str = "gemini-2.0-flash-lite"
MAX_OUTPUT_TOKENS: int = 8192
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
        1: 50,   # Stranger → Acquaintance: 50 messages
        2: 100,   # Acquaintance → Friend: 100 messages
        3: 200,  # Friend → Close Friend: 200 messages
    },
    "affection_points": {  # Affection points to reach each level
        1: 100,   # Stranger → Acquaintance: 50 points
        2: 200,  # Acquaintance → Friend: 200 points
        3: 500,  # Friend → Close Friend: 500 points
    }
}

# NLP Settings
NLP_MODELS_DIR: str = os.getenv("NLP_MODELS_DIR", "data/models")
EMOTION_DETECTION_MODEL: str = os.getenv(
    "EMOTION_DETECTION_MODEL", 
    "AnasAlokla/multilingual_go_emotions_V1.1"  # HuggingFace hosted model
)
SENTIMENT_MODEL: str = os.getenv(
    "SENTIMENT_MODEL",
    "mdhugol/indonesia-bert-sentiment-classification"  # HuggingFace hosted #distilbert-base-uncased-finetuned-sst-2-english
)
SUPPORTED_EMOTIONS: List[str] = ["joy", "sadness", "anger", "fear", "surprise", "neutral"]
EMOTION_CONFIDENCE_THRESHOLD: float = 0.4  # Minimum confidence to assign an emotion

# Feature Flags
FEATURES: Dict[str, bool] = {
    "memory": True,
    "rag": True,
    "emotion_detection": True,
    "roleplay": True,
    "russian_expressions": True,
    "relationship_levels": True,
    "use_huggingface_models": os.getenv("USE_HUGGINGFACE_MODELS", "true").lower() == "false"  # Toggle between HF models and custom NLP
}

# Security
MAX_MESSAGE_LENGTH: int = 4096  # Telegram limit

# Logging Settings
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"