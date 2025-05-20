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
    set_language_command, db_stats_command, rotate_db_command
)
from handlers.trace_handlers import handle_trace_request

logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    """
    Setup all handlers for the bot with proper priority.
    
    This function organizes handlers in priority order:
    1. Core command handlers (start, help, etc.)
    2. Special message handlers (search, trace)
    3. Callback handlers (buttons)
    4. General message handlers
    5. Media handlers
    6. Admin/developer commands
    
    Args:
        application: The Telegram Application instance
    """
    # =========================
    # Basic Command Handlers
    # =========================
    basic_commands = [
        ("start", start),
        ("help", help_command),
        ("reset", reset_command),
        ("ping", ping_command),
        ("lang", set_language_command)
    ]
    
    for command, handler in basic_commands:
        application.add_handler(CommandHandler(command, handler))
        logger.debug(f"Registered command handler: /{command}")
    
    # =========================
    # Special Message Handlers (Higher Priority)
    # =========================
    
    # Search handler for messages starting with !search
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^!search'), 
        handle_search,
        block=False
    ))
    
    # Trace handler for messages starting with !trace
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^!trace'),
        handle_trace_request,
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
    admin_commands = [
        ("update", update_command),
        ("stats", stats_command),
        ("debug", debug_command),
        ("shell", shell_command),
        ("dbstats", db_stats_command),
        ("rotatedb", rotate_db_command)
    ]
    
    for command, handler in admin_commands:
        application.add_handler(CommandHandler(command, handler))
        logger.debug(f"Registered admin command handler: /{command}")
    
    logger.info("All handlers have been set up successfully")