"""
Media Message Handlers for Alya Bot.

This module handles various media types sent to the bot, including
photos, documents, audio, and video files.
"""

import logging
from typing import Optional, List, Dict, Any

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

logger = logging.getLogger(__name__)

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
    photo = update.message.photo[-1]  # Get highest resolution
    
    logger.info(f"Received photo from user {user.id}: {photo.file_id}")
    
    # For now just acknowledge receipt
    await update.message.reply_text(
        "Aku menerima fotomu. Apa yang harus kulakukan dengan ini?"
    )

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
    document = update.message.document
    
    logger.info(f"Received document from user {user.id}: {document.file_name}")
    
    # For now just acknowledge receipt
    await update.message.reply_text(
        "Aku menerima dokumenmu. Apa yang harus kulakukan dengan ini?"
    )

async def handle_audio(update: Update, context: CallbackContext) -> None:
    """
    Handle audio files sent to the bot.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    if not update.message or not update.message.audio:
        return
    
    user = update.effective_user
    audio = update.message.audio
    
    logger.info(f"Received audio from user {user.id}: {audio.title or 'Untitled'}")
    
    # For now just acknowledge receipt
    await update.message.reply_text(
        "Aku menerima file audiomu. Apa yang harus kulakukan dengan ini?"
    )

async def handle_voice(update: Update, context: CallbackContext) -> None:
    """
    Handle voice messages sent to the bot.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    if not update.message or not update.message.voice:
        return
    
    user = update.effective_user
    voice = update.message.voice
    
    logger.info(f"Received voice message from user {user.id}: {voice.file_id}")
    
    # For now just acknowledge receipt
    await update.message.reply_text(
        "Aku menerima pesan suaramu. Maaf, aku belum bisa memproses pesan suara."
    )

def register_media_handlers(app: Application) -> None:
    """
    Register all media handlers with the application.
    
    Args:
        app: The telegram application instance
    """
    # Photo handler
    app.add_handler(MessageHandler(
        filters.PHOTO & ~filters.COMMAND,
        handle_photo
    ))
    
    # Document handler
    app.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.COMMAND,
        handle_document
    ))
    
    # Audio handler
    app.add_handler(MessageHandler(
        filters.AUDIO & ~filters.COMMAND,
        handle_audio
    ))
    
    # Voice handler
    app.add_handler(MessageHandler(
        filters.VOICE & ~filters.COMMAND,
        handle_voice
    ))
    
    logger.info("All media handlers registered successfully")
