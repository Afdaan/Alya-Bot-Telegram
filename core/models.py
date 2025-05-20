"""
LLM Handler for Alya Telegram Bot.

This module manages interactions with the Gemini AI model
and integrates with personas defined in `personas.py`.
"""

# Standard library imports
import logging
import asyncio
import time
import os
import re
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
import yaml
try:
    import google.generativeai as genai
except ImportError:
    raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

# Local imports
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
    HISTORY_EXPIRE,
    GEMINI_BACKUP_API_KEYS
)
from utils.rate_limiter import rate_limited, gemini_limiter, get_api_key_manager
# Fix imports untuk hindari circular dependency
from utils.context_manager import context_manager

# Setup logger
logger = logging.getLogger(__name__)

__all__ = [
    'ChatHistory',
    'add_message_to_history',
    'get_user_history',
    'clear_user_history',
    'check_rate_limit',
    'can_user_chat',
    'is_message_valid',
    'generate_chat_response',
    'generate_response',
    'fix_roleplay_format'
]

# --------------------
# Constants and Model Configuration
# --------------------

# Model version tracking for compatibility
GEMINI_API_VERSION = "1.0.0"

# Model capabilities for different versions
MODEL_CAPABILITIES = {
    # Free plan model - what we're using
    "gemini-2.0-flash-exp": {
        "max_tokens": 32768,  # Total context window
        "max_output_tokens": 2048,  # Free tier output limit 
        "supports_tools": True,
        "supports_images": True,
        "free_tier": True,
        "rate_limit": "60 calls per minute"  # Free tier rate limit
    },
    # Below are paid models - not currently used
    "gemini-1.0-pro": {
        "max_tokens": 8192,
        "supports_tools": False,
        "supports_images": True,
        "free_tier": False
    },
    "gemini-1.5-pro": {
        "max_tokens": 32768,
        "supports_tools": True,
        "supports_images": True,
        "free_tier": False
    }
}

# Definisikan _convert_safety_settings() SEBELUM digunakan
def _convert_safety_settings() -> List[Dict[str, Any]]:
    """
    Convert safety settings from config format to Gemini API format.
    
    Returns:
        List of safety setting dictionaries compatible with Gemini API
    """
    safety_settings_list = []
    try:
        for category, threshold in SAFETY_SETTINGS.items():
            if not isinstance(category, str) or not isinstance(threshold, str):
                logger.warning(f"Invalid safety setting: {category}={threshold}")
                continue
                
            # Convert from config format to Gemini API format
            safety_settings_list.append({
                "category": category,
                "threshold": threshold
            })
        
        return safety_settings_list
    except Exception as e:
        logger.error(f"Error converting safety settings: {e}")
        # Return safe default configuration
        return [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]

# Define necessary helper functions
def _get_current_gemini_key() -> str:
    """Get current Gemini API key from rotation manager."""
    return get_api_key_manager().get_current_key()

# Updated initialization using key from manager
try:
    # Rather than statically configuring, make this function dynamic
    def _get_gemini_model(model_name=DEFAULT_MODEL):
        """Get Gemini model with current API key from rotation."""
        current_key = _get_current_gemini_key()
        genai.configure(api_key=current_key)
        return genai.GenerativeModel(
            model_name=model_name,
            safety_settings=_convert_safety_settings(),
            generation_config=GENERATION_CONFIG
        )
    
    # Initial model setup (will be recreated with fresh key when needed)
    chat_model = _get_gemini_model(DEFAULT_MODEL)
except Exception as e:
    logger.error(f"Error initializing Gemini model: {e}")
    chat_model = None

# Global variables for state management
user_chats: Dict[int, 'ChatHistory'] = {}
rate_limits: Dict[int, datetime] = {}
request_timestamps: List[float] = []

# --------------------
# Chat History Management
# --------------------

class ChatHistory:
    """Class to manage user chat history with expiration."""
    
    def __init__(self) -> None:
        """Initialize a new chat history."""
        self.messages: List[Dict[str, Any]] = []
        self.last_update = time.time()

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the user's history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        if len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)
        self.last_update = time.time()

    def is_expired(self) -> bool:
        """
        Check if the chat history has expired.
        
        Returns:
            True if history has expired
        """
        return (time.time() - self.last_update) > HISTORY_EXPIRE

    def get_history_text(self) -> str:
        """
        Return chat history as a formatted text.
        
        Returns:
            Formatted history text
        """
        return "\n".join(f"{msg['role']}: {msg['content']}" for msg in self.messages)

# --------------------
# Utility Functions
# --------------------

