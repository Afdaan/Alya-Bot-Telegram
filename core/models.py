import logging
import google.generativeai as genai

from config.settings import (
    GEMINI_API_KEY, 
    DEFAULT_MODEL, 
    SAFETY_SETTINGS, 
    GENERATION_CONFIG
)

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Dictionary to store chat history for each user
user_chats = {}

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

def generate_chat_response(prompt: str, persona_context: str = None) -> str:
    """Generate a chat response with configurable output."""
    try:
        # Start new chat
        chat = chat_model.start_chat(history=[])
        
        # Combine persona and prompt if persona is provided
        full_prompt = f"{persona_context}\n\nUser Question: {prompt}" if persona_context else prompt
        response = chat.send_message(full_prompt)
        
        return response.text
    except Exception as e:
        logger.error(f"Error in generate_chat_response: {e}")
        return "Gomen ne sayang~ Alya sedang bingung.. Bisa diulang? 🥺❤️"