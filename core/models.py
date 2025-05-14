"""
LLM Models and Chat Management for Alya Telegram Bot.

Module ini menangani interaksi dengan model Gemini AI, mengelola history chat pengguna,
dan menyediakan fungsi generate respons dengan kemampuan pencarian yang ditingkatkan.
"""

import logging
import time
import re
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    logging.error("google-generativeai tidak terinstal. Jalankan: pip install google-generativeai")
    raise

from telegram.ext import CallbackContext
from core.search_engine import SearchEngine
from utils.language_handler import get_prompt_language_instruction, get_language

from config.settings import (
    GEMINI_API_KEY, 
    DEFAULT_MODEL, 
    SAFETY_SETTINGS, 
    GENERATION_CONFIG,
    MAX_HISTORY,
    HISTORY_EXPIRE
)

# Setup logger
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Dictionary untuk menyimpan history chat setiap user
user_chats = {}

# Pattern untuk mendeteksi pertanyaan tentang developer
DEVELOPER_PATTERNS = [
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer)',
    r'siapa (yang )?(develop|buat|bikin|membuat|develop|developer) bot ini',
    r'(develop|developer|pembuat|creator) bot ini',
    r'bot ini (di)?(buat|bikin|develop)',
    r'siapa (sih )?yang (bikin|buat)',
    r'di(buat|bikin|develop) (oleh )?siapa'
]

# Pattern untuk keyword pencarian
SEARCH_KEYWORDS = [
    'siapa', 'apa', 'dimana', 'kapan', 'bagaimana', 'mengapa', 'gimana', 'kenapa',
    'jadwal', 'info', 'cara', 'lokasi', 'rute', 'harga', 'biaya', 'jam', 'waktu', 
    'berapa', 'cari', 'tolong carikan', 'carikan', 'bantu', 'tolong cari'
]

# Topic untuk pencarian
SEARCH_TOPICS = [
    'jadwal', 'kereta', 'krl', 'stasiun', 'pesawat', 'bus', 'film', 'bioskop',
    'restoran', 'makanan', 'hotel', 'berita', 'cuaca', 'konser', 'event'
]


class ChatHistory:
    """Class untuk mengelola history chat user dengan fitur expiration."""
    
    def __init__(self):
        """Inisialisasi history chat kosong dengan timestamp."""
        self.messages = []
        self.last_update = time.time()

    def add_message(self, role: str, content: str) -> None:
        """
        Tambahkan pesan ke history dengan format berdasarkan role.
        
        Args:
            role: 'user' atau 'assistant'
            content: Konten pesan
        """
        self.messages.append({"role": role, "parts": [{"text": content}]})
        
        # Hapus pesan tertua jika melebihi batas
        if len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)
            
        self.last_update = time.time()

    def is_expired(self) -> bool:
        """Cek apakah history telah kedaluwarsa berdasarkan pengaturan timeout."""
        return (time.time() - self.last_update) > HISTORY_EXPIRE

    def get_context(self) -> list:
        """Dapatkan history terformat untuk Gemini API."""
        return self.messages

    def get_history_text(self) -> str:
        """Dapatkan history terformat sebagai text human-readable."""
        history_text = ""
        for msg in self.messages:
            role = msg["role"]
            content = msg["parts"][0]["text"]
            history_text += f"{role}: {content}\n"
        return history_text


def get_user_history(user_id: int) -> ChatHistory:
    """
    Dapatkan atau buat history chat user dengan penanganan expiration.
    
    Args:
        user_id: ID user Telegram
        
    Returns:
        Objek ChatHistory untuk user (baru atau yang sudah ada)
    """
    # Buat history baru jika belum ada atau sudah expired
    if user_id not in user_chats or user_chats[user_id].is_expired():
        user_chats[user_id] = ChatHistory()
        
    return user_chats[user_id]


def setup_gemini_model(model_name: str = DEFAULT_MODEL):
    """
    Setup model Gemini dengan safety settings dan konfigurasi generasi.
    
    Args:
        model_name: Nama varian model Gemini yang akan digunakan
        
    Returns:
        Instance GenerativeModel yang terkonfigurasi
    """
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings=SAFETY_SETTINGS,
            generation_config=GENERATION_CONFIG
        )
        return model
    except Exception as e:
        logger.error(f"Error saat setup model Gemini: {e}")
        raise


def is_developer_question(text: str) -> bool:
    """
    Cek apakah pesan bertanya tentang developer.
    
    Args:
        text: Teks pesan user
        
    Returns:
        True jika bertanya tentang developer, False jika tidak
    """
    text = text.lower()
    return any(re.search(pattern, text) for pattern in DEVELOPER_PATTERNS)


def get_developer_response(username: str) -> str:
    """
    Dapatkan respons informasi developer dengan format Markdown.
    
    Args:
        username: Nama display user untuk personalisasi
        
    Returns:
        Info developer dengan format Markdown untuk Telegram
    """
    responses = [
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` 💕",
        f"Ara ara~ {username}\\-kun tertarik sama penciptaku ya? Aku karya *Afdaan* lho\\! Bisa dikunjungi di `alif\\.horn\\-yastudio\\.com` ✨",
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` ya~ 🌸",
    ]
    return random.choice(responses)


def needs_search_query(prompt: str) -> bool:
    """
    Tentukan apakah prompt memerlukan pencarian informasi faktual.
    
    Args:
        prompt: Teks pesan dari user
        
    Returns:
        True jika perlu pencarian, False jika tidak
    """
    prompt_lower = prompt.lower()
    return (
        any(keyword in prompt_lower for keyword in SEARCH_KEYWORDS) or
        any(topic in prompt_lower for topic in SEARCH_TOPICS)
    )


async def generate_chat_response(
    prompt: str, 
    user_id: int, 
    context: Optional[CallbackContext] = None, 
    persona_context: Optional[str] = None
) -> str:
    """
    Generate respons AI dengan kemampuan pencarian dan context awareness.
    
    Args:
        prompt: Teks pesan user
        user_id: ID Telegram user
        context: CallbackContext untuk pengaturan bahasa
        persona_context: Konteks kepribadian untuk AI
        
    Returns:
        Respons AI yang digenerate
    """
    try:
        # Inisialisasi model dan tool
        chat_model = setup_gemini_model()
        chat = chat_model.start_chat()
        search_engine = SearchEngine()
        
        # Dapatkan language preference
        language = get_language(context) if context else "id"
        language_instruction = get_prompt_language_instruction(language, context)
        
        # Dapatkan history chat untuk context awareness
        chat_history = get_user_history(user_id)
        
        # Format context window
        context_window = ""
        history_text = chat_history.get_history_text()
        if history_text:
            # Ambil maksimal 3 pertukaran pesan terakhir
            history_lines = history_text.strip().split('\n')
            # Ambil maksimal 6 pesan terakhir (3 pertukaran) jika tersedia
            relevant_history = history_lines[-min(6, len(history_lines)):]
            context_window = "\n".join(relevant_history)
        
        # Tentukan apakah perlu pencarian
        should_search = needs_search_query(prompt)
        search_results = ""
        
        # Lakukan pencarian jika perlu
        if should_search:
            try:
                search_results = await asyncio.wait_for(
                    search_engine.search(prompt),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Pencarian timeout untuk: {prompt}")
                search_results = "Tidak dapat melakukan pencarian karena timeout."
            except Exception as e:
                logger.error(f"Error pencarian: {e}")
                search_results = f"Error saat melakukan pencarian: {str(e)}"
        
        # Buat prompt berdasarkan mode
        if should_search:
            smart_prompt = f"""
            {persona_context or ""}
            
            LANGUAGE PREFERENCE: {language_instruction}
            
            CONVERSATION HISTORY:
            {context_window}
            
            User's Question: {prompt}
            
            Search Results:
            {search_results}
            
            Instructions for your response:
            1. Start with a friendly greeting in your waifu persona style
            2. Always call the user as "[username]-kun" or "[username]-chan" (no space)
            3. Analyze the CONVERSATION HISTORY to understand the current context
            4. If the user's message is a follow-up question, connect it to the previous context
            5. Provide clear, accurate information from the search results
            6. Structure the information in an easy-to-read format
            7. Include relevant details like times, locations, and dates if available
            8. If the information is incomplete, suggest where the user can get more details
            9. End with a supportive, encouraging message
            10. Use appropriate emoji to enhance your response
            11. Make sure to maintain your character's personality
            12. By default respond in {"English" if language == "en" else "Indonesian"}, but if user requests another language, feel free to use that
            
            Respond in a helpful, informative way while staying in character and maintaining context awareness.
            """
        else:
            smart_prompt = f"""
            {persona_context or ""}
            
            LANGUAGE PREFERENCE: {language_instruction}
            
            CONVERSATION HISTORY:
            {context_window}
            
            User Message: {prompt}
            
            Instructions:
            1. Please respond naturally and in character as Alya-chan
            2. Always call the user as "[username]-kun" or "[username]-chan" (no space between name and honorific)
            3. Analyze the CONVERSATION HISTORY to understand the current context
            4. If the user's message is a follow-up question, connect it to the previous discussion
            5. Maintain context awareness throughout your response
            6. By default respond in {"English" if language == "en" else "Indonesian"}, but if user requests another language, feel free to use that
            
            Respond with context awareness while staying in character.
            """
        
        # Generate response dengan timeout handling
        try:
            with ThreadPoolExecutor() as executor:
                send_message_task = executor.submit(chat.send_message, smart_prompt)
                response = await asyncio.wait_for(
                    asyncio.wrap_future(send_message_task),
                    timeout=30.0
                )
            response_text = response.text
            
            # Simpan ke history
            chat_history.add_message("user", prompt)
            chat_history.add_message("assistant", response_text)
            
            return response_text
        except asyncio.TimeoutError:
            logger.warning(f"Generasi respons timeout untuk: {prompt}")
            if language == "en":
                return "Sorry~ Alya needs more time to process this message. Could you express it in a simpler way? 🥺"
            return "Gomennasai~ Alya butuh waktu lebih lama untuk memproses pesan ini. Bisa disampaikan dengan cara yang lebih sederhana? 🥺"
        
    except Exception as e:
        logger.error(f"Error di generate_chat_response: {e}")
        if context and get_language(context) == "en":
            return "Sorry darling~ There was an error... 🥺"
        return "Gomen ne sayang~ Ada error... 🥺"


# Inisialisasi model saat module dimuat
chat_model = setup_gemini_model(DEFAULT_MODEL)
image_model = setup_gemini_model(DEFAULT_MODEL)