"""
Trace Handlers for Alya Telegram Bot.

This module provides handlers for image and document tracing/analysis
with persistent context storage.
"""

import logging
import time
from typing import Optional, Union
from telegram import Update, Message, User
from telegram.ext import CallbackContext

# Remove circular import
# from handlers.document_handlers import handle_trace_command
from utils.context_manager import context_manager
from config.settings import ANALYZE_PREFIX

logger = logging.getLogger(__name__)

async def handle_trace_request(update: Update, context: CallbackContext) -> None:
    """
    Process trace command for document/image analysis with context persistence.
    
    Args:
        update: Telegram update object
        context: CallbackContext object
    """
    if not update.message:
        logger.warning("Received trace request without a message")
        return
    
    message = update.message
    user = update.effective_user
    
    # Use media interface instead of direct import
    from handlers.media_interface import handle_media_trace
    
    # Process using document handler
    await handle_media_trace(message, user)
    
    # Store context data using local function
    await store_media_context(message, user.id, 'trace')

async def store_media_context(
    message: Message, 
    user_id: int, 
    context_type: str, 
    additional_data: Optional[dict] = None
) -> None:
    """
    Store media related context for persistence.
    
    Args:
        message: Message containing media
        user_id: User ID
        context_type: Type of context (trace, sauce, etc.)
        additional_data: Optional additional context data
    """
    try:
        chat_id = message.chat.id
        
        # Basic context data
        context_data = {
            'command': context_type,
            'timestamp': int(time.time()),
            'chat_id': chat_id,
            'message_id': message.message_id,
            'has_photo': bool(message.photo),
            'has_document': bool(message.document),
            'caption': message.caption,
        }
        
        # Add any additional data provided
        if additional_data:
            context_data.update(additional_data)
        
        # Save to context manager
        context_manager.save_context(user_id, chat_id, f'media_{context_type}', context_data)
        logger.debug(f"Stored {context_type} context for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error saving media context: {e}")
