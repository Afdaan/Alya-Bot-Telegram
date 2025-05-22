"""
Media Interface Module for Alya Telegram Bot.

This module provides a clean interface for media handling functionality,
connecting document handlers with bot initialization without circular imports.
"""

import logging
from typing import Optional
from telegram import Update, Message, User
from telegram.ext import Application, CommandHandler

logger = logging.getLogger(__name__)

# Function to setup media handlers
def setup_media_handlers(app: Application) -> None:
    """
    Setup all media-related command handlers.
    
    Args:
        app: Telegram bot application
    """
    # Import document_handlers here to avoid circular imports
    from handlers.document_handlers import handle_trace_command, handle_sauce_command
    
    # Add trace/image analysis command
    app.add_handler(CommandHandler("trace", trace_handler))
    app.add_handler(CommandHandler("sauce", sauce_handler))
    app.add_handler(CommandHandler("ocr", ocr_handler))
    
    logger.info("Media handlers registered successfully")

# Bridge functions to avoid circular imports
async def trace_handler(update: Update, context) -> None:
    """Bridge function for trace command."""
    if not update.message:
        return
        
    # Import here to avoid circular imports
    from handlers.document_handlers import handle_trace_command
    
    await handle_trace_command(update.message, update.effective_user, context)

async def sauce_handler(update: Update, context) -> None:
    """Bridge function for sauce command."""
    if not update.message:
        return
        
    # Import here to avoid circular imports
    from handlers.document_handlers import handle_sauce_command
    
    await handle_sauce_command(update.message, update.effective_user, context)

async def ocr_handler(update: Update, context) -> None:
    """Bridge function for OCR command."""
    if not update.message:
        return
        
    # Import here to avoid circular imports
    from handlers.document_handlers import handle_ocr_command
    
    # Fallback to trace handler if OCR handler not available
    try:
        await handle_ocr_command(update.message, update.effective_user, context)
    except (ImportError, AttributeError):
        logger.warning("OCR handler not available, falling back to trace")
        await handle_trace_command(update.message, update.effective_user, context)

# Legacy function to maintain backward compatibility
async def handle_media_trace(message: Message, user: User) -> None:
    """
    Legacy function for handling media trace requests.
    
    Args:
        message: Telegram message with media
        user: User who sent the message
    """
    # Import here to avoid circular imports
    from handlers.document_handlers import handle_trace_command
    
    # Create dummy context
    class DummyContext:
        def __init__(self):
            self.bot = None
            
    dummy_context = DummyContext()
    
    try:
        await handle_trace_command(message, user, dummy_context)
    except Exception as e:
        logger.error(f"Error in handle_media_trace: {e}")
