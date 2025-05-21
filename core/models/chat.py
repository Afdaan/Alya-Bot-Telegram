"""Chat response generation using Gemini."""

import json
import logging
from typing import Dict, Any, Optional

from telegram import Update
from telegram.ext import CallbackContext
import google.generativeai as genai

from config.settings import DEFAULT_MODEL, GENERATION_CONFIG, DEFAULT_LANGUAGE, MAX_RESPONSE_LENGTH
from utils.context_manager import context_manager
from .gemini import convert_safety_settings

logger = logging.getLogger(__name__)

async def get_chat_response(update: Update, context: CallbackContext) -> str:
    """Get chat response with proper username handling."""
    try:
        # Get user info
        user = update.effective_user
        username = user.first_name
        user_id = user.id
        chat_id = update.effective_chat.id
        
        # Store username in context
        if not context.user_data.get("username"):
            context.user_data["username"] = username
            
        # Get and process message
        message_text = update.message.text if update.message else ""
        if message_text:
            context_manager.add_message_to_history(
                user_id=user_id,
                role="user",
                content=message_text,
                chat_id=chat_id,
                message_id=update.message.message_id
            )
        
        # Get context and generate response
        context_data = context_manager.recall_relevant_context(user_id, message_text, chat_id)
        response = await generate_response(message_text, username, user_id, context_data)
        
        # Save response to history
        context_manager.add_message_to_history(
            user_id=user_id,
            role="assistant", 
            content=response,
            chat_id=chat_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_chat_response: {e}")
        return f"Maaf {username}-kun, ada error saat memproses pesan. 😔"

async def generate_response(
    message: str,
    username: str,
    user_id: int,
    context_data: Optional[Dict] = None
) -> str:
    """Generate response using Gemini."""
    try:
        model = genai.GenerativeModel(
            model_name=DEFAULT_MODEL,
            generation_config=GENERATION_CONFIG,
            safety_settings=convert_safety_settings()
        )
        
        prompt = create_chat_prompt(message, username, context_data)
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            return f"Maaf {username}-kun, Alya tidak bisa merespon saat ini. 😔"
            
        return response.text
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"Gomenasai {username}-kun! Ada error: {str(e)[:100]}... 😔"

def create_chat_prompt(message: str, username: str, context_data: Optional[Dict]) -> str:
    """Create properly formatted chat prompt."""
    return f"""You are Alya, a tsundere anime girl bot. Follow these rules:
    
    1. ALWAYS use this EXACT response format:
       [roleplay action in {DEFAULT_LANGUAGE}]
       
       Main message with formatting (*bold*, _italic_) and 1-2 emoji
       
       (Optional) Additional casual response or comment
       
       {{emotion/mood in {DEFAULT_LANGUAGE}}}

    2. Format rules:
       - [actions] describe what you're doing in {DEFAULT_LANGUAGE}
       - Main message uses Markdown formatting (*bold*, _italic_) with 1-2 emoji
       - Optional message adds natural conversation flow 
       - {{emotions}} describe your feelings/mood in {DEFAULT_LANGUAGE}
       - Each section MUST be separated by blank lines
       - All Language should be consistent with the user's language but default to {DEFAULT_LANGUAGE}
       
    3. Example format (in Indonesian):
       [memalingkan wajah dengan kesal]
       
       *Mou*~ Kenapa kamu selalu menanyakan hal yang _memalukan_ seperti itu {username}-kun! 😤
       
       Lagipula... bukan berarti aku tidak suka atau apa...
       
       {{tersipu malu sambil menggembungkan pipi}}

    Current user: {username}
    Message: {message}
    
    Previous context:
    {json.dumps(context_data, indent=2) if context_data else 'No context available'}
    """

async def generate_chat_response(
    message: str,
    username: str,
    user_id: int,
    context_data: Optional[Dict] = None,
    max_length: int = MAX_RESPONSE_LENGTH,
    temperature: float = 0.7,
    persona: str = "tsundere",
    language: str = DEFAULT_LANGUAGE
) -> str:
    """Generate chat response using Gemini API.

    Args:
        message: User's message text
        username: User's display name
        user_id: Telegram user ID
        context_data: Optional conversation context
        max_length: Maximum response length
        temperature: Response randomness (0-1)
        persona: Persona style to use
        language: Response language
    
    Returns:
        Generated response text
    """
    try:
        # Use the existing generate_response function
        return await generate_response(
            message=message,
            username=username,
            user_id=user_id,
            context_data=context_data
        )
    except Exception as e:
        logger.error(f"Error in generate_chat_response: {e}")
        return f"Maaf {username}-kun, ada error saat membuat respons 😔"

# Export all public functions
__all__ = [
    'get_chat_response',
    'generate_response',
    'generate_chat_response'
]
