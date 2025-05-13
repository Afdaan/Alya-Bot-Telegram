import logging
import google.generativeai as genai
import time
import re
import random
import asyncio
import concurrent.futures
from datetime import datetime
from telegram.ext import CallbackContext
from core.search_engine import SearchEnginefrom concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor
 import (
from config.settings import ( 
    GEMINI_API_KEY, 
    DEFAULT_MODEL, 
    SAFETY_SETTINGS, ONFIG,
    GENERATION_CONFIG,
    HISTORY_EXPIRE   MAX_HISTORY,
    HISTORY_EXPIRE)
)
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

# Configure Gemini APIgenai.configure(api_key=GEMINI_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
 store chat history for each user
# Dictionary to store chat history for each useruser_chats = {}
user_chats = {}

class ChatHistory:
    def __init__(self):
        self.messages = []        self.last_update = time.time()
        self.last_update = time.time()
content: str):
    def add_message(self, role: str, content: str):
        """Add message to history.""""parts": [{"text": content}]})
        self.messages.append({"role": role, "parts": [{"text": content}]})MAX_HISTORY:
        if len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)        self.last_update = time.time()
        self.last_update = time.time()

    def is_expired(self) -> bool:
        """Check if history has expired."""        return (time.time() - self.last_update) > HISTORY_EXPIRE
        return (time.time() - self.last_update) > HISTORY_EXPIRE

    def get_context(self) -> list:tory for Gemini."""
        """Get formatted history for Gemini."""        return self.messages
        return self.messages

    def get_history_text(self) -> str:history as text."""
        """Get formatted history as text."""
        history_text = ""es:
        for msg in self.messages:
            role = msg["role"]
            content = msg["parts"][0]["text"] f"{role}: {content}\n"
            history_text += f"{role}: {content}\n"        return history_text
        return history_text
History:
def get_user_history(user_id: int) -> ChatHistory:story."""
    """Get or create user chat history."""
    if user_id not in user_chats:)
        user_chats[user_id] = ChatHistory()
    elif user_chats[user_id].is_expired():ChatHistory()
        user_chats[user_id] = ChatHistory()    return user_chats[user_id]
    return user_chats[user_id]

def setup_gemini_model(model_name=DEFAULT_MODEL):etup Gemini model with complete configuration."""
    """Setup Gemini model with complete configuration."""
    try:del(
        model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings=SAFETY_SETTINGS,   generation_config=GENERATION_CONFIG
            generation_config=GENERATION_CONFIG
        )
        return model
    except Exception as e:r.error(f"Error setting up Gemini model: {e}")
        logger.error(f"Error setting up Gemini model: {e}")        raise
        raise

# Initialize models with configuration
chat_model = setup_gemini_model(DEFAULT_MODEL)image_model = setup_gemini_model(DEFAULT_MODEL)
image_model = setup_gemini_model(DEFAULT_MODEL)
atterns
# Add developer info patterns
DEVELOPER_PATTERNS = [elop|developer)',
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer)', bot ini',
    r'(develop|developer|pembuat|creator) bot ini',)',
    r'bot ini (di)?(buat|bikin|develop)',
    r'siapa (sih )?yang (bikin|buat)',   r'di(buat|bikin|develop) (oleh )?siapa'
    r'di(buat|bikin|develop) (oleh )?siapa']
]

def is_developer_question(text: str) -> bool: is asking about the developer."""
    """Check if message is asking about the developer."""
    text = text.lower()    return any(re.search(pattern, text) for pattern in DEVELOPER_PATTERNS)
    return any(re.search(pattern, text) for pattern in DEVELOPER_PATTERNS)

def get_developer_response(username: str) -> str:ted developer information response."""
    """Get formatted developer information response."""
    responses = [\\.com` 💕",
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` ya~ 🌸",n\\-yastudio\\.com` 💕",
        f"Ara ara~ {username}\\-kun tertarik sama penciptaku ya? Aku karya *Afdaan* lho\\! Bisa dikunjungi di `alif\\.horn\\-yastudio\\.com` ✨"   f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` ya~ 🌸",
    ] tertarik sama penciptaku ya? Aku karya *Afdaan* lho\\! Bisa dikunjungi di `alif\\.horn\\-yastudio\\.com` ✨"
    return random.choice(responses)    ]

async def generate_chat_response(prompt: str, user_id: int, context: CallbackContext = None, persona_context: str = None) -> str:
    """Generate enhanced response with search capability."""f generate_chat_response(prompt: str, user_id: int, context: CallbackContext = None, persona_context: str = None) -> str:
    try: search capability."""
        chat = chat_model.start_chat()
        search_engine = SearchEngine()chat = chat_model.start_chat()
        
        # Enhanced keyword detection for search queries
        search_keywords = [
            'siapa', 'apa', 'dimana', 'kapan', 'bagaimana', 'mengapa', 'gimana', 'kenapa',
            'jadwal', 'info', 'cara', 'lokasi', 'rute', 'harga', 'biaya', 'jam', 'waktu', 'kenapa',
            'berapa', 'cari', 'tolong carikan', 'carikan', 'bantu', 'tolong cari'   'jadwal', 'info', 'cara', 'lokasi', 'rute', 'harga', 'biaya', 'jam', 'waktu', 
        ]    'berapa', 'cari', 'tolong carikan', 'carikan', 'bantu', 'tolong cari'
        
        # Enhanced topic detection for search queries
        search_topics = [
            'jadwal', 'kereta', 'krl', 'stasiun', 'pesawat', 'bus', 'film', 'bioskop',
            'restoran', 'makanan', 'hotel', 'berita', 'cuaca', 'konser', 'event'   'jadwal', 'kereta', 'krl', 'stasiun', 'pesawat', 'bus', 'film', 'bioskop',
        ]    'restoran', 'makanan', 'hotel', 'berita', 'cuaca', 'konser', 'event'
        
        # Check if the prompt likely needs factual information
        words = prompt.lower().split()
        needs_search = any(keyword in prompt.lower() for keyword in search_keywords) or \
                     any(topic in prompt.lower() for topic in search_topics)needs_search = any(keyword in prompt.lower() for keyword in search_keywords) or \
        (topic in prompt.lower() for topic in search_topics)
        if needs_search:
            # Get search results with a timeout_search:
            try:
                search_results = await asyncio.wait_for(
                    search_engine.search(prompt), await asyncio.wait_for(
                    timeout=10.0   search_engine.search(prompt),
                )
            except asyncio.TimeoutError:
                logger.warning(f"Search timed out for: {prompt}")
                search_results = "Tidak dapat melakukan pencarian karena timeout."earch timed out for: {prompt}")
            except Exception as e:kukan pencarian karena timeout."
                logger.error(f"Search error: {e}")
                search_results = "Error saat melakukan pencarian."logger.error(f"Search error: {e}")
                an."
            # Enhanced prompt for better information synthesis
            smart_prompt = f"""etter information synthesis
            {persona_context or ""}smart_prompt = f"""
            
            User's Question: {prompt}
            : {prompt}
            Search Results:
            {search_results}Search Results:
            
            Instructions for your response:
            1. Start with a friendly greeting in your waifu persona style
            2. Always call the user as "[username]-kun" or "[username]-chan" (no space)
            3. Provide clear, accurate information from the search resultsame]-chan" (no space)
            4. Structure the information in an easy-to-read format
            5. Include relevant details like times, locations, and dates if available
            6. If the information is incomplete, suggest where the user can get more detailsions, and dates if available
            7. End with a supportive, encouraging messagee the user can get more details
            8. Use appropriate emoji to enhance your response
            9. Make sure to maintain your character's personality8. Use appropriate emoji to enhance your response
            
            Respond in a helpful, informative way while staying in character.
            """Respond in a helpful, informative way while staying in character.
            
            # Use ThreadPoolExecutor to run the synchronous send_message in a separate thread
            try:
                with ThreadPoolExecutor() as executor:
                    send_message_task = executor.submit(chat.send_message, smart_prompt)   chat.send_message(smart_prompt),
                    # Use asyncio.wait_for to add a timeout to the thread execution timeout for generation
                    response = await asyncio.wait_for(
                        asyncio.wrap_future(send_message_task),
                        timeout=30.0
                    )   logger.warning(f"Response generation timed out for: {prompt}")
                response_text = response.textsai~ Alya butuh waktu lebih lama untuk memproses pertanyaan ini. Bisa ditanyakan dengan cara yang lebih sederhana? 🥺"
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                logger.warning(f"Response generation timed out for: {prompt}")
                return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pertanyaan ini. Bisa ditanyakan dengan cara yang lebih sederhana? 🥺"chat_prompt = f"""
            except Exception as e:}
                logger.error(f"Error generating response: {str(e)}")
                return "Gomennasai~ Ada kesalahan saat memproses permintaan. Bisa dicoba lagi? 🥺"
        else:
            # Regular chat modease respond naturally and in character as Alya-chan.
            chat_prompt = f"""Always call the user as "[username]-kun" or "[username]-chan" (no space between name and honorific).
            {persona_context or ""}
            
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