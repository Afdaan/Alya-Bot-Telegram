"""
Bot Core Setup Module for Alya Telegram Bot.

This module handles the initialization and setup of the bot,
including command handlers and middleware.
"""

import logging
import os
import time
from typing import Any, Dict, List

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, Application, ContextTypes, ConversationHandler, CallbackContext
)

from config.settings import (
    TELEGRAM_BOT_TOKEN, 
    DEVELOPER_IDS, 
    DEFAULT_LANGUAGE,
)
from config.logging_config import setup_logging
from utils.rate_limiter import limiter
from handlers.dev_handlers import update_command

# Import handlers
from handlers.command_handlers import start, help_command, reset_command, handle_search
from handlers.document_handlers import handle_document_image, handle_trace_command, handle_sauce_command
from handlers.message_handlers import handle_message
from handlers.callback_handlers import handle_callback_query
from handlers.roast_handlers import handle_roast_command, handle_github_roast

# Setup logging
logger = logging.getLogger(__name__)

def setup_handlers(app: Application) -> None:
    """
    Setup command and message handlers for the bot.
    
    Args:
        app: Telegram bot application instance
    """
    # Add handlers for commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    # Search command handler
    app.add_handler(CommandHandler("search", handle_search))
    
    # Document/media handlers
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL, 
        handle_document_image
    ))
    
    # Trace/sauce commands
    app.add_handler(CommandHandler("trace", _trace_command_handler))
    app.add_handler(CommandHandler("sauce", _sauce_command_handler))
    app.add_handler(CommandHandler("ocr", _trace_command_handler))  # OCR uses same handler for now
    
    # Callback query handler for buttons
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Roast command handlers
    app.add_handler(CommandHandler("roast", handle_roast_command))
    app.add_handler(CommandHandler("github_roast", handle_github_roast))
    
    # Message handler (should be last to catch all other messages)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message
    ))
    
    logger.info("All handlers have been registered")

# Simple bridge handlers to avoid circular imports
async def _trace_command_handler(update: Update, context: CallbackContext) -> None:
    """Bridge for trace/OCR command."""
    if not update.message:
        return
    await handle_trace_command(update.message, update.effective_user, context)

async def _sauce_command_handler(update: Update, context: CallbackContext) -> None:
    """Bridge for sauce command."""
    if not update.message:
        return
    await handle_sauce_command(update.message, update.effective_user, context)

async def post_init(app: Application) -> None:
    """
    Post-initialization setup.
    
    Args:
        app: Telegram bot application instance
    """
    # Set default language for the bot
    app.bot_data["language"] = DEFAULT_LANGUAGE
    
    # Log startup information
    logger.info("Bot is starting up")
    
    # Initialize rate limiter
    limiter.allowance = {"global": limiter.rate}
    limiter.last_check = {"global": time.time()}
    
    # Set up any required background tasks here
    # ...existing code...

def create_app() -> Application:
    """
    Create and configure the bot application instance.
    
    Returns:
        Configured Application instance
    """
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
    
    # Create application with persistence
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Setup handlers
    setup_handlers(application)
    
    return application

def run_bot() -> None:
    """Run the bot application."""
    # Setup logging first
    setup_logging()
    
    try:
        # Create and start the application
        application = create_app()
        application.run_polling()
    except Exception as e:
        logger.critical(f"Fatal error starting bot: {e}", exc_info=True)
        raise