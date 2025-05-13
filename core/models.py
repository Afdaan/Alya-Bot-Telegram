"""
LLM Models and Chat Management for Alya Telegram Bot.

This module handles interactions with the Gemini AI model, manages user chat histories,
and provides response generation functionality with enhanced search capabilities.
"""

import logging
import google.generativeai as genai
import time
import re
import random
import asyncio
import concurrent.futures
from datetime import datetime
from telegram.ext import CallbackContext
from core.search_engine import SearchEngine
from concurrent.futures import ThreadPoolExecutor
# Ganti import sesuai nama fungsi yang tersedia di module
from utils.language_handler import get_prompt_language_instruction, get_language

from config.settings import (
    GEMINI_API_KEY, 
    DEFAULT_MODEL, 
    SAFETY_SETTINGS, 
    GENERATION_CONFIG,
    MAX_HISTORY,
    HISTORY_EXPIRE
)

logger = logging.getLogger(__name__)

# =========================
# Gemini API Configuration
# =========================

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Dictionary to store chat history for each user
user_chats = {}

# =========================
# Chat History Management
# =========================

class ChatHistory:
    """Class to manage user chat history with expiration."""
    
    def __init__(self):
        """Initialize empty chat history with timestamp."""
        self.messages = []
        self.last_update = time.time()

    def add_message(self, role: str, content: str):
        """
        Add message to history with role-based formatting.
        
        Args:
            role: Either 'user' or 'assistant'
            content: Message text content
        """
        self.messages.append({"role": role, "parts": [{"text": content}]})
        if len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)  # Remove oldest message when limit reached
        self.last_update = time.time()

    def is_expired(self) -> bool:
        """Check if history has expired based on timeout setting."""
        return (time.time() - self.last_update) > HISTORY_EXPIRE

    def get_context(self) -> list:
        """Get formatted history for Gemini API."""
        return self.messages

    def get_history_text(self) -> str:
        """Get formatted history as human-readable text."""
        history_text = ""
        for msg in self.messages:
            role = msg["role"]
            content = msg["parts"][0]["text"]
            history_text += f"{role}: {content}\n"
        return history_text


def get_user_history(user_id: int) -> ChatHistory:
    """
    Get or create user chat history with expiration handling.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        ChatHistory object for the user (new or existing)
    """
    if user_id not in user_chats:
        user_chats[user_id] = ChatHistory()
    elif user_chats[user_id].is_expired():
        # Replace expired history with fresh one
        user_chats[user_id] = ChatHistory()
    return user_chats[user_id]

# =========================
# Model Setup & Management
# =========================

def setup_gemini_model(model_name=DEFAULT_MODEL):
    """
    Setup Gemini model with safety settings and generation config.
    
    Args:
        model_name: Name of the Gemini model variant to use
        
    Returns:
        Configured GenerativeModel instance
    """
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings=SAFETY_SETTINGS,
            generation_config=GENERATION_CONFIG
        )
        return model
    except Exception as e:
        logger.error(f"Error setting up Gemini model: {e}")
        raise

# Initialize models with configuration
chat_model = setup_gemini_model(DEFAULT_MODEL)
image_model = setup_gemini_model(DEFAULT_MODEL)

# =========================
# Developer Info Detection
# =========================

# Patterns to identify questions about the bot's developer
DEVELOPER_PATTERNS = [
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer)',
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer) bot ini',
    r'(develop|developer|pembuat|creator) bot ini',
    r'bot ini (di)?(buat|bikin|develop)',
    r'siapa (sih )?yang (bikin|buat)',
    r'di(buat|bikin|develop) (oleh )?siapa'
]

def is_developer_question(text: str) -> bool:
    """
    Check if message is asking about the developer.
    
    Args:
        text: User message text
        
    Returns:
        True if asking about developer, False otherwise
    """
    text = text.lower()
    return any(re.search(pattern, text) for pattern in DEVELOPER_PATTERNS)

def get_developer_response(username: str) -> str:
    """
    Get formatted developer information response with Markdown escaping.
    
    Args:
        username: User's display name for personalization
        
    Returns:
        Developer info with Markdown formatting for Telegram
    """
    responses = [
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` 💕",
        f"Ara ara~ {username}\\-kun tertarik sama penciptaku ya? Aku karya *Afdaan* lho\\! Bisa dikunjungi di `alif\\.horn\\-yastudio\\.com` ✨",
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` ya~ 🌸",
    ]
    return random.choice(responses)

# =========================
# Response Generation
# =========================

async def generate_chat_response(prompt: str, user_id: int, context: CallbackContext = None, persona_context: str = None) -> str:
    """
    Generate enhanced AI response with search capability.
    
    Args:
        prompt: User message text
        user_id: Telegram user ID
        context: CallbackContext for language settings
        persona_context: Personality context for the AI
        
    Returns:
        Generated AI response
    """
    try:
        chat = chat_model.start_chat()
        search_engine = SearchEngine()
        
        # Gunakan fungsi get_language yang tersedia di module
        language = get_language(context)
        
        # Generate language instruction (soft preference, not strict requirement)
        language_instruction = get_prompt_language_instruction(language, context)
        
        # Enhanced keyword detection for search queries
        search_keywords = [
            'siapa', 'apa', 'dimana', 'kapan', 'bagaimana', 'mengapa', 'gimana', 'kenapa',
            'jadwal', 'info', 'cara', 'lokasi', 'rute', 'harga', 'biaya', 'jam', 'waktu', 
            'berapa', 'cari', 'tolong carikan', 'carikan', 'bantu', 'tolong cari'
        ]
        
        # Enhanced topic detection for search queries
        search_topics = [
            'jadwal', 'kereta', 'krl', 'stasiun', 'pesawat', 'bus', 'film', 'bioskop',
            'restoran', 'makanan', 'hotel', 'berita', 'cuaca', 'konser', 'event'
        ]
        
        # Check if the prompt likely needs factual information
        needs_search = any(keyword in prompt.lower() for keyword in search_keywords) or \
                      any(topic in prompt.lower() for topic in search_topics)

        if needs_search:
            # Get search results with a timeout
            try:
                search_results = await asyncio.wait_for(
                    search_engine.search(prompt),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Search timed out for: {prompt}")
                search_results = "Tidak dapat melakukan pencarian karena timeout."
            except Exception as e:
                logger.error(f"Search error: {e}")
                search_results = "Error saat melakukan pencarian."
            
            # Enhanced prompt for better information synthesis with flexible language
            smart_prompt = f"""
            {persona_context or ""}
            
            LANGUAGE PREFERENCE: {language_instruction}
            
            User's Question: {prompt}
            
            Search Results:
            {search_results}
            
            Instructions for your response:
            1. Start with a friendly greeting in your waifu persona style
            2. Always call the user as "[username]-kun" or "[username]-chan" (no space)
            3. Provide clear, accurate information from the search results
            4. Structure the information in an easy-to-read format
            5. Include relevant details like times, locations, and dates if available
            6. If the information is incomplete, suggest where the user can get more details
            7. End with a supportive, encouraging message
            8. Use appropriate emoji to enhance your response
            9. Make sure to maintain your character's personality
            10. By default respond in {"English" if language == "en" else "Indonesian"}, but if user requests another language, feel free to use that
            
            Respond in a helpful, informative way while staying in character.
            """
            
            # Use ThreadPoolExecutor to run the synchronous send_message in a separate thread
            try:
                with ThreadPoolExecutor() as executor:
                    send_message_task = executor.submit(chat.send_message, smart_prompt)
                    # Use asyncio.wait_for to add a timeout to the thread execution
                    response = await asyncio.wait_for(
                        asyncio.wrap_future(send_message_task),
                        timeout=30.0
                    )
                response_text = response.text
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                logger.warning(f"Response generation timed out for: {prompt}")
                if language == "en":
                    return "Sorry~ Alya needs more time to process this question. Could you ask in a simpler way? 🥺"
                return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pertanyaan ini. Bisa ditanyakan dengan cara yang lebih sederhana? 🥺"
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                if language == "en":
                    return "Sorry~ There was an error processing your request. Could you try again? 🥺"
                return "Gomennasai~ Ada kesalahan saat memproses permintaan. Bisa dicoba lagi? 🥺"
        else:
            # Regular chat mode
            chat_prompt = f"""
            {persona_context or ""}
            
            LANGUAGE PREFERENCE: {language_instruction}
            
            User Message: {prompt}
            
            Please respond naturally and in character as Alya-chan.
            Always call the user as "[username]-kun" or "[username]-chan" (no space between name and honorific).
            By default respond in {"English" if language == "en" else "Indonesian"}, but if user requests another language, feel free to use that.
            """
            try:
                with ThreadPoolExecutor() as executor:
                    send_message_task = executor.submit(chat.send_message, chat_prompt)
                    response = await asyncio.wait_for(
                        asyncio.wrap_future(send_message_task),
                        timeout=30.0
                    )
                response_text = response.text
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                logger.warning(f"Chat response generation timed out for: {prompt}")
                if language == "en":
                    return "Sorry~ Alya needs more time to process this message. Could you express it in a simpler way? 🥺"
                return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pesan ini. Bisa disampaikan dengan cara yang lebih sederhana? 🥺"
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                if language == "en":
                    return "Sorry~ There was an error processing your request. Could you try again? 🥺"
                return "Gomennasai~ Ada kesalahan saat memproses permintaan. Bisa dicoba lagi? 🥺"

        # Add to history
        chat_history = get_user_history(user_id)
        chat_history.add_message("user", prompt)
        chat_history.add_message("assistant", response_text)

        return response_text

    except Exception as e:        logger.error(f"Error in generate_chat_response: {e}")        # Return error message in the appropriate language        if 'language' in locals():            if language == "en":                return "Sorry darling~ There was an error... 🥺"        return "Gomen ne sayang~ Ada error... 🥺"