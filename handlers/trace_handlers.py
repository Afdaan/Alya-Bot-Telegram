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

from utils.context_manager import context_manager
from config.settings import (
    ANALYZE_PREFIX,
    SAUCE_PREFIX,
    GROUP_CHAT_REQUIRES_PREFIX,
    CHAT_PREFIX,
    ADDITIONAL_PREFIXES
)

logger = logging.getLogger(__name__)

# Semua kemungkinan prefiks untuk validasi
ALL_VALID_PREFIXES = [CHAT_PREFIX.lower(), ANALYZE_PREFIX.lower(), SAUCE_PREFIX.lower()] + \
                     [prefix.lower() for prefix in ADDITIONAL_PREFIXES] + \
                     ["!trace", "!sauce", "!ocr", "/trace", "/sauce", "/ocr"]

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
    
    # PERBAIKAN: Cek dulu apakah ini group chat & butuh prefix
    is_private_chat = message.chat.type == "private"
    caption_text = (message.caption or "").lower().strip()
    has_valid_prefix = any(caption_text.startswith(prefix) for prefix in ALL_VALID_PREFIXES)
    
    # Jika ini group chat dan kita butuh prefix, tapi tidak ada prefix valid, jangan proses
    if not is_private_chat and GROUP_CHAT_REQUIRES_PREFIX and not has_valid_prefix:
        logger.debug(f"Ignoring trace request in group without valid prefix. Caption: '{caption_text[:30]}...'")
        return
    
    # Use media interface instead of direct import
    from handlers.media_interface import handle_media_trace
    
    # Process using document handler
    await handle_media_trace(message, user)
    
    # Store context data using local function
    await store_media_context(message, user.id, 'trace')

async def handle_trace_command(message: Message, user: User, context: CallbackContext) -> None:
    """
    Handle trace (image analysis) command for both images and documents.
    
    Args:
        message: Telegram message with image or document
        user: User who sent the message
        context: Callback context
    """
    # PERBAIKAN: Validasi bahwa perintah ini memang dijalankan oleh command handler yang tepat
    # atau pesan dengan caption yang memiliki prefix command yang valid
    if not validate_command_prefix(message):
        # Jika tidak valid, jangan proses
        logger.debug(f"Ignoring non-command image analysis request from user {user.id}")
        return
        
    try:
        # Send initial processing message
        status_msg = await message.reply_text(
            "Menganalisis konten... 🔍",
            parse_mode=None
        )
        
        # ...existing code...
    except Exception as e:
        logger.error(f"Error in trace command: {e}")
        # ...error handling...

# Tambahkan fungsi validasi prefix
def validate_command_prefix(message: Message) -> bool:
    """
    Validate that a message contains a valid command prefix.
    
    Args:
        message: Telegram message to check
        
    Returns:
        True if message has valid command prefix, False otherwise
    """
    if not message:
        return False
        
    # Cek jika ini adalah hasil dari command handler (/trace, /sauce, dll)
    # Dalam kasus ini, message.caption mungkin None tapi tetap valid
    if hasattr(message, 'via_bot') and message.via_bot:
        return True
        
    # Cek apakah ini private chat (selalu valid)
    if message.chat.type == "private":
        return True
        
    # Periksa caption untuk command prefix
    caption = message.caption
    if not caption:
        return False
        
    caption_lower = caption.lower().strip()
    
    # Cek apakah caption dimulai dengan prefix valid
    return any(caption_lower.startswith(prefix) for prefix in ALL_VALID_PREFIXES)

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
