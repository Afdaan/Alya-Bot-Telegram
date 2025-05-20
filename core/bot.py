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
    GROUP_CHAT_REQUIRES_PREFIX,
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
    
    # PERBAIKAN: Handler untuk menangkap commands di grup yang diawali dengan `!`
    # Filter ini akan menangkap pesan teks yang diawali dengan !sauce, !trace, !search
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & 
        (filters.Regex(r'^!sauce\b') | filters.Regex(r'^!trace\b') | filters.Regex(r'^!search\b')),
        handle_text_commands
    ))
    
    # PERBAIKAN: Media handler dengan improved detection untuk caption commands
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.Document.ALL) & 
        filters.Caption(lambda text: text is not None and any(
            text.startswith(prefix) for prefix in [
                "!trace", "!sauce", "!ocr", "/trace", "/sauce", "/ocr"
            ]
        )),
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
    # PERBAIKI: Tambahkan filter untuk private chat atau di grup harus dengan prefix
    if GROUP_CHAT_REQUIRES_PREFIX:
        # Jika kita mewajibkan prefix di grup, gunakan filter yang lebih ketat
        app.add_handler(MessageHandler(
            (filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^!')) & 
            (filters.ChatType.PRIVATE | 
             filters.Regex(r'^!ai\b') | 
             filters.Regex(r'^!alya\b')),
            handle_message
        ))
    else:
        # Kalau tidak wajib prefix, gunakan filter sederhana
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

# New handler for text-based commands with ! prefix
async def handle_text_commands(update: Update, context: CallbackContext) -> None:
    """
    Process text-based commands that start with ! (e.g., !trace, !sauce, !search).
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.message or not update.message.text:
        return
        
    message_text = update.message.text.strip()
    
    # Dispatch based on command
    if message_text.startswith("!search"):
        # Remove prefix and pass to search handler
        query = message_text[7:].strip()  # Remove "!search"
        
        # FIX: Jangan assign ke context.args, gunakan modified update dengan text yang diedit  # FIX: context.args is a list, not a callback function
        # Atau pass query as is ke handler
        
        # Buat temporary context untuk handle_search
        temp_context = context
        # Bikin dict dummy kalau context.args gak ada
        if not hasattr(context, 'args'):
            temp_context.args = query.split()
        else:
            # Cuma override context utk fungsi ini
            context_args = query.split()
            await handle_search_with_args(update, context, context_args)
            return
            
        await handle_search(update, temp_context)
        
    elif message_text.startswith("!trace"):
        # Jangan pakai update.message karena handle_trace_command harapkan Message bukan Update
        await handle_trace_command(update.message, update.effective_user, context)
        
    elif message_text.startswith("!sauce"):
        await handle_sauce_command(update.message, update.effective_user, context)

# Wrapper function for handling search with explicit args
async def handle_search_with_args(update: Update, context: CallbackContext, query_args: list) -> None:
    """
    Handle search command with explicitly provided arguments.
    
    Args:
        update: Telegram update object 
        context: Callback context
        query_args: Search query arguments as list
    """
    # Create modified update with /search command text for handler
    message = update.message
    
    # Get original text and reconstruct it with /search command
    query_text = " ".join(query_args)
    search_text = f"/search {query_text}"
    
    # Create modified message with the search text
    message._text = search_text  # This uses a protected attribute, but works for our purpose
    
    # Call regular search handler
    await handle_search(update, context)

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