"""
Core bot implementation for Alya Bot Telegram.
"""
import os
import logging
import datetime
from typing import Optional

from telegram.ext import (
    Application, ApplicationBuilder, CallbackContext, CommandHandler, 
    MessageHandler, filters
)

from config.settings import (
    BOT_TOKEN, LOG_LEVEL, LOG_FORMAT, PTB_DEFAULTS, 
    FEATURES, MEMORY_EXPIRY_DAYS
)
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from database.memory_manager import MemoryManager
from core.database import DatabaseManager
from core.nlp import NLPEngine
from handlers.conversation import ConversationHandler
from handlers.admin import AdminHandler, register_admin_handlers
from handlers.commands import CommandsHandler, reset_command
from utils.roast import RoastHandler
from database.session import ensure_database_schema
from config.settings import BOT_TOKEN
from database.session import initialize_database

# Configure logging
logger = logging.getLogger(__name__)

async def cleanup_task(context: CallbackContext) -> None:
    """Run database cleanup task.
    
    Args:
        context: The callback context
    """
    try:
        db_manager = context.application.bot_data.get("db_manager")
        if db_manager:
            logger.info("Running scheduled cleanup")
            db_manager.cleanup_old_data()
            logger.info("Cleanup completed")
        else:
            logger.error("Database manager not found in bot_data")
    except Exception as e:
        logger.error(f"Error in scheduled cleanup: {e}")

def configure_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=getattr(logging, LOG_LEVEL)
    )

    # Setup detailed logging for handlers
    telegram_logger = logging.getLogger('telegram')
    telegram_logger.setLevel(logging.ERROR)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    telegram_logger.addHandler(handler)

def initialize_application() -> Optional[Application]:
    """Initialize and configure the bot application.
    
    Returns:
        Application object if successful, None otherwise
    """
    try:
        # Check for valid token
        if not BOT_TOKEN:
            logger.error("No bot token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
            return None
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Initialize database schema first - ensure tables and columns exist
        logger.info("Ensuring database schema is up-to-date...")
        ensure_database_schema()
        
        # Initialize core components
        logger.info("Initializing components...")
        db_manager = DatabaseManager()
        memory_manager = MemoryManager()
        gemini_client = GeminiClient()
        persona_manager = PersonaManager()
        
        # Initialize NLP engine if enabled
        nlp_engine = None
        if FEATURES.get("emotion_detection", False):
            nlp_engine = NLPEngine()
        
        # Initialize application with simplified approach
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Store components in bot_data for access in handlers and jobs
        application.bot_data["db_manager"] = db_manager
        application.bot_data["memory_manager"] = memory_manager
        application.bot_data["gemini_client"] = gemini_client
        application.bot_data["persona_manager"] = persona_manager
        application.bot_data["nlp_engine"] = nlp_engine
        
        # Register handlers
        register_handlers(application, gemini_client, persona_manager, memory_manager, db_manager, nlp_engine)
        
        # Schedule periodic cleanup task using job queue
        setup_scheduled_tasks(application)
        
        return application
        
    except Exception as e:
        logger.critical(f"Fatal error during initialization: {e}", exc_info=True)
        return None

def register_handlers(
    application: Application, 
    gemini_client: GeminiClient,
    persona_manager: PersonaManager,
    memory_manager: MemoryManager,
    db_manager: DatabaseManager,
    nlp_engine: Optional[NLPEngine] = None
) -> None:
    """Register all handlers with the application.
    
    Args:
        application: The application instance
        gemini_client: Gemini client instance
        persona_manager: Persona manager instance
        memory_manager: Memory manager instance
        db_manager: Database manager instance
        nlp_engine: NLP engine instance (optional)
    """
    # Clear all existing handlers to avoid conflicts
    application.handlers.clear()
    
    # Register handlers in CORRECT ORDER OF PRECEDENCE
    # 1. First register standard command handlers
    logger.info("Registering standard command handlers...")
    
    from handlers.commands import register_commands
    register_commands(application)
    
    # 2. Next register regex pattern handlers with EXPLICIT patterns
    logger.info("Registering regex pattern handlers...")
    # Initialize RoastHandler directly and register its handlers
    roast_handler = RoastHandler(gemini_client, persona_manager, db_manager)
    for handler in roast_handler.get_handlers():
        application.add_handler(handler)
        if isinstance(handler, MessageHandler):
            logger.info(f"  - Registered roast handler with filter: {handler.filters}")
    
    # 3. Register conversation handlers
    logger.info("Registering conversation handlers...")
    conversation_handler = ConversationHandler(
        gemini_client, 
        persona_manager, 
        memory_manager,
        nlp_engine
    )
    
    for handler in conversation_handler.get_handlers():
        application.add_handler(handler)
        if isinstance(handler, MessageHandler):
            logger.info(f"  - Registered conversation handler with filter: {handler.filters}")
        
    # 4. Register admin handlers
    logger.info("Registering admin handlers...")
    admin_handler = AdminHandler(db_manager, persona_manager)
    for handler in admin_handler.get_handlers():
        application.add_handler(handler)
        
    # 5. Register deployment admin handlers
    logger.info("Registering deployment handlers...")
    register_admin_handlers(application, db_manager=db_manager, persona_manager=persona_manager)
    
    # 6. Register command handlers for other utility commands
    logger.info("Registering utility command handlers...")
    command_handler = CommandsHandler(application)
    
    # Log all registered handlers
    log_registered_handlers(application)

def log_registered_handlers(application: Application) -> None:
    """Log summary of all registered handlers.
    
    Args:
        application: The application instance
    """
    logger.info("Registered handlers summary:")
    handler_count = 0
    for group_id, handlers in application.handlers.items():
        for handler in handlers:
            handler_count += 1
            if isinstance(handler, MessageHandler):
                logger.info(f"  - Group {group_id}: MessageHandler with filter: {handler.filters}")
            elif isinstance(handler, CommandHandler):
                cmd_str = ', '.join(handler.commands) if isinstance(handler.commands, (list, tuple)) else str(handler.commands)
                logger.info(f"  - Group {group_id}: CommandHandler for commands: {cmd_str}")
            else:
                logger.info(f"  - Group {group_id}: Other handler: {type(handler).__name__}")
    logger.info(f"Total registered handlers: {handler_count}")

def setup_scheduled_tasks(application: Application) -> None:
    """Set up scheduled tasks for the application.
    
    Args:
        application: The application instance
    """
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

def run_bot() -> None:
    """Initialize and run the Alya Bot."""
    try:
        logger.info("Starting Alya Bot")
        
        # Initialize database schema first
        initialize_database()
        
        # Initialize and configure the application
        application = initialize_application()
        if not application:
            logger.error("Failed to initialize application")
            return
        
        # Start the bot
        logger.info("Starting polling...")
        application.run_polling(allowed_updates=["message", "callback_query", "chat_member"])
        
    except KeyboardInterrupt:
        logger.info("Bot stopped manually by KeyboardInterrupt")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
