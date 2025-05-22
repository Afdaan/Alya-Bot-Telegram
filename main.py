"""
Main entry point for Alya Telegram Bot.

This module initializes the bot, sets up handlers, and starts the bot polling.
"""

import logging
import asyncio
import os
import signal
import sys
from pathlib import Path

from telegram.ext import Application

from core.bot import create_app, run_bot
from core.personas import init_personas
from handlers.command_handlers import register_command_handlers
from handlers.message_handlers import register_message_handlers
from handlers.callback_handlers import register_callback_handlers
from config.logging_config import setup_logging

# Setup logging
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Handle termination signals gracefully."""
    logger.info("Received termination signal. Shutting down...")
    sys.exit(0)

def main():
    """Initialize and run the bot."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize logging
    setup_logging()
    
    try:
        # Initialize personas
        init_personas()
        
        # Create application
        app = create_app()
        
        # Register handlers explicitly
        register_command_handlers(app)
        register_message_handlers(app)
        register_callback_handlers(app)
        
        logger.info("Command handlers registered successfully")
        
        # Run the bot
        app.run_polling()
        
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()