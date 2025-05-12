import os
from typing import Optional

def get_env_var(key: str) -> Optional[str]:
    """Get environment variable with error handling."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Missing environment variable: {key}")
    return value

# Bot configuration
TELEGRAM_TOKEN = get_env_var("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = get_env_var("GEMINI_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")  # Optional

# Chat prefix for group chats
CHAT_PREFIX = "!ai"
ANALYZE_PREFIX = "!trace"  # New prefix for document/image analysis

# Model Configuration
DEFAULT_MODEL = "gemini-2.0-flash"
IMAGE_MODEL = "gemini-2.0-flash"

# Generation Configuration
GENERATION_CONFIG = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
}

# Safety Settings Configuration
SAFETY_SETTINGS = {
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE"
}

# Chat Configuration
MAX_HISTORY = 10  # Maximum number of messages to keep in history
HISTORY_EXPIRE = 3600  # History expiration in seconds (1 hour)