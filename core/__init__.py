"""
Core Module for Alya Telegram Bot.

This module provides the core functionality and models for the bot,
including Gemini AI integration, persona management, and response generation.
"""

from core.models import (
    generate_chat_response, 
    generate_response,
    add_message_to_history,
    get_user_history,
    clear_user_history
)

from core.personas import (
    persona_manager,
    get_persona_context
)

from core.mood_manager import (
    mood_manager,
    get_mood_response,
    format_with_mood
)

# Import the new modules for better emotion handling
from core.emotion_system import (
    emotion_engine,
    detect_emotion,
    update_emotion,
    get_emotion,
    enhance_response as enhance_with_emotion
)

from core.roleplay_actions import (
    roleplay_manager,
    get_action,
    enhance_response as enhance_with_roleplay
)

__all__ = [
    # Models
    'generate_chat_response', 'generate_response',
    'add_message_to_history', 'get_user_history', 'clear_user_history',
    
    # Personas
    'persona_manager', 'get_persona_context',
    
    # Mood management (legacy)
    'mood_manager', 'get_mood_response', 'format_with_mood',
    
    # New emotion system
    'emotion_engine', 'detect_emotion', 'update_emotion', 
    'get_emotion', 'enhance_with_emotion',
    
    # Roleplay actions
    'roleplay_manager', 'get_action', 'enhance_with_roleplay'
]