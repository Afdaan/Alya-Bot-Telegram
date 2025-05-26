"""
Main entry point for Alya Bot.
"""
import os
import logging
import datetime

from telegram.ext import (
    ApplicationBuilder, CallbackContext, CommandHandler, 
    MessageHandler, filters
)

from config.settings import (
    BOT_TOKEN, LOG_LEVEL, LOG_FORMAT, PTB_DEFAULTS, 
    FEATURES, MEMORY_EXPIRY_DAYS
)
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.memory import MemoryManager
from core.database import DatabaseManager
from core.nlp import NLPEngine
from handlers.conversation import ConversationHandler
from handlers.admin import AdminHandler

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL)
)

logger = logging.getLogger(__name__)

async def cleanup_task(context: CallbackContext) -> None:
    """Run database cleanup task.
    
    Args:
        context: The callback context
    """
    try:
        db_manager = context.application.db_manager
        logger.info("Running scheduled cleanup")
        db_manager.cleanup_old_data()
        logger.info("Cleanup completed")
    except Exception as e:
        logger.error(f"Error in scheduled cleanup: {e}")

def main() -> None:
    """Application entry point."""
    try:
        logger.info("Starting Alya Bot")
        
        # Check for valid token
        if not BOT_TOKEN:
            logger.error("No bot token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
            return
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Initialize core components
        logger.info("Initializing components...")
        db_manager = DatabaseManager()
        memory_manager = MemoryManager(db_manager)
        gemini_client = GeminiClient()
        persona_manager = PersonaManager()
        
        # Initialize NLP engine if enabled
        nlp_engine = None
        if FEATURES.get("emotion_detection", False):
            nlp_engine = NLPEngine()
        
        # Initialize application with simplified approach
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Store db_manager for later use in job
        application.db_manager = db_manager
        
        # Create handlers
        conversation_handler = ConversationHandler(
            gemini_client, 
            persona_manager, 
            memory_manager,
            nlp_engine
        )
        
        admin_handler = AdminHandler(db_manager, persona_manager)
        
        # Register handlers
        for handler in conversation_handler.get_handlers():
            application.add_handler(handler)
            
        # Register admin handlers
        for handler in admin_handler.get_handlers():
            application.add_handler(handler)
        
        # Schedule periodic cleanup task using job queue
        job_queue = application.job_queue
        if job_queue:
            # Use timezone-aware datetime (fixed deprecation warning)
            current_time = datetime.time(hour=3, minute=0, second=0)
            
            # Run cleanup job every 24 hours
            job_queue.run_daily(
                callback=cleanup_task,
                time=current_time,
                days=(0, 1, 2, 3, 4, 5, 6)
            )
            logger.info("Scheduled daily cleanup task")
        
        # Start the bot
        logger.info("Starting polling...")
        application.run_polling(allowed_updates=["message", "callback_query", "chat_member"])
        
    except KeyboardInterrupt:
        logger.info("Bot stopped manually by KeyboardInterrupt")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
