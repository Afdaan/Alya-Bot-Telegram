"""
Main entry point for Alya Telegram Bot.

This module sets up the bot, initializes all necessary components,
and starts the bot's event loop.
"""

import logging
import os
import sys
import asyncio
import signal
from typing import Dict, Any, List, Optional

from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, CallbackQueryHandler, AIORateLimiter
)

# Setup basic logging first to catch any early errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_application() -> Optional[Application]:
    """
    Setup bot application with proper error handling.
    
    Returns:
        Configured Application instance or None if setup fails
    """
    try:
        # Import settings (which may raise exceptions for missing env vars)
        from config.settings import TELEGRAM_BOT_TOKEN, LOGGING_CONFIG
        
        # Configure full logging
        from config.logging_config import setup_logging
        setup_logging()
        
        # Initialize database - skip if module not available
        try:
            from database.database import init_database
            init_database()
        except ImportError:
            logger.warning("Database module not available. Skipping initialization.")
        
        # Create application instance with token and rate limiter
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).rate_limiter(
            AIORateLimiter(max_retries=3)
        ).build()
        
        return application
        
    except ValueError as e:
        # Handle missing environment variables
        logger.error(f"Configuration error: {e}")
        logger.error("Please set the required environment variables or create a .env file")
        logger.error("Minimum required: TELEGRAM_BOT_TOKEN, GEMINI_API_KEY")
        return None
        
    except Exception as e:
        # Handle other errors
        logger.error(f"Error during setup: {e}", exc_info=True)
        return None

async def initialize(application: Application) -> Application:
    """
    Initialize and configure the bot application.
    
    Args:
        application: Application instance to configure
        
    Returns:
        Configured Application instance
    """
    # Add command handlers - only import what's available
    try:
        from handlers.command_handlers import start, help_command, reset_command, handle_search
        
        # Add core command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("reset", reset_command))
        application.add_handler(CommandHandler("search", handle_search))
        
        logger.info("Command handlers registered successfully")
    except ImportError as e:
        logger.warning(f"Some command handlers unavailable: {e}")
    
    # CRITICAL FIX: Register prefix handlers from core.bot
    try:
        from core.bot import setup_handlers
        setup_handlers(application)
        logger.info("Prefix handlers registered successfully")
    except ImportError as e:
        logger.error(f"Failed to register prefix handlers: {e}")
    
    # Add message handler if available
    try:
        from handlers.message_handlers import handle_message
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("Message handler registered successfully")
    except ImportError as e:
        logger.warning(f"Message handler unavailable: {e}")
    
    # Add callback query handler if available
    try:
        from handlers.callback_handlers import handle_callback_query
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        logger.info("Callback handler registered successfully")
    except ImportError as e:
        logger.warning(f"Callback handler unavailable: {e}")
    
    # Setup media handlers only if available
    try:
        # Try to import photo handler directly
        from handlers.media_handlers import handle_photo, handle_document
        
        # Add media handlers if available
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        logger.info("Media handlers registered successfully")
    except ImportError:
        logger.warning("Media handlers unavailable, skipping registration")
    
    # Log startup
    logger.info("Bot initialized successfully")
    
    return application

async def main_async() -> None:
    """Asynchronous main function with proper coroutine handling."""
    app = None
    try:
        # Set up the application
        app = setup_application()
        if not app:
            logger.critical("Failed to setup application. Exiting.")
            sys.exit(1)
            
        # Initialize handlers and configuration
        await initialize(app)
        
        # Start polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep the app running until interrupted
        stop_event = asyncio.Event()
        
        # Setup signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(shutdown(app, stop_event))
            )
        
        # Log ready state
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Wait until we need to exit
        await stop_event.wait()
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        # Ensure we attempt shutdown
        if app:
            await shutdown_app(app)
        sys.exit(1)

async def shutdown(app: Application, stop_event: asyncio.Event) -> None:
    """
    Gracefully shutdown the application.
    
    Args:
        app: Application instance to shutdown
        stop_event: Event to signal shutdown completion
    """
    logger.info("Signal received, shutting down...")
    
    # Proper shutdown sequence
    await shutdown_app(app)
    
    # Signal that we're done
    stop_event.set()

async def shutdown_app(app: Application) -> None:
    """
    Safely shutdown application components.
    
    Args:
        app: Application instance to shutdown
    """
    logger.info("Shutting down bot...")
    
    # First, try to stop updater polling
    try:
        # Check if updater is still running
        if app.updater.running:
            logger.info("Stopping updater polling...")
            await app.updater.stop()
            logger.info("Updater polling stopped")
    except Exception as e:
        logger.error(f"Error stopping updater: {e}")
    
    # Then stop the application
    try:
        logger.info("Stopping application...")
        await app.stop()
        logger.info("Application stopped")
    except Exception as e:
        logger.error(f"Error stopping application: {e}")
    
    # Do not call shutdown() as it will try to shut down the updater again,
    # which is already stopped above

def main() -> None:
    """Run the bot with proper asyncio handling."""
    try:
        # Create a new event loop and run the async main
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()