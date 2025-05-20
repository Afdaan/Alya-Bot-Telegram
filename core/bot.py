"""
Bot Core Setup Module for Alya Telegram Bot.

This module handles the initialization and setup of the bot,
including command handlers and middleware.
"""

import logging
import os
import time
import re
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
    GROUP_CHAT_REQUIRES_PREFIX,
    CHAT_PREFIX,
    ADDITIONAL_PREFIXES,
    ANALYZE_PREFIX,
    SAUCE_PREFIX,
    ROAST_PREFIX
)
from config.logging_config import setup_logging
from utils.rate_limiter import limiter

# Import handlers
from handlers.command_handlers import start, help_command, reset_command, handle_search, ping_command # Tambah ping_command disini
from handlers.document_handlers import handle_document_image, handle_trace_command, handle_sauce_command
from handlers.message_handlers import handle_message, process_chat_message
from handlers.callback_handlers import handle_callback_query
from handlers.roast_handlers import handle_roast_command, handle_github_roast
# Import developer handlers
from handlers.dev_handlers import register_dev_handlers

# Setup logging
logger = logging.getLogger(__name__)

def setup_handlers(app: Application) -> None:
    """
    Setup command and message handlers for the bot.
    
    Args:
        app: Telegram bot application instance
    """
    # Add handlers for basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("search", handle_search))
    app.add_handler(CommandHandler("ping", ping_command, filters=filters.ChatType.PRIVATE))
    
    # Register developer command handlers
    register_dev_handlers(app)

    # Handle !ai prefix (chat commands)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f'^{CHAT_PREFIX}\\b'),
        handle_chat_prefix
    ))
    
    # Handle !alya prefix (alternative chat)
    for prefix in ADDITIONAL_PREFIXES:
        if prefix.startswith('!'):  # Only handle text prefixes, not mentions
            app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(f'^{prefix}\\b'),
                handle_chat_prefix
            ))
    
    # Handle !trace prefix (image analysis)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f'^{ANALYZE_PREFIX}\\b'),
        handle_trace_prefix
    ))
    
    # Handle !sauce prefix (reverse image search)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f'^{SAUCE_PREFIX}\\b'),
        handle_sauce_prefix
    ))
    
    # Handle !search prefix (web search)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex('^!search\\b'),
        handle_search_prefix
    ))
    
    # Handle !ocr prefix (text extraction)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex('^!ocr\\b'),
        handle_ocr_prefix
    ))
    
    # Handle !roast prefix (roasting)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f'^{ROAST_PREFIX}\\b'),
        handle_roast_prefix
    ))
    
    # Media handler with caption commands - FIX: Using regex instead of lambda function
    caption_prefixes = [
        re.escape(ANALYZE_PREFIX), re.escape(SAUCE_PREFIX), "!ocr",
        "/trace", "/sauce", "/ocr"
    ]
    caption_pattern = f"^({('|'.join(caption_prefixes))})"
    
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.Document.ALL) & 
        filters.CaptionRegex(caption_pattern),
        handle_document_image
    ))
    
    # Slash command handlers for media operations
    app.add_handler(CommandHandler("trace", _trace_command_handler))
    app.add_handler(CommandHandler("sauce", _sauce_command_handler))
    app.add_handler(CommandHandler("ocr", _trace_command_handler))  # OCR uses same handler
    
    # Roast command handlers
    app.add_handler(CommandHandler("roast", handle_roast_command))
    app.add_handler(CommandHandler("github_roast", handle_github_roast))
    
    # Callback query handler for buttons
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # General message handler (runs after text command handlers)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("All handlers have been registered")

# Bridge handlers to avoid circular imports
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

# SIMPLIFIED PREFIX HANDLERS - Each handler is dedicated to a specific prefix type

async def handle_chat_prefix(update: Update, context: CallbackContext) -> None:
    """
    Handle !ai and !alya prefixes for chat.
    """
    if not update.message or not update.message.text:
        return
        
    message_text = update.message.text.strip()
    
    # Change log level from INFO to DEBUG to reduce noise
    if hasattr(logger, 'debug'):
        logger.debug(f"Chat prefix detected: '{message_text[:20]}...'")
    
    # Extract everything after the prefix
    if message_text.lower().startswith(CHAT_PREFIX):
        processed_text = message_text[len(CHAT_PREFIX):].strip()
    elif any(message_text.lower().startswith(prefix) for prefix in ADDITIONAL_PREFIXES):
        # Find which prefix was used
        used_prefix = next(prefix for prefix in ADDITIONAL_PREFIXES if message_text.lower().startswith(prefix))
        processed_text = message_text[len(used_prefix):].strip()
    else:
        processed_text = ""
    
    # Check if it's a roast command
    if processed_text.lower().startswith("roast "):
        roast_args = processed_text[6:].strip()
        context.args = roast_args.split()
        await handle_roast_command(update, context)
    else:
        # Process as regular chat
        await process_chat_message(update, context, processed_text)

async def handle_trace_prefix(update: Update, context: CallbackContext) -> None:
    """
    Handle !trace prefix for image analysis.
    """
    # Change log level from INFO to DEBUG
    logger.debug(f"Trace prefix detected: '{update.message.text[:20]}...'")
    await handle_trace_command(update.message, update.effective_user, context)

async def handle_sauce_prefix(update: Update, context: CallbackContext) -> None:
    """
    Handle !sauce prefix for reverse image search.
    """
    # Change log level from INFO to DEBUG
    logger.debug(f"Sauce prefix detected: '{update.message.text[:20]}...'")
    await handle_sauce_command(update.message, update.effective_user, context)

async def handle_search_prefix(update: Update, context: CallbackContext) -> None:
    """
    Handle !search prefix for web search.
    """
    if not update.message or not update.message.text:
        return
        
    message_text = update.message.text.strip()
    # Change log level from INFO to DEBUG
    logger.debug(f"Search prefix detected: '{message_text[:20]}...'")
    
    # Extract query and process search
    query = message_text[7:].strip()  # Remove "!search"
    context.args = query.split()
    await handle_search(update, context)

async def handle_ocr_prefix(update: Update, context: CallbackContext) -> None:
    """
    Handle !ocr prefix for text extraction.
    """
    # Change log level from INFO to DEBUG
    logger.debug(f"OCR prefix detected: '{update.message.text[:20]}...'")
    await handle_trace_command(update.message, update.effective_user, context)

async def handle_roast_prefix(update: Update, context: CallbackContext) -> None:
    """
    Handle !roast prefix for roasting.
    """
    if not update.message or not update.message.text:
        return
        
    message_text = update.message.text.strip()
    # Change log level from INFO to DEBUG
    logger.debug(f"Roast prefix detected: '{message_text[:20]}...'")
    
    # Extract roast args and process
    roast_args = message_text[len(ROAST_PREFIX):].strip()
    context.args = roast_args.split()
    await handle_roast_command(update, context)

async def post_init(app: Application) -> None:
    """Post-initialization setup."""
    # Set default language for the bot
    app.bot_data["language"] = DEFAULT_LANGUAGE
    
    # Log startup information
    logger.info("Bot is starting up")
    
    # Initialize rate limiter
    limiter.allowance = {"global": limiter.rate}
    limiter.last_check = {"global": time.time()}

def create_app() -> Application:
    """Create and configure the bot application instance."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
    
    # Create application with post_init callback
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