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

from config.settings import (
    GEMINI_API_KEY, 
    DEFAULT_MODEL, 
    SAFETY_SETTINGS, 
    GENERATION_CONFIG,
    MAX_HISTORY,
    HISTORY_EXPIRE
)

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Dictionary to store chat history for each user
user_chats = {}

class ChatHistory:
    def __init__(self):
        self.messages = []
        self.last_update = time.time()

    def add_message(self, role: str, content: str):
        """Add message to history."""
        self.messages.append({"role": role, "parts": [{"text": content}]})
        if len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)
        self.last_update = time.time()

    def is_expired(self) -> bool:
        """Check if history has expired."""
        return (time.time() - self.last_update) > HISTORY_EXPIRE

    def get_context(self) -> list:
        """Get formatted history for Gemini."""
        return self.messages

    def get_history_text(self) -> str:
        """Get formatted history as text."""
        history_text = ""
        for msg in self.messages:
            role = msg["role"]
            content = msg["parts"][0]["text"]
            history_text += f"{role}: {content}\n"
        return history_text

def get_user_history(user_id: int) -> ChatHistory:
    """Get or create user chat history."""
    if user_id not in user_chats:
        user_chats[user_id] = ChatHistory()
    elif user_chats[user_id].is_expired():
        user_chats[user_id] = ChatHistory()
    return user_chats[user_id]

def setup_gemini_model(model_name=DEFAULT_MODEL):
    """Setup Gemini model with complete configuration."""
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

# Add developer info patterns
DEVELOPER_PATTERNS = [
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer)',
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer) bot ini',
    r'(develop|developer|pembuat|creator) bot ini',
    r'bot ini (di)?(buat|bikin|develop)',
    r'siapa (sih )?yang (bikin|buat)',
    r'di(buat|bikin|develop) (oleh )?siapa'
]

def is_developer_question(text: str) -> bool:
    """Check if message is asking about the developer."""
    text = text.lower()
    return any(re.search(pattern, text) for pattern in DEVELOPER_PATTERNS)

def get_developer_response(username: str) -> str:
    """Get formatted developer information response."""
    responses = [
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` 💕",
        f"Ara ara~ {username}\\-kun tertarik sama penciptaku ya? Aku karya *Afdaan* lho\\! Bisa dikunjungi di `alif\\.horn\\-yastudio\\.com` ✨",
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` ya~ 🌸",
    ]
    return random.choice(responses)

async def generate_chat_response(prompt: str, user_id: int, context: CallbackContext = None, persona_context: str = None) -> str:
    """Generate enhanced response with search capability."""
    try:
        chat = chat_model.start_chat()
        search_engine = SearchEngine()
        
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
        words = prompt.lower().split()
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
            
            # Enhanced prompt for better information synthesis
            smart_prompt = f"""
            {persona_context or ""}
            
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
                return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pertanyaan ini. Bisa ditanyakan dengan cara yang lebih sederhana? 🥺"
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                return "Gomennasai~ Ada kesalahan saat memproses permintaan. Bisa dicoba lagi? 🥺"
        else:
            # Regular chat mode
            chat_prompt = f"""
            User Message: {prompt}
            
            Please respond naturally and in character as Alya-chan.   chat.send_message(chat_prompt),
            Always call the user as "[username]-kun" or "[username]-chan" (no space between name and honorific). timeout for generation
            """
            
            # Use ThreadPoolExecutor to run the synchronous send_message in a separate thread
            try:                logger.warning(f"Chat response generation timed out for: {prompt}")
                with ThreadPoolExecutor() as executor:Gomennasai~ Alya butuh waktu lebih lama untuk memproses pesan ini. Bisa disampaikan dengan cara yang lebih sederhana? 🥺"
                    send_message_task = executor.submit(chat.send_message, chat_prompt)
                    # Use asyncio.wait_for to add a timeout to the thread execution
                    response = await asyncio.wait_for(
                        asyncio.wrap_future(send_message_task),        chat_history.add_message("user", prompt)
                        timeout=30.0sage("assistant", response_text)
                    )
                response_text = response.textxt
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                logger.warning(f"Chat response generation timed out for: {prompt}")















        return "Gomen ne sayang~ Ada error... 🥺"        logger.error(f"Error in generate_chat_response: {e}")    except Exception as e:        return response_text        chat_history.add_message("assistant", response_text)        chat_history.add_message("user", prompt)        chat_history = get_user_history(user_id)        # Add to history                return "Gomennasai~ Ada kesalahan saat memproses permintaan. Bisa dicoba lagi? 🥺"                logger.error(f"Error generating response: {str(e)}")            except Exception as e:                return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pesan ini. Bisa disampaikan dengan cara yang lebih sederhana? 🥺"        logger.error(f"Error in generate_chat_response: {e}")
        return "Gomen ne sayang~ Ada error... 🥺"