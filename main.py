"""
Main entry point for Alya Telegram Bot.
This module sets up logging configuration and launches the bot.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv

# Load .env first before any other imports
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)
from telegram.error import RetryAfter, TimedOut, NetworkError

# Import settings after loading .env
from config.settings import (
    TELEGRAM_BOT_TOKEN,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    DB_VACUUM_INTERVAL_DAYS
)

# Import tambahan untuk context persistence
from utils.context_manager import context_manager

# Import database initialization
from database.database import init_database

# DO NOT directly import document_handlers or trace_handlers here
# Only import the clean interface to avoid circular imports
from handlers.media_interface import process_document_image

# Import db maintenance
from utils.database import run_database_maintenance

# =========================
# Logging Configuration
# =========================

class HTTPFilter(logging.Filter):
    """Filter to remove successful HTTP request logs."""
    def filter(self, record):
        return not (
            'HTTP Request:' in record.getMessage() and 
            'HTTP/1.1 200' in record.getMessage()
        )

def setup_logging():
    """Configure logging with custom filters."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Add filter to root logger
    logging.getLogger().addFilter(HTTPFilter())
    
    # Reduce verbosity for HTTP-related logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Reduce verbosity for other libraries
    logging.getLogger("core.models").setLevel(logging.WARNING)  # Turunin dari INFO ke WARNING
    logging.getLogger("utils.database").setLevel(logging.ERROR)  # Turunin dari WARNING ke ERROR
    logging.getLogger("utils.context_manager").setLevel(logging.ERROR)  # Matiin debug logs
    
    # remove spammy logs from telegram and asyncio
    logging.getLogger("telegram").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# =========================
# Bot Initialization
# =========================

from core.bot import setup_handlers

async def error_handler(update: object, context: CallbackContext) -> None:
    """Handle errors in the dispatcher."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if isinstance(context.error, RetryAfter):
        retry_in = context.error.retry_after
        logger.warning(f"Rate limited by Telegram. Retry after {retry_in} seconds")
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Bot is being rate limited by Telegram. Please try again in {retry_in} seconds."
                )
            except Exception as e:
                logger.error(f"Failed to send rate limit notification: {e}")
    elif isinstance(context.error, TimedOut):
        logger.warning("Request timed out")
    elif isinstance(context.error, NetworkError):
        logger.warning(f"Network error: {context.error}")

# Function for cleaning up expired context entries
async def cleanup_expired_contexts(context: CallbackContext):
    """Clean up expired contexts and history entries from database."""
    logger.info("Running scheduled context cleanup...")
    context_count, history_count = context_manager.cleanup_expired()
    logger.info(f"Cleanup completed: {context_count} contexts and {history_count} history entries removed")

# Function for database maintenance
async def run_db_maintenance(context: CallbackContext):
    """Run scheduled database maintenance tasks."""
    logger.info("Running scheduled database maintenance...")
    
    try:
        # Run maintenance tasks
        results = await asyncio.to_thread(run_database_maintenance)
        
        # Log results
        logger.info(f"Database maintenance completed: {results}")
    except Exception as e:
        logger.error(f"Error during database maintenance: {e}")

def main() -> None:
    """Main function to run the bot."""
    # Load dotenv first before everything else
    load_dotenv()
    
    # Validate configuration
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Telegram token not found. Please check your .env file")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    try:
        init_database()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Create application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Initialize default language
    application.bot_data["language"] = DEFAULT_LANGUAGE
    logger.info(f"Setting default language to {DEFAULT_LANGUAGE} ({SUPPORTED_LANGUAGES.get(DEFAULT_LANGUAGE, 'Unknown')})")
    
    # Setup all handlers
    setup_handlers(application)
    
    # Add global error handler
    application.add_error_handler(error_handler)
    
    # Register callback handler for sauce search via interface
    application.add_handler(CallbackQueryHandler(
        lambda update, context: asyncio.create_task(process_document_image(update, context)),
        pattern='^(sauce_nao)_'
    ))
    
    # Add scheduled job to clean up expired context entries (runs every 12 hours)
    if application.job_queue:
        # Register existing cleanup job
        application.job_queue.run_repeating(cleanup_expired_contexts, interval=43200)
        
        # Add database maintenance job (runs every DB_VACUUM_INTERVAL_DAYS converted to seconds)
        maintenance_interval = DB_VACUUM_INTERVAL_DAYS * 86400  # Days to seconds
        application.job_queue.run_repeating(run_db_maintenance, interval=maintenance_interval)
        logger.info(f"Database maintenance scheduled to run every {DB_VACUUM_INTERVAL_DAYS} days")
    else:
        logger.warning("JobQueue not available. Install python-telegram-bot[job-queue] for scheduled tasks")
        # Run cleanup once at startup
        asyncio.create_task(cleanup_expired_contexts(None))
    
    # Start bot
    logger.info("Starting Alya Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# =========================
# Entry Point
# =========================

if __name__ == '__main__':
    main()