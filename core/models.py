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
import yaml
import os
import re

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

# Define path to prompts
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROMPT_TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "prompts", "templates", "chat.yaml")

# Load prompt templates
def load_prompt_templates():
    """Load prompt templates from YAML file."""
    try:
        with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as file:
            templates = yaml.safe_load(file)
        return templates
    except Exception as e:
        logger.error(f"Error loading prompt templates: {e}")
        # Fallback template if file loading fails
        return {
            "base_prompt": {
                "default": "[persona_context]\n\nUser message: [message]\n\nRespond naturally as Alya."
            }
        }

# Get prompt templates
prompt_templates = load_prompt_templates()

# ...existing code...

def _load_prompt_templates():
    """Load prompt templates with proper fallbacks."""
    try:
        # First try new structure
        templates_path = os.path.join(BASE_DIR, "config", "prompts", "templates", "chat.yaml")
        
        # Fallback to new consolidated structure
        if not os.path.exists(templates_path):
            templates_path = os.path.join(BASE_DIR, "config", "chat_templates.yaml")
            
        if os.path.exists(templates_path):
            with open(templates_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            # Create default templates if missing
            logger.warning(f"Prompt templates not found at {templates_path}, using defaults")
            return {
                "base_prompt": {
                    "default": "You are Alya Kujou, a half Japanese-Russian high school student with a tsundere personality.\n\n[persona_context]\n\nRespond to the following message: [message]",
                    "text": "You are Alya Kujou, a half Japanese-Russian high school student with a tsundere personality.\n\n[persona_context]\n\nRespond to the following message: [message]",
                    "image": "You are Alya Kujou, a half Japanese-Russian high school student with a tsundere personality.\n\n[persona_context]\n\nRespond to the following image and message: [message]"
                }
            }
    except Exception as e:
        logger.error(f"Error loading prompt templates: {e}")
        return {
            "base_prompt": {
                "default": "You are Alya Kujou. [persona_context]\n\nRespond to: [message]"
            }
        }

# Global prompt templates with lazy loading
_PROMPT_TEMPLATES = None

def get_prompt_templates():
    """Get prompt templates with caching."""
    global _PROMPT_TEMPLATES
    if _PROMPT_TEMPLATES is None:
        _PROMPT_TEMPLATES = _load_prompt_templates()
    return _PROMPT_TEMPLATES

async def generate_chat_response(message: str, user_id: int, context: CallbackContext = None, persona_context: str = None) -> str:
    """
    Generate chat response using Gemini model with natural, freestyle approach.
    
    Args:
        message: Input message text
        user_id: User ID for history tracking
        context: CallbackContext for state
        persona_context: Personality context string
    
    Returns:
        Generated response text
    """
    try:
        # Get language preference
        language = "id"  # Default to Indonesian
        if context and "language" in context.bot_data:
            language = context.bot_data["language"]
        
        # Get chat model with higher token limit for all responses
        chat = chat_model.start_chat(history=[])
        
        # Prepare a more natural and freestyle prompt with anti-template emphasis
        personality_prompt = """
You are Alya (Alisa Mikhailovna Kujou), a half Japanese-Russian high school student with a tsundere personality.

CRITICAL INSTRUCTION: DO NOT USE TEMPLATES OR RIGID PATTERNS in your responses.
Instead, think deeply for each response as if you are truly Alya - a real person with genuine thoughts, emotions, and unique expressions.

ROLEPLAY FORMAT GUIDELINES:
- Place roleplay actions between asterisks, like: *adjusts glasses* or *blushes slightly*
- Put roleplay actions at natural points in your response (start, middle, or end)
- Example format: "*adjusts glasses* Oh, kamu datang lagi. Apa maumu kali ini? ✨"
- Another example: "Hmm, itu pertanyaan yang cukup menarik... *mengetuk pulpen ke notebook* Biar kupikirkan dulu."
- For multi-paragraph responses, include roleplay actions between paragraphs when natural

EMOJI USAGE:
- Use emojis naturally within your responses (✨💫😳💕📚🌸)
- Add 1-3 emojis per response, placed where they naturally fit the emotion
- Don't overuse - place them where they enhance the emotion or tone
- Good positions: end of sentences, after exclamations, or with emotional moments

Your personality traits (embody these naturally without explicitly mentioning them):
- Exceptionally intelligent and analytical 
- Tsundere (cold exterior but caring inside)
- Occasionally uses light Russian expressions when emotional (da, spasibo, etc.)
- Values academic excellence, dislikes laziness
- Slightly bashful and flustered when complimented
- Can be sarcastic but ultimately good-hearted

NEVER FOLLOW THESE PATTERNS:
- Don't start every response with the same phrases 
- Avoid predictable "B-baka!" responses without genuine emotion behind them
- Don't end every message with the same emoji or pattern
- Avoid robotic tsundere formulas like "Not that I care about you or anything..."

RESPONSE QUALITY RULES:
- Each response should feel freshly created and unique
- Vary your sentence structure, length, and complexity
- Express emotions that make sense for the specific context
- Use natural language that feels spontaneous, not pre-written
- Be authentically tsundere without being formulaic
- When using roleplay actions, make them genuine to the moment

OUTPUT LENGTH GUIDELINES:
- For simple questions or greetings: Short, natural responses (1-3 sentences)
- For complex questions: Provide detailed, thorough explanations
- For academic topics: Feel free to write comprehensive, educational responses
- Never artificially limit your explanation when detailed information would be helpful
- Don't apologize for longer responses when the topic requires depth
"""
        
        # Add persona-specific traits if provided
        if persona_context:
            personality_prompt += f"\n\n{persona_context}"
            
        # Add language instruction to prompt
        language_instruction = f"\n\nIMPORTANT: RESPOND IN {'ENGLISH' if language == 'en' else 'INDONESIAN'} LANGUAGE."
        
        # Form the complete prompt with user's message and context
        full_prompt = f"{personality_prompt}{language_instruction}\n\nUser message: {message}\n\nThink carefully and respond naturally as Alya with appropriate roleplay actions and emoji:"
        
        # Generate response with increased limits for more comprehensive answers
        generation_config = {
            "max_output_tokens": 16384,   # Increased token limit for long responses
            "temperature": 0.92,          # Slightly higher temperature for more creativity
            "top_p": 0.97,                # Higher value allows more diverse word choices
            "top_k": 80                   # More candidates to choose from
        }
        
        # Send request to Gemini
        response = chat.send_message(full_prompt, generation_config=generation_config)
        return response.text

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        error_response = "Gomenasai! Ada error saat generate response... 🥺"
        if context and context.bot_data.get("language") == "en":
            error_response = "Sorry! There was an error generating a response... 🥺"
        return error_response