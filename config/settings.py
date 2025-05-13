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
SAUCE_PREFIX = "!sauce"    # For reverse image search

# Model Configuration
DEFAULT_MODEL = "gemini-2.0-flash-exp"
IMAGE_MODEL = "gemini-2.0-flash-exp"

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

# Roast Configuration
ROAST_PREFIX = "!roast"
GITHUB_CACHE_DURATION = 3600  # Cache GitHub data for 1 hour

# Logging Configuration
LOGGING_CONFIG = {
    'SHOW_HTTP_SUCCESS': False,  # Don't show successful HTTP requests
    'LOG_LEVEL': 'INFO',
    'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}