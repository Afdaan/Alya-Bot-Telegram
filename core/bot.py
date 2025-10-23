"""
Core bot implementation for Alya Bot Telegram.
"""
import os
import logging
import datetime
from typing import Optional

from telegram.ext import (
    Application, ApplicationBuilder, CallbackContext, CommandHandler, 
    MessageHandler
)

from config.settings import (
    BOT_TOKEN, LOG_LEVEL, LOG_FORMAT, FEATURES
)
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.memory import MemoryManager
from database.database_manager import db_manager, DatabaseManager
from core.nlp import NLPEngine
from handlers.conversation import ConversationHandler
from handlers.admin import AdminHandler, register_admin_handlers
from handlers.commands import CommandsHandler, register_commands, set_bot_commands
from utils.roast import RoastHandler
from database.session import ensure_database_schema
from database.session import initialize_database

logger = logging.getLogger(__name__)

async def cleanup_task(context: CallbackContext) -> None:
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
    logging.basicConfig(
        format=LOG_FORMAT,
        level=getattr(logging, LOG_LEVEL)
    )
    telegram_logger = logging.getLogger('telegram')
    telegram_logger.setLevel(logging.ERROR)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    telegram_logger.addHandler(handler)

async def post_init(application: Application) -> None:
    try:
        await set_bot_commands(application)
        logger.info("Registered commands to Telegram menu")
    except Exception as e:
        logger.error(f"Failed to register bot commands: {e}")

def initialize_application() -> Optional[Application]:
    try:
        if not BOT_TOKEN:
            logger.error("No bot token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
            return None
        os.makedirs("data", exist_ok=True)
        logger.info("Ensuring database schema is up-to-date...")
        ensure_database_schema()
        logger.info("Initializing components...")
        # Use global db_manager instance instead of creating new one
        memory_manager = MemoryManager(db_manager)
        gemini_client = GeminiClient()
        persona_manager = PersonaManager()
        nlp_engine = None
        if FEATURES.get("emotion_detection", False):
            nlp_engine = NLPEngine()
        application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
        application.bot_data["db_manager"] = db_manager
        application.bot_data["memory_manager"] = memory_manager
        application.bot_data["gemini_client"] = gemini_client
        application.bot_data["persona_manager"] = persona_manager
        application.bot_data["nlp_engine"] = nlp_engine
        
        # Pass clients to the application object so handlers can access them
        application.gemini_client = gemini_client
        application.persona_manager = persona_manager
        
        gemini_client.set_persona_manager(persona_manager)

        register_handlers(application, gemini_client, persona_manager, memory_manager, db_manager, nlp_engine)
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
    application.handlers.clear()
    
    # Register commands first (higher priority)
    logger.info("Registering standard command handlers...")
    register_commands(application)
    
    # ============================================================================
    # HANDLER REGISTRATION ORDER (Critical for proper routing)
    # ============================================================================
    # Order matters: First matching handler wins!
    # Priority: Specific handlers > General handlers
    # 
    # 1. ConversationHandler (highest priority)
    #    - Handles: !ai prefix, replies to bot, mentions
    #    - Filter: ~filters.Regex(r"^!(?!ai)") blocks other ! commands
    # 
    # 2. CommandsHandler (medium priority)
    #    - Handles: !ask, !sauce, and other utility commands
    # 
    # 3. RoastHandler, AdminHandler (lower priority)
    #    - Handles: !roast, !gitroast, admin commands
    # ============================================================================
    
    logger.info("=" * 60)
    logger.info("REGISTERING HANDLERS (Priority Order)")
    logger.info("=" * 60)
    
    # PRIORITY 1: Conversation Handler (Most specific - !ai, replies, mentions)
    logger.info("[1/4] Registering ConversationHandler (Priority: HIGHEST)")
    conversation_handler = ConversationHandler(
        gemini_client, 
        persona_manager, 
        memory_manager,
        nlp_engine
    )
    for handler in conversation_handler.get_handlers():
        application.add_handler(handler)
        if isinstance(handler, MessageHandler):
            logger.info(f"  ✓ Conversation handler: {handler.filters}")
    
    # PRIORITY 2: Utility Commands (!ask, !sauce, search, etc.)
    logger.info("[2/4] Registering CommandsHandler (Priority: HIGH)")
    CommandsHandler(application)
    
    # PRIORITY 3: Roast Handler (!roast, !gitroast)
    logger.info("[3/4] Registering RoastHandler (Priority: MEDIUM)")
    roast_handler = RoastHandler(gemini_client, persona_manager, db_manager)
    for handler in roast_handler.get_handlers():
        application.add_handler(handler)
        if isinstance(handler, MessageHandler):
            logger.info(f"  ✓ Roast handler: {handler.filters}")
    
    # PRIORITY 4: Admin & System Commands
    logger.info("[4/4] Registering Admin & System Handlers (Priority: LOW)")
    admin_handler = AdminHandler(db_manager, persona_manager)
    for handler in admin_handler.get_handlers():
        application.add_handler(handler)
    
    register_admin_handlers(application, db_manager=db_manager, persona_manager=persona_manager)
    
    logger.info("=" * 60)
    
    log_registered_handlers(application)

def log_registered_handlers(application: Application) -> None:
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
    job_queue = application.job_queue
    if job_queue:
        current_time = datetime.time(hour=3, minute=0, second=0)
        job_queue.run_daily(
            callback=cleanup_task,
            time=current_time,
            days=(0, 1, 2, 3, 4, 5, 6)
        )
        logger.info("Scheduled daily cleanup task")

def run_bot() -> None:
    try:
        logger.info("Starting Alya Bot")
        initialize_database()
        application = initialize_application()
        if not application:
            logger.error("Failed to initialize application")
            return
        logger.info("Starting polling...")
        application.run_polling(allowed_updates=["message", "callback_query", "chat_member"])
    except KeyboardInterrupt:
        logger.info("Bot stopped manually by KeyboardInterrupt")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
