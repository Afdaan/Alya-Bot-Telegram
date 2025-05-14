"""
Main entry point for Alya Telegram Bot.
This module sets up logging configuration and launches the bot.
"""

import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CallbackContext  # Added CallbackContext import
from telegram.error import RetryAfter, TimedOut, NetworkError

# =========================
# Environment & Config Setup
# =========================

# Load environment variables first
load_dotenv()

# Import settings after environment variables are loaded
from config.settings import TELEGRAM_TOKEN, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

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

def main() -> None:
    """Main function to run the bot."""
    # Validate configuration
    if not TELEGRAM_TOKEN:
        logger.error("Telegram token not found. Please check your .env file")
        return
        
    # Create application instance
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Initialize default language
    application.bot_data["language"] = DEFAULT_LANGUAGE
    logger.info(f"Setting default language to {DEFAULT_LANGUAGE} ({SUPPORTED_LANGUAGES.get(DEFAULT_LANGUAGE, 'Unknown')})")
    
    # Setup all handlers
    setup_handlers(application)
    
    # Add global error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Starting Alya Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# =========================
# Entry Point
# =========================

if __name__ == '__main__':
    main()