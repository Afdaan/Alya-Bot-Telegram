"""
Trace Handlers for Alya Telegram Bot.

This module provides handlers for image and document tracing/analysis
with persistent context storage.
"""

import logging
import time
from telegram import Update
from telegram.ext import CallbackContext

from handlers.document_handlers import handle_trace_command
from utils.context_manager import context_manager

logger = logging.getLogger(__name__)

async def handle_trace_request(update: Update, context: CallbackContext) -> None:
    """
    Process !trace command for document/image analysis with context persistence.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    message = update.message
    user = update.effective_user
    
    # Process using document handler
    await handle_trace_command(message, user)
    
    # If message has photo, store context
    if message.photo:
        # PERBAIKAN: Validasi tipe data dan error handling
        try:
            # Get user ID dan chat ID yang valid
            user_id = int(user.id)
            chat_id = int(message.chat.id)
            
            # Get the largest photo
            photo = message.photo[-1]
            
            # Store context data
            context_data = {
                'command': 'trace',
                'timestamp': int(time.time()),
                'media_type': 'image',
                'file_id': photo.file_id,
                'chat_type': message.chat.type,
                'caption': message.caption or "",
                'response_summary': "Image analysis completed"
            }
            
            # Tambahkan error handling
            try:
                context_manager.save_context(user_id, chat_id, 'trace', context_data)
                logger.debug(f"Trace context saved for image from user_id: {user_id}")
            except Exception as e:
                logger.error(f"Failed to save trace context for image: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"Type error in trace handler for image: {e}")
        
    # If message has document, store context
    elif message.document:
        # PERBAIKAN: Sama dengan yang di atas
        try:
            user_id = int(user.id)
            chat_id = int(message.chat.id)
            
            context_data = {
                'command': 'trace',
                'timestamp': int(time.time()),
                'media_type': 'document',
                'file_id': message.document.file_id,
                'file_name': message.document.file_name,
                'mime_type': message.document.mime_type,
                'caption': message.caption or "",
                'response_summary': "Document analysis completed"
            }
            
            try:
                context_manager.save_context(user_id, chat_id, 'trace', context_data)
                logger.debug(f"Trace context saved for document from user_id: {user_id}")
            except Exception as e:
                logger.error(f"Failed to save trace context for document: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"Type error in trace handler for document: {e}")
