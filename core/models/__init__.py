"""Core model functionality for Alya Bot."""

# Standard library imports
from typing import Dict, Any

# Import from submodules
from .chat import (
    get_chat_response,
    generate_response,
    generate_chat_response
)
from .gemini import (
    initialize_gemini,
    get_current_gemini_key,
    convert_safety_settings
)
from .image import (
    generate_image_analysis,
    generate_document_analysis
)
from utils.context_manager import context_manager

# Define user_chats as a module-level variable
user_chats: Dict[int, Dict[str, Any]] = {}

# Re-export context manager functions
add_message_to_history = context_manager.add_message_to_history
recall_relevant_context = context_manager.recall_relevant_context
get_user_history = context_manager.get_conversation_history
clear_user_history = context_manager.clear_chat_history

__all__ = [
    'get_chat_response',
    'generate_response',
    'generate_chat_response',
    'initialize_gemini',
    'get_current_gemini_key',
    'convert_safety_settings',
    'add_message_to_history',
    'recall_relevant_context',
    'get_user_history',
    'clear_user_history',
    'user_chats',
    'generate_image_analysis',
    'generate_document_analysis'
]
