import logging
from telegram.ext import (
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler,
    Application
)

from handlers.command_handlers import start, help_command, mode_command, reset_command
from handlers.message_handlers import handle_message
from handlers.document_handlers import handle_document_image
from handlers.callback_handlers import button_callback
from handlers.ping_handlers import ping_command
from handlers.dev_handlers import (
    update_command, stats_command, debug_command, shell_command,
    # Add other dev commands here
)

logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    """Setup all handlers for the bot."""
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Add ping command
    application.add_handler(CommandHandler("ping", ping_command))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message,
        block=False  # Non-blocking for better performance
    ))
    
    # Document and image handlers
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        handle_document_image
    ))
    
    # Developer Commands
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("shell", shell_command))
    # Add other dev command handlers
    
    logger.info("All handlers have been set up successfully")