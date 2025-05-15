"""
LLM Handler for Alya Telegram Bot.

This module manages interactions with the Gemini AI model
and integrates with personas defined in `personas.py`.
"""

import logging
import asyncio
import time
from typing import Optional, Dict, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

__all__ = [
    'ChatHistory',
    'add_message_to_history',
    'get_user_history',
    'clear_user_history',
    'check_rate_limit',
    'can_user_chat',
    'is_message_valid'
]

# Move ChatHistory class definition to top
class ChatHistory:
    """Class to manage user chat history with expiration."""
    def __init__(self):
        self.messages: List[Dict] = []
        self.last_update = time.time()

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the user's history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        if len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)
        self.last_update = time.time()

    def is_expired(self) -> bool:
        """Check if the chat history has expired."""
        return (time.time() - self.last_update) > HISTORY_EXPIRE

    def get_history_text(self) -> str:
        """Return chat history as a formatted text."""
        return "\n".join(f"{msg['role']}: {msg['content']}" for msg in self.messages)

# Setup logger
logger = logging.getLogger(__name__)

# Import required modules
try:
    import google.generativeai as genai
except ImportError:
    logger.error("google-generativeai not installed. Run: pip install google-generativeai")
    raise

from telegram.ext import CallbackContext
from utils.language_handler import get_prompt_language_instruction, get_language
from utils.cache_manager import response_cache
from core.personas import get_persona_context
from config.settings import (
    GEMINI_API_KEY,
    DEFAULT_MODEL,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
    MAX_HISTORY,
    HISTORY_EXPIRE
)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize model
try:
    chat_model = genai.GenerativeModel(
        model_name=DEFAULT_MODEL,
        safety_settings=SAFETY_SETTINGS,
        generation_config=GENERATION_CONFIG
    )
except Exception as e:
    logger.error(f"Error initializing Gemini model: {e}")
    raise

# Global variables
user_chats: Dict[int, ChatHistory] = {}
rate_limits = {}
request_timestamps = []
MAX_REQUESTS_PER_MINUTE = 20

def add_message_to_history(user_id: int, content: str, role: str) -> None:
    """Add message to user chat history."""
    if user_id is None or content is None or role is None:
        raise ValueError("Invalid parameters")
        
    if role not in ["user", "assistant", "system"]:
        raise ValueError("Invalid role")
        
    if user_id not in user_chats:
        user_chats[user_id] = ChatHistory()
        
    user_chats[user_id].add_message(role, content)

def get_user_history(user_id: int) -> List[Dict]:
    """Get user chat history messages."""
    if user_id not in user_chats:
        user_chats[user_id] = ChatHistory()
    return user_chats[user_id].messages

def clear_user_history(user_id: int) -> None:
    """Clear user chat history."""
    if user_id in user_chats:
        user_chats[user_id].messages = []

def check_rate_limit(user_id: int) -> bool:
    """Check if user is rate limited."""
    now = datetime.now()
    if user_id in rate_limits:
        last_request = rate_limits[user_id]
        if (now - last_request).seconds < 1:  # 1 second cooldown
            return False
    rate_limits[user_id] = now
    return True

def can_user_chat(user_id: int) -> bool:
    """Check if user can chat."""
    # Implement ban logic here if needed
    return True

def is_message_valid(content: str) -> bool:
    """Validate message content."""
    if not content or content.isspace():
        return False
    if len(content) > 4000:  # Max length
        return False
    return True

# =========================
# Rate Limiting
# =========================

async def wait_for_rate_limit():
    """Enforce rate limiting for API requests."""
    global request_timestamps
    now = time.time()
    request_timestamps = [t for t in request_timestamps if now - t < 60]
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - request_timestamps[0])
        logger.warning(f"Rate limit reached. Pausing for {wait_time:.2f} seconds.")
        await asyncio.sleep(wait_time)
    request_timestamps.append(now)

# =========================
# Response Generation
# =========================

async def generate_chat_response(
    prompt: str,
    user_id: int,
    context: Optional[CallbackContext] = None,
    persona_context: Optional[str] = None
) -> str:
    """Generate AI response with personality."""
    try:
        # Check cache for existing response
        cached_response = response_cache.get(prompt)
        if cached_response:
            return cached_response

        # Enforce rate limit
        await wait_for_rate_limit()

        # Get user chat history
        if user_id not in user_chats:
            user_chats[user_id] = ChatHistory()
        chat_history = user_chats[user_id]
        history_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history.messages)

        # Get language settings
        language = get_language(context) if context else "id"
        language_instruction = get_prompt_language_instruction(language, context)

        # Get personality based on message type 
        if "roast" in prompt.lower():
            if not persona_context:
                persona_context = get_persona_context("toxic")
        else:
            if not persona_context:
                persona_context = get_persona_context("waifu")

        # Build the full prompt with more expressive personality
        full_prompt = f"""
        {persona_context}

        Context:
        {history_text}

        User Message: {prompt}

        Instructions:
        1. Respond with FULL personality - be extremely expressive!
        2. Use lots of kawaii expressions, emojis and excitement
        3. For toxic mode: BE EXTREMELY TOXIC with all caps and brutal roasts
        4. Always stay in character no matter what
        5. Don't hold back the personality at all!
        """

        # Generate response with full personality
        with ThreadPoolExecutor() as executor:
            response = await asyncio.wait_for(
                asyncio.wrap_future(executor.submit(chat_model.start_chat().send_message, full_prompt)),
                timeout=30
            )
            response_text = response.text

        # Save response to cache and history
        response_cache.set(prompt, response_text)
        chat_history.add_message("user", prompt)
        chat_history.add_message("assistant", response_text)

        return response_text

    except asyncio.TimeoutError:
        logger.warning(f"Response timeout for prompt: {prompt}")
        return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pesan ini 🥺💕."

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "Alya mengalami error! Maaf ya 🥺💕."