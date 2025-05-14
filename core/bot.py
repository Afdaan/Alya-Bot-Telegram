"""
Bot Handler Setup for Alya Telegram Bot.

This module configures all handlers for the Telegram bot,
organizing them by type and priority.
"""

import logging
from telegram.ext import (
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler,
    Application
)

# Import all handlers
from handlers.command_handlers import start, help_command, reset_command, handle_search
from handlers.message_handlers import handle_message
from handlers.document_handlers import handle_document_image
from handlers.callback_handlers import handle_button_callback
from handlers.ping_handlers import ping_command
from handlers.dev_handlers import (
    update_command, stats_command, debug_command, shell_command,
    set_language_command
)

logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    """
    Setup all handlers for the bot with proper priority.
    
    Args:
        application: The Telegram Application instance
    """
    # =========================
    # Basic Command Handlers
    # =========================
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("lang", set_language_command))
    
    # =========================
    # Special Message Handlers (Higher Priority)
    # =========================
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^!search'), 
        handle_search,
        block=False
    ))
    
    # =========================
    # Callback Handlers
    # =========================
    application.add_handler(CallbackQueryHandler(handle_button_callback))
    
    # =========================
    # General Message Handlers
    # =========================
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message,
        block=False  # Non-blocking for better performance
    ))
    
    # =========================
    # Media Handlers
    # =========================
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        handle_document_image
    ))
    
    # =========================
    # Developer/Admin Commands
    # =========================
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("shell", shell_command))
    
    logger.info("All handlers have been set up successfully")