"""
Media Message Handlers for Alya Bot.

This module handles various media types sent to the bot, including
photos and documents.
"""

import logging
from typing import Optional, List, Dict, Any

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

from config.settings import (
    GROUP_CHAT_REQUIRES_PREFIX,
    CHAT_PREFIX,
    ANALYZE_PREFIX,
    SAUCE_PREFIX,
    ADDITIONAL_PREFIXES
)

logger = logging.getLogger(__name__)

# Combine all valid prefixes for media commands
ALL_VALID_PREFIXES = [
    CHAT_PREFIX.lower(), 
    ANALYZE_PREFIX.lower(), 
    SAUCE_PREFIX.lower()
] + [prefix.lower() for prefix in ADDITIONAL_PREFIXES] + [
    "!trace", "!sauce", "!ocr", "/trace", "/sauce", "/ocr"
]

async def handle_photo(update: Update, context: CallbackContext) -> None:
    """
    Handle photos sent to the bot.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    if not update.message or not update.message.photo:
        return
    
    user = update.effective_user
    message = update.message
    
    # Check if in group chat and enforce prefix requirements
    is_group_chat = message.chat.type in ["group", "supergroup"]
    
    if is_group_chat and GROUP_CHAT_REQUIRES_PREFIX:
        # Check for valid caption prefix
        caption = message.caption or ""
        caption_lower = caption.lower().strip()
        has_valid_prefix = any(caption_lower.startswith(prefix) for prefix in ALL_VALID_PREFIXES)
        
        # Check if replying to bot
        is_reply_to_bot = (
            message.reply_to_message and
            message.reply_to_message.from_user and
            message.reply_to_message.from_user.id == context.bot.id
        )
        
        # Check if bot is mentioned
        mentions_bot = (
            context.bot.username and 
            f"@{context.bot.username.lower()}" in caption_lower
        )
        
        # If none of the conditions are met, silently ignore in group chats
        if not (has_valid_prefix or is_reply_to_bot or mentions_bot):
            logger.debug(f"Ignoring photo in group chat without valid prefix from user {user.id}")
            return
    
    photo = update.message.photo[-1]  # Get highest resolution
    logger.info(f"Received photo from user {user.id}: {photo.file_id}")
    
    # Forward to document_handlers to handle image analysis correctly
    from handlers.document_handlers import handle_document_image
    await handle_document_image(update, context)

async def handle_document(update: Update, context: CallbackContext) -> None:
    """
    Handle documents sent to the bot.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    if not update.message or not update.message.document:
        return
    
    user = update.effective_user
    message = update.message
    
    # Check if in group chat and enforce prefix requirements
    is_group_chat = message.chat.type in ["group", "supergroup"]
    
    if is_group_chat and GROUP_CHAT_REQUIRES_PREFIX:
        # Check for valid caption prefix
        caption = message.caption or ""
        caption_lower = caption.lower().strip()
        has_valid_prefix = any(caption_lower.startswith(prefix) for prefix in ALL_VALID_PREFIXES)
        
        # Check if replying to bot
        is_reply_to_bot = (
            message.reply_to_message and
            message.reply_to_message.from_user and
            message.reply_to_message.from_user.id == context.bot.id
        )
        
        # Check if bot is mentioned
        mentions_bot = (
            context.bot.username and 
            f"@{context.bot.username.lower()}" in caption_lower
        )
        
        # If none of the conditions are met, silently ignore in group chats
        if not (has_valid_prefix or is_reply_to_bot or mentions_bot):
            logger.debug(f"Ignoring document in group chat without valid prefix from user {user.id}")
            return
    
    document = update.message.document
    logger.info(f"Received document from user {user.id}: {document.file_name}")
    
    # Forward to document_handlers to handle document analysis correctly
    from handlers.document_handlers import handle_document_image
    await handle_document_image(update, context)

def register_media_handlers(app: Application) -> None:
    """
    Register all media handlers with the application.
    
    Args:
        app: The telegram application instance
    """
    # Photo handler - ensure correct prefix validation
    app.add_handler(MessageHandler(
        filters.PHOTO & ~filters.COMMAND,
        handle_photo
    ))
    
    # Document handler
    app.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.COMMAND,
        handle_document
    ))
    
    logger.info("Photo and document handlers registered successfully")
