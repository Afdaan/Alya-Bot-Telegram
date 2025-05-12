import logging
import google.generativeai as genai
import time
import re
import random

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
        f"Ehehe~ {username}\\-kun penasaran ya? Aku dibuat oleh *Afdaan* lho\\! Kalau mau kenal lebih dekat, bisa cek profil nya di `alif\\.horn\\-yastudio\\.com` 💕",
        f"*Afdaan* yang menciptakan aku untuk menemani {username}\\-kun\\! Mau tau lebih banyak? Cek website nya di `alif\\.horn\\-yastudio\\.com` ya~ 🌸",
        f"Ara ara~ {username}\\-kun tertarik sama penciptaku ya? Aku karya *Afdaan* lho\\! Bisa dikunjungi di `alif\\.horn\\-yastudio\\.com` ✨"
    ]
    return random.choice(responses)

def generate_chat_response(prompt: str, user_id: int, persona_context: str = None) -> str:
    try:
        # Check for developer question first
        if is_developer_question(prompt):
            username = prompt.split(':')[0] if ':' in prompt else ''
            return get_developer_response(username)
            
        history = get_user_history(user_id)
        
        system_prompt = """
        Important instructions:
        1. User's name must be followed by honorifics (-kun, -chan, -san)
        2. The message after "User:" contains the user's message, not their name
        3. Always use the username from the history/context, not from the message content
        4. Never interpret the message content as a username
        """
        
        # Combine history and current prompt
        full_prompt = system_prompt + "\n\n"
        
        # Add persona if it's a new conversation
        if persona_context and not history.messages:
            full_prompt += f"System: {persona_context}\n"
        
        # Add conversation history
        full_prompt += history.get_history_text()
        
        # Add current prompt with username in context
        username_context = f"Current username: {prompt.split()[0]}\n"  # Get first word as context
        full_prompt += username_context
        full_prompt += f"User message: {prompt}\n"
        
        # Generate response
        chat = chat_model.start_chat()
        response = chat.send_message(full_prompt)
        
        # Save to history
        history.add_message("user", prompt)
        history.add_message("assistant", response.text)
        
        return response.text
    except Exception as e:
        logger.error(f"Error in generate_chat_response: {e}")
        return "Gomen ne sayang~ Alya sedang bingung.. Bisa diulang? 🥺❤️"