def get_model_capabilities(model_name: str) -> Dict[str, Any]:
    """
    Get capabilities of the specified model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dictionary with model capabilities
    """
    return MODEL_CAPABILITIES.get(model_name, {
        "max_tokens": 8192,  # Safe default
        "supports_tools": False,
        "supports_images": False
    })

def add_message_to_history(user_id: int, content: str, role: str) -> None:
    """
    Add message to user chat history.
    
    Args:
        user_id: User ID 
        content: Message content
        role: Message role (user, assistant, system)
    
    Raises:
        ValueError: If parameters are invalid
    """
    if user_id is None or content is None or role is None:
        raise ValueError("Invalid parameters")
        
    if role not in ["user", "assistant", "system"]:
        raise ValueError("Invalid role")
        
    if user_id not in user_chats:
        user_chats[user_id] = ChatHistory()
        
    user_chats[user_id].add_message(role, content)

def get_user_history(user_id: int) -> List[Dict[str, Any]]:
    """
    Get user chat history messages.
    
    Args:
        user_id: User ID
    
    Returns:
        List of message dictionaries
    """
    if user_id not in user_chats:
        user_chats[user_id] = ChatHistory()
    return user_chats[user_id].messages

def clear_user_history(user_id: int) -> None:
    """
    Clear user chat history.
    
    Args:
        user_id: User ID
    """
    if user_id in user_chats:
        user_chats[user_id].messages = []

def check_rate_limit(user_id: int) -> bool:
    """
    Check if user is rate limited.
    
    Args:
        user_id: User ID
    
    Returns:
        True if user can send messages, False if rate limited
    """
    now = datetime.now()
    if user_id in rate_limits:
        last_request = rate_limits[user_id]
        if (now - last_request).seconds < 1:  # 1 second cooldown
            return False
    rate_limits[user_id] = now
    return True

def can_user_chat(user_id: int) -> bool:
    """
    Check if user can chat (e.g., not banned).
    
    Args:
        user_id: User ID
    
    Returns:
        True if user can chat
    """
    # Implement ban logic here if needed
    return True

def is_message_valid(content: str) -> bool:
    """
    Validate message content.
    
    Args:
        content: Message content
        
    Returns:
        True if message is valid
    """
    if not content or content.isspace():
        return False
    if len(content) > 4000:  # Max length
        return False
    return True

# --------------------
# Rate Limiting Functions
# --------------------

async def wait_for_rate_limit() -> None:
    """
    Enforce rate limiting for API requests.
    """
    global request_timestamps
    now = time.time()
    request_timestamps = [t for t in request_timestamps if now - t < 60]
    
    # Define constant for rate limiting - was using undefined var
    MAX_REQUESTS_PER_MINUTE = 60
    
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - request_timestamps[0])
        logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds.")
        await asyncio.sleep(wait_time)
    request_timestamps.append(now)

# --------------------
# Prompt Template Management
# --------------------

# Define paths to prompts
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PERSONA_DIR = os.path.join(BASE_DIR, "config", "persona")
PROMPT_TEMPLATE_PATH = os.path.join(PERSONA_DIR, "chat.yaml")
PERSONALITY_TEMPLATE_PATH = os.path.join(PERSONA_DIR, "personality.yaml")

def _load_personality_template() -> Dict[str, Any]:
    """
    Load personality template from YAML file.
    
    Returns:
        Dictionary of personality template configuration
    """
    try:
        if os.path.exists(PERSONALITY_TEMPLATE_PATH):
            with open(PERSONALITY_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Personality template not found at {PERSONALITY_TEMPLATE_PATH}, using defaults")
            return {}
    except Exception as e:
        logger.error(f"Error loading personality template: {e}")
        return {}

# Global personality template with lazy loading
_PERSONALITY_TEMPLATE = None

def get_personality_template() -> Dict[str, Any]:
    """
    Get personality template with caching.
    
    Returns:
        Dictionary of personality template configuration
    """
    global _PERSONALITY_TEMPLATE
    if (_PERSONALITY_TEMPLATE is None):
        _PERSONALITY_TEMPLATE = _load_personality_template()
    return _PERSONALITY_TEMPLATE

# Global prompt templates with lazy loading
_PROMPT_TEMPLATES = None

def _load_prompt_templates() -> Dict[str, Any]:
    """
    Load prompt templates from YAML file.
    
    Returns:
        Dictionary of prompt templates
    """
    try:
        if os.path.exists(PROMPT_TEMPLATE_PATH):
            with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        else:
            logger.warning(f"Prompt templates not found at {PROMPT_TEMPLATE_PATH}, using defaults")
            return {}
    except Exception as e:
        logger.error(f"Error loading prompt templates: {e}")
        return {}

def get_prompt_templates() -> Dict[str, Any]:
    """
    Get prompt templates with caching.
    
    Returns:
        Dictionary of prompt templates
    """
    global _PROMPT_TEMPLATES
    if _PROMPT_TEMPLATES is None:
        _PROMPT_TEMPLATES = _load_prompt_templates()
    return _PROMPT_TEMPLATES

# --------------------
# LLM Interaction Functions
# --------------------

async def generate_chat_response(
    message: str, 
    user_id: int, 
    context: Optional[CallbackContext] = None, 
    persona_context: Optional[str] = None,
    retry_count: int = 0  # Track retry attempts
) -> str:
    """
    Generate chat response using Gemini model with natural, freestyle approach.
    
    Args:
        message: Input message text
        user_id: User ID for history tracking
        context: CallbackContext for state
        persona_context: Personality context string
        retry_count: Track retry attempts
    
    Returns:
        Generated response text
    """
    global chat_model
    
    try:
        # Get language preference
        language = "id"  # Default to Indonesian
        if context and "language" in context.bot_data:
            language = context.bot_data["language"]
        
        # Ensure model is initialized with current API key
        chat_model = _get_gemini_model()
        
        # Get chat_id properly - critically important for memory recall
        chat_id = None
        if context:
            # Try to get from context.chat_data first
            if hasattr(context, 'chat_data') and isinstance(context.chat_data, dict):
                # Extract chat_id from context if available
                chat_id = context.chat_data.get("chat_id")
            
            # If not found yet, try update object
            if not chat_id and hasattr(context, 'update') and context.update:
                # Fix: Make sure update has effective_chat before accessing it
                if hasattr(context.update, 'effective_chat') and context.update.effective_chat:
                    chat_id = context.update.effective_chat.id
                    
        # Fall back to user_id if chat_id is still None
        if not chat_id:
            chat_id = user_id
            logger.debug(f"Couldn't get chat_id, falling back to user_id: {user_id}")
            
        # For debugging - print the values we're working with
        logger.debug(f"Memory context params - user_id: {user_id}, chat_id: {chat_id}")
        
        # Determine if we need to check for memory recall intent - SIMPLIFIED
        memory_recall_intent = detect_memory_recall_intent(message)
        
        # Debug memory recall
        if memory_recall_intent:
            logger.debug(f"Memory recall detected in message: {message[:50]}...")
        
        # Check cache only for non-memory-recall queries
        if not memory_recall_intent:
            cache_key = f"{user_id}:{message[:100]}"
            cached_response = response_cache.get(cache_key)
            if cached_response:
                # Still save the message to history even when using cached response
                add_message_to_history(user_id, message, "user")
                add_message_to_history(user_id, cached_response, "assistant")
                
                # Also save to persistent context - log at DEBUG level only
                logger.debug(f"Using cached response for user {user_id}")
                try:
                    # Run in thread to avoid blocking
                    # FIX: Function not defined earlier, fix async call without creating partial function
                    asyncio.create_task(_save_message_to_context(user_id, "user", message, chat_id, 1.2))
                    asyncio.create_task(_save_message_to_context(user_id, "assistant", cached_response, chat_id, 1.2))
                except Exception as e:
                    logger.error(f"Error saving cached messages: {e}")
                
                return cached_response
        
        # Get relevant conversation history with better formatting - SIMPLIFIED TO MATCH ORIGINAL
        conversation_context, history_messages = format_conversation_history(user_id, message, chat_id)
        
        # Add memory instructions - KEEP IT SIMPLE
        memory_instructions = ""
        if memory_recall_intent:
            memory_instructions = create_memory_instructions(message, True)
        
        # Get chat model with higher token limit for all responses
        chat = chat_model.start_chat(history=[])
        
        # Get personality template from YAML
        personality_config = get_personality_template()
        
        # Build personality prompt from template
        if personality_config and 'base' in personality_config and 'core_prompt' in personality_config['base']:
            # Use template from YAML
            personality_prompt = personality_config['base']['core_prompt']
        else:
            # Fallback to default if YAML not found or invalid
            logger.warning("Using default personality prompt - YAML template not found")
            personality_prompt = """
You are Alya (Alisa Mikhailovna Kujou), a half Japanese-Russian high school student with a tsundere personality.
You are smart, sometimes sarcastic, and exhibit a unique blend of shy and confident behaviors.
You initially act cold or dismissive but gradually show your caring side.
You occasionally use Russian expressions when emotional (like "Bozhe moy!", "Chert!", "Pryvet", "Da").
"""
        
        # Add persona-specific traits if provided
        if persona_context:
            personality_prompt += f"\n\n{persona_context}"
            
        # Add conversation context right after personality instructions
        if conversation_context:
            personality_prompt += f"\n\n{conversation_context}"
            
        # ALWAYS add memory instructions - they're critical
        personality_prompt += memory_instructions
            
        # Add language instruction from template if available
        if personality_config and 'language' in personality_config:
            lang_key = 'english' if language == 'en' else 'indonesian'
            language_instruction = personality_config['language'].get(lang_key, 
                f"\n\nIMPORTANT: RESPOND IN {'ENGLISH' if language == 'en' else 'INDONESIAN'} LANGUAGE.")
        else:
            # Fallback language instruction
            language_instruction = f"\n\nIMPORTANT: RESPOND IN {'ENGLISH' if language == 'en' else 'INDONESIAN'} LANGUAGE."
        
        # Get output format from template
        output_format = "\n\nUser message: {message}\n\nThink carefully and respond naturally as Alya with appropriate roleplay actions and emoji:"
        if personality_config and 'output_format' in personality_config:
            output_format = personality_config['output_format']
        
        # Format the complete prompt with user's message
        output_format = output_format.replace("{message}", message)
        full_prompt = f"{personality_prompt}{language_instruction}\n\n{output_format}"
        
        # Generate response with parameters optimized for free tier
        generation_config = {
            "max_output_tokens": 4096,   # Increased from 2048 to 4096 for longer responses
            "temperature": 0.92,          # Slightly higher temperature for more creativity
            "top_p": 0.97,                # Higher value allows more diverse word choices
            "top_k": 80                   # More candidates to choose from
        }
        
        # Send request to Gemini
        response = chat.send_message(full_prompt, generation_config=generation_config)
        response_text = response.text
        
        # Save message to both systems
        add_message_to_history(user_id, message, "user")
        add_message_to_history(user_id, response_text, "assistant")
        
        # Save to persistent context in background task to avoid blocking
        importance = 1.5 if memory_recall_intent else 1.2
        try:
            # Run database operations asynchronously - use fixed function
            asyncio.create_task(_save_message_to_context(user_id, "user", message, chat_id, importance))
            asyncio.create_task(_save_message_to_context(user_id, "assistant", response_text, chat_id, importance))
        except Exception as e:
            logger.error(f"Error saving to context: {e}")
        
        # Cache the response to avoid duplicate API calls (but not for memory recall)
        if not memory_recall_intent:
            cache_key = f"{user_id}:{message[:100]}"
            response_cache.set(cache_key, response_text)
        
        return response_text

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        
        # Check if it's a rate limit error (429)
        if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
            # Don't retry too many times - use API key manager directly from module import
            from utils.rate_limiter import api_key_manager
            
            if retry_count >= len(api_key_manager.all_keys):
                logger.error(f"Exhausted all API keys after {retry_count} retries")
                error_response = "Maaf, semua API quota habis. Coba lagi nanti ya... 🥺"
                return error_response
                
            # Rotate to new API key
            logger.info(f"Rotating API key due to rate limit (retry #{retry_count+1})")
            new_key = api_key_manager.rotate_key(force=True)
            
            # Update our global model with new key
            chat_model = _get_gemini_model()
            
            # Retry with new API key
            logger.info(f"Retrying with new API key: {new_key[:5]}...")
            return await generate_chat_response(
                message=message,
                user_id=user_id,
                context=context,
                persona_context=persona_context,
                retry_count=retry_count + 1  # Increment retry counter
            )
        
        # Handle other errors with standard message
        error_response = "Gomenasai! Ada error saat generate response... 🥺"
        if context and context.bot_data.get("language") == "en":
            error_response = "Sorry! There was an error generating a response... 🥺"
        return error_response

@rate_limited(gemini_limiter)
async def generate_response(prompt: str, persona_context: Optional[str] = None) -> str:
    """
    Simple wrapper to generate a response from Gemini model.
    
    Uses rate limiting to stay within free tier API limits.
    
    Args:
        prompt: The prompt to send to the model
        persona_context: Optional persona context to include
        
    Returns:
        Generated response as a string
    """
    try:
        # Get current API key from rotation manager
        current_key = _get_current_gemini_key()
        
        # Configure with current key
        genai.configure(api_key=current_key)
        
        # Get model with current key
        model = genai.GenerativeModel(
            model_name=DEFAULT_MODEL,
            generation_config=GENERATION_CONFIG,
            safety_settings=_convert_safety_settings()
        )
        
        # Create enhanced prompt with persona if provided
        full_prompt = prompt
        if persona_context:
            # Create a persona-enhanced prompt
            full_prompt = (
                f"You are Alya, a high school student with the following traits:\n\n"
                f"{persona_context}\n\n"
                f"User message: {prompt}\n\n"
                f"Respond in Indonesian language in character as Alya. Add appropriate "
                f"roleplay actions in asterisks (like *menghela napas*) and use at most 2 emoji."
            )
            
        # Generate response
        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt
        )
        
        # Check if we got a valid response
        if not response or not response.text:
            logger.warning("Empty response from Gemini")
            return ""
        
        return response.text.strip()
        
    except Exception as e:
        # Check if error is related to quota or rate limits
        if "quota" in str(e).lower() or "rate" in str(e).lower():
            logger.error(f"Rate limit or quota exceeded: {e}")
            
            # Try to rotate key and retry once
            from utils.rate_limiter import api_key_manager
            new_key = api_key_manager.rotate_key(force=True)
            logger.info(f"Rotated to new API key after quota error")
            
            try:
                # Try again with new key
                genai.configure(api_key=new_key)
                model = genai.GenerativeModel(
                    model_name=DEFAULT_MODEL,
                    generation_config=GENERATION_CONFIG,
                    safety_settings=_convert_safety_settings()
                )
                
                # Retry generation with new key
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt
                )
                
                if response and response.text:
                    return response.text.strip()
            except Exception as retry_error:
                logger.error(f"Retry with new key also failed: {retry_error}")
            
            return "Maaf, kuota API sudah habis. Coba lagi nanti ya."
        
        logger.error(f"Error in generate_response: {e}")
        return ""

# --------------------
# New Helper Functions for Better Memory Handling
# --------------------

def detect_memory_recall_intent(message: str) -> bool:
    """
    Detect if the message contains an intent to recall memory/previous messages.
    Natural language understanding without relying on strict regex patterns.
    
    Args:
        message: User's message
        
    Returns:
        Boolean indicating if message contains memory recall intent
    """
    # Lowercase for case-insensitive matching
    message_lower = message.lower().strip()
    
    # Use semantic understanding by checking for key phrases and contexts
    
    # Check for direct questions about previous messages/conversation
    if any(phrase in message_lower for phrase in [
        # Common Indonesian phrases for asking about previous messages
        "tadi nanya apa", "tadi aku tanya", "tadi gw tanya", "tadi saya tanya",
        "tadi aku bilang apa", "tadi gue bilang", "tadi gw bilang", "tadi saya bilang",
        "tadi aku ngomong apa", "tadi gue ngomong", "tadi gw ngomong", "tadi saya ngomong",
        "tadi kita bahas apa", "tadi kita omongin", 
        
        # Common questions about previous context
        "sebelumnya kita bahas", "yang sebelumnya", "pertanyaan sebelumnya",
        "yang tadi", "yang barusan", "yang tadi kita", 
        
        # Memory/recall oriented phrases
        "inget gak yang tadi", "masih inget gak", "masih ingat",
        "coba ingat", "coba inget", "coba ingatin", 
        
        # English equivalents (simpler check)
        "what did i ask", "what did i say", "i asked before", "previous question",
        "what were we talking", "remember what i"
    ]):
        logger.debug(f"Memory recall detected by phrase matching in: {message[:30]}...")
        return True
    
    # Check for context-based recall triggers
    if ("yang" in message_lower and any(word in message_lower for word in 
                                        ["tadi", "barusan", "sebelumnya"])):
        if any(verb in message_lower for verb in 
               ["tanya", "bilang", "ngomong", "bahas", "omongin"]):
            logger.debug(f"Memory recall detected by context in: {message[:30]}...")
            return True
    
    # Check for first-person references combined with recall indicators
    first_person = ["aku", "gw", "gue", "saya", "ku"]
    recall_verbs = ["tanya", "bilang", "ngomong", "bahas", "omongin", "katakan"]
    time_indicators = ["tadi", "sebelumnya", "barusan", "sebelum ini"]
    
    # Check if there's a combination of first person + recall verb + time indicator
    if (any(fp in message_lower for fp in first_person) and
        any(rv in message_lower for rv in recall_verbs) and
        any(ti in message_lower for ti in time_indicators)):
        logger.debug(f"Memory recall detected by component analysis in: {message[:30]}...")
        return True
    
    return False

def create_memory_instructions(message: str, is_memory_recall: bool = False) -> str:
    """
    Create instruction block for memory recall based on message intent.
    
    Args:
        message: User's message
        is_memory_recall: Whether message contains memory recall intent
    
    Returns:
        Memory instruction string
    """
    # Standard memory instructions
    standard_instructions = (
        "\n\nCONVERSATION MEMORY INSTRUCTIONS:\n"
        "1. ALWAYS maintain awareness of the conversation history shown above.\n"
        "2. If the user refers to previous messages or asks what they said before, directly "
        "reference the numbered conversation context.\n"
        "3. If asked about 'what I asked before' or similar questions (in ANY language or slang), "
        "quote their previous message from the context.\n"
        "4. Stay AWARE of what topics have been discussed previously.\n"
        "5. Don't invent or imagine previous messages that aren't in the context.\n"
    )
    
    # Enhanced instructions for memory recall intent
    if is_memory_recall:
        memory_recall_instructions = (
            "\n\nMEMORY RECALL REQUEST DETECTED - EXTREMELY IMPORTANT INSTRUCTIONS:\n"
            "1. User is asking what they said before or what they previously asked.\n"
            "2. YOU MUST search the RECENT CONVERSATION HISTORY section above.\n"
            "3. Find and QUOTE the most recent USER message before the current one.\n"
            "4. Format your response EXACTLY like this: \"Kamu bertanya: '[exact previous question]'\"\n"
            "5. NEVER make up content that isn't in the history.\n"
            "6. EXAMPLES OF CORRECT RESPONSES:\n"
            "   - User asks: \"tadi gw nanya apa?\" → You respond: \"Kamu bertanya: 'kamu bisa bahasa "
            "rusia?'\"\n"
            "   - User asks: \"what did I ask before?\" → You respond: \"Kamu bertanya: 'apakah kamu "
            "suka anime?'\"\n"
            "7. If you REALLY can't find any previous messages, respond: \"Maaf, sepertinya ini "
            "pertanyaan pertamamu.\"\n"
        )
        return standard_instructions + memory_recall_instructions
    
    return standard_instructions

def format_conversation_history(user_id: int, current_message: str, chat_id: Optional[int] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format conversation history for better context understanding.
    
    Args:
        user_id: User ID
        current_message: Current message from user
        chat_id: Optional chat ID for group chats
    
    Returns:
        Tuple containing (formatted_context_string, history_messages)
    """
    # Get conversation context from context_manager
    context_data = context_manager.recall_relevant_context(user_id, current_message, chat_id=chat_id)
    
    # Get messages from history
    history_messages = context_data.get("history", [])
    
    # If we have very few messages, try to get more
    if len(history_messages) < 3:
        # Try to get more from the history directly
        more_history = context_manager.get_chat_history(user_id, chat_id, 5)
        if (more_history and len(more_history) > len(history_messages)):
            history_messages = more_history
            
    # Get personal facts if available to provide more context
    personal_facts = context_data.get("personal_facts", {})
    
    # Limit to last 5 for context clarity (excluding current message)
    recent_messages = history_messages[-5:] if history_messages else []
    
    # Format conversation context
    conversation_context = "RECENT CONVERSATION HISTORY:\n"
    
    # If we have a reasonable history
    if recent_messages:
        for idx, msg in enumerate(recent_messages):
            role = msg.get("role", "").upper()
            role_display = "USER" if role == "USER" else "ALYA (YOU)"
            content = msg.get("content", "").strip()
            
            # Format with bold numbering and clear role separation
            conversation_context += f"MESSAGE {idx+1}: {role_display}: \"{content}\"\n"
            
        # Add current message reference
        conversation_context += f"\nCURRENT MESSAGE: USER: \"{current_message}\"\n"
    else:
        conversation_context += "No previous messages found.\n"
        conversation_context += f"\nCURRENT MESSAGE: USER: \"{current_message}\"\n"
    
    # Add personal facts if available
    if personal_facts:
        conversation_context += "\nUSER FACTS:\n"
        for fact_key, fact_value in personal_facts.items():
            conversation_context += f"- {fact_key}: {fact_value}\n"
    
    return conversation_context, history_messages

# Helper function to make DB operations async
async def _save_message_to_context(user_id: int, role: str, content: str, 
                                  chat_id: Optional[int] = None,
                                  importance: float = 1.0) -> None:
    """Save message to context database with proper await handling."""
    try:
        # Perbaikan: gunakan context_manager secara asinkron, tidak langsung await boolean
        await asyncio.to_thread(
            context_manager.add_message_to_history,
            user_id=user_id,
            role=role,
            content=content,
            chat_id=chat_id,
            importance=importance
        )
    except Exception as e:
        logger.error(f"Error saving message to context: {e}")

# Fix HTML formatting helper (needed by document analysis)
def fix_html_formatting(text: str) -> str:
    """
    Fix common HTML formatting issues in Gemini outputs.
    
    Args:
        text: Text with potential HTML formatting issues
        
    Returns:
        Text with fixed HTML formatting
    """
    # Replace potential markdown * with HTML tags
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    
    # Find all unclosed HTML tags or tag fragments
    unclosed_tag_pattern = r'</[a-zA-Z]*$'
    text = re.sub(unclosed_tag_pattern, '', text)
    
    # Check for unbalanced tags in common formats
    common_tags = ['b', 'i', 'u', 's', 'ul', 'li', 'ol', 'p', 'code', 'pre']
    
    # Count tag occurrences
    tag_counts = {}
    for tag in common_tags:
        open_count = text.count(f'<{tag}') + text.count(f'<{tag} ')
        close_count = text.count(f'</{tag}>')
        tag_counts[tag] = open_count - close_count
    
    # Close unclosed tags
    for tag, count in tag_counts.items():
        if count > 0:
            # Add closing tags at the end
            text += f'</{tag}>' * count
        elif count < 0:
            # Too many closing tags - remove excess closing tags
            excess_close = abs(count)
            for _ in range(excess_close):
                last_pos = text.rfind(f'</{tag}>')
                if (last_pos >= 0):
                    text = text[:last_pos] + text[last_pos + len(f'</{tag}>'):]
    
    # Fix incorrectly escaped < and >
    text = text.replace('&lt;b&gt;', '<b>')
    text = text.replace('&lt;/b&gt;', '</b>')
    text = text.replace('&lt;i&gt;', '<i>')
    text = text.replace('&lt;/i&gt;', '</i>')
    
    # Fix partial tags - find any leftover partial tags at the end
    partial_pattern = r'</?[a-zA-Z0-9]*$'
    match = re.search(partial_pattern, text)
    if match:
        text = text[:match.start()]
    
    return text

# Document analysis function that was missing
async def generate_document_analysis(text_content: str) -> str:
    """
    Generate analysis of document text using Gemini.
    
    Args:
        text_content: Text content of the document
        
    Returns:
        Detailed analysis text
    """
    try:
        # Limit text length to avoid token limits
        if len(text_content) > 8000:
            truncated_text = text_content[:8000] + "... [terpotong karena terlalu panjang]"
        else:
            truncated_text = text_content
            
        # Create prompt with better HTML formatting instructions
        prompt = f"""
        Analisis dokumen berikut dengan detail dan rangkum dengan jelas:
        
        ```
        {truncated_text}
        ```
        
        Berikan analisis komprehensif dengan format berikut:
        
        1. Rangkuman Dokumen: 
           - Jelaskan tentang apa isi dokumen ini dengan singkat dan jelas
           - Identifikasi jenis dokumen (artikel, email, laporan, kontrak, dll)
           
        2. Poin-Poin Penting (minimal 3-6 poin):
           - Ekstrak dan format ide utama atau informasi krusial
           - Jika ada angka atau statistik penting, sebutkan
           
        3. Topik utama:
           - Identifikasi tema atau subjek utama
           - Jelaskan pentingnya topik ini dalam dokumen
           
        4. Analisis Gaya dan Nada:
           - Apakah dokumen formal/informal
           - Apakah tujuan dokumen informatif, persuasif, edukatif, dll
        
        INSTRUKSI PENTING FORMAT:
        - GUNAKAN HANYA tag HTML yang valid dan lengkap (<b></b> untuk bold, <i></i> untuk italic)
        - JANGAN PERNAH gunakan simbol markdown seperti *, **, _, __ dll
        - PASTIKAN setiap tag yang dibuka SELALU ditutup dengan benar
        - VERIFIKASI semua tag dibuka dan ditutup dengan benar
        - JANGAN gunakan tag yang tidak didukung Telegram seperti <div>, <span>, dsb
        
        INSTRUKSI GAYA:
        - Tulis dalam Bahasa Indonesia
        - Gunakan gaya bahasa tsundere yang sedikit sok tau tapi tetap informatif
        - Sisipkan sedikit ekspresi Rusia seperti "ponyatno?" atau "da?"
        - Maksimal gunakan 2 emoji di seluruh teks
        - Hindari bahasa yang tidak sopan
        
        PENTING: PERIKSA KEMBALI output akhir dan pastikan tidak ada tag HTML yang tidak lengkap
        atau tidak ditutup dengan benar. Semua tag HARUS memiliki pasangan penutupnya.
        """
        
        # Use current API key from rotation
        current_key = _get_current_gemini_key()
        genai.configure(api_key=current_key)
        
        # Get model with current configuration
        model = genai.GenerativeModel(
            model_name=DEFAULT_MODEL,
            generation_config={
                "max_output_tokens": 1500,   # Increased for better document analysis
                "temperature": 0.7,          # More factual for analysis
                "top_p": 0.95,
                "top_k": 40
            },
            safety_settings=_convert_safety_settings()
        )
        
        # Generate response
        response = await asyncio.to_thread(
            model.generate_content,
            prompt
        )
        
        analysis = response.text if response and response.text else "Tidak dapat menganalisis dokumen."
        
        # Fix possible HTML formatting issues with improved function
        analysis = fix_html_formatting(analysis)
        
        # Limit to 4000 characters for document analysis
        if len(analysis) > 4000:
            analysis = analysis[:4000] + "..."
        
        # Final safety check - find any unclosed tags at end of string
        # This specifically targets the "</u" problem
        if re.search(r'</?[a-zA-Z0-9]*$', analysis):
            analysis = re.sub(r'</?[a-zA-Z0-9]*$', '', analysis)
        
        return analysis
    except Exception as e:
        logger.error(f"Gemini document analysis error: {e}")
        return f"<i>Tidak dapat menganalisis dokumen: {str(e)[:100]}...</i>"

# Function to analyze images that was missing
async def generate_image_analysis(image_path: str, prompt: Optional[str] = None) -> str:
    """
    Generate analysis of image using Gemini.
    
    Args:
        image_path: Path to image file
        prompt: Optional custom prompt to use
        
    Returns:
        Analysis text
    """
    try:
        import PIL.Image
        
        # Use current API key from rotation
        current_key = _get_current_gemini_key()
        genai.configure(api_key=current_key)
        
        # Open image
        image = PIL.Image.open(image_path)
        
        # Create default prompt if not provided
        if not prompt:
            prompt = """
            Analisis gambar ini dengan detail.
            1. Jelaskan apa yang terlihat dalam gambar
            2. Identifikasi objek utama, orang, atau elemen penting
            3. Jelaskan konteks gambar bila memungkinkan
            4. Berikan informasi tambahan yang relevan
            
            Gunakan bahasa Indonesia yang natural, dengan sedikit sentuhan tsundere.
            Kamu bisa menggunakan tag HTML <b></b> untuk teks penting dan <i></i> untuk penekanan.
            Jangan gunakan simbol markdown seperti *, **.
            Maksimal gunakan 2 emoji dalam responmu.
            """
        
        # Get model with current configuration - perlu define IMAGE_MODEL
        from config.settings import IMAGE_MODEL
        
        model = genai.GenerativeModel(
            model_name=IMAGE_MODEL,
            generation_config={
                "max_output_tokens": 800,
                "temperature": 0.8,
                "top_p": 0.95,
                "top_k": 40
            },
            safety_settings=_convert_safety_settings()
        )
        
        # Generate response with image
        response = await asyncio.to_thread(
            model.generate_content,
            [prompt, image]
        )
        
        analysis = response.text.strip() if response and response.text else "Tidak dapat menganalisis gambar."
        
        # Fix HTML formatting and ensure valid HTML for Telegram
        analysis = fix_html_formatting(analysis)
        
        # Limit length of analysis
        if len(analysis) > 3000:
            analysis = analysis[:3000] + "..."
        
        return analysis
    except Exception as e:
        logger.error(f"Gemini image analysis error: {e}")
        return f"<i>Tidak dapat menganalisis gambar dengan Gemini: {str(e)[:100]}...</i>"

# Function for roleplay formatting that was mistakenly removed
def fix_roleplay_format(text: str) -> str:
    """
    Fix and format roleplay actions in text for MarkdownV2.
    
    Args:
        text: Text with roleplay actions
        
    Returns:
        Text with properly formatted roleplay actions
    """
    # Already escaped text with \* - convert to italic for proper roleplay formatting
    # Match text between \*...\* and format as italics
    pattern = r'\\*([^\\*]+)\\*'
    result = re.sub(pattern, r'_\1_', text)
    
    return result