import random
import logging
import os
import tempfile
import time
from typing import Dict, Any, Optional, Callable, Awaitable, List, Union, TYPE_CHECKING

from telegram import Update, Message
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from config.settings import SAUCENAO_PREFIX, COMMAND_PREFIX
from utils.saucenao import search_with_saucenao
from core.gemini_client import GeminiClient
from utils.formatters import format_response
from database.session import get_db_session
from database.memory_manager import MemoryManager
from core.persona import PersonaManager
from core.database import DatabaseManager
from handlers.response.help import help_response
from handlers.response.start import start_response
from handlers.response.ping import ping_response
from handlers.response.stats import stats_response

logger = logging.getLogger(__name__)

class CommandsHandler:
    """A class to handle all bot commands centrally with proper structure."""
    
    def __init__(self, application) -> None:
        """Initialize the command handler with the application.
        
        Args:
            application: Telegram bot application instance
        """
        self.application = application
        # Ensure handlers are registered at initialization
        self._register_handlers()
        logger.info("Command handlers initialized and registered")
    
    def _register_handlers(self) -> None:
        """Register all command handlers with the application."""
        # Register sauce handlers
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{SAUCENAO_PREFIX}"),
                self.handle_sauce_command
            )
        )
        
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO & filters.CaptionRegex(f".*{SAUCENAO_PREFIX}.*"),
                self.handle_image_auto_sauce
            )
        )
        
        # Additional commands
        self.application.add_handler(CommandHandler("ping", ping_command))
        self.application.add_handler(CommandHandler("stats", stats_command))
        self.application.add_handler(CommandHandler("reset", reset_command))
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        
        # Log all registered commands
        logger.info(f"Registered sauce and utility commands successfully")
            
    async def handle_sauce_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle !sauce command for reverse image search.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        message = update.effective_message
        user = update.effective_user
        
        # Check if replying to a message with photo
        if message.reply_to_message and message.reply_to_message.photo:
            # Get the largest photo size
            photo = message.reply_to_message.photo[-1]
            
            # Send initial response
            status_message = await message.reply_text("🔍 Alya sedang menganalisis gambar...")
            
            try:
                # Download photo to temporary file
                photo_file = await photo.get_file()
                
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    await photo_file.download_to_drive(temp_file.name)
                    temp_path = temp_file.name
                
                # Search using SauceNAO
                await search_with_saucenao(status_message, temp_path)
                
            except Exception as e:
                logger.error(f"Sauce command error: {e}")
                await status_message.edit_text(
                    "❌ Terjadi kesalahan saat mencari sumber gambar. Coba lagi nanti ya~",
                    parse_mode='HTML'
                )
            finally:
                # Clean up temporary file
                try:
                    if 'temp_path' in locals():
                        os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
                    
        else:
            await message.reply_text(
                "❓ <b>Cara pakai:</b>\n\n"
                "Reply ke gambar dengan <code>!sauce</code> untuk mencari sumber gambar anime/manga.\n\n"
                "<i>~Alya akan membantu mencari sumber gambar. Bukan karena peduli sama kamu atau apa~</i> 😳",
                parse_mode='HTML'
            )
    
    async def handle_image_auto_sauce(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Auto-detect images and provide sauce option.
        
        Args:
            update: Telegram update object  
            context: Callback context
        """
        message = update.effective_message
        
        # Only process if message contains sauce prefix in caption or reply
        message_text = message.caption or ""
        
        if SAUCENAO_PREFIX.lower() in message_text.lower():
            # Get the largest photo size
            photo = message.photo[-1]
            
            # Send initial response
            status_message = await message.reply_text("🔍 Mencari sumber gambar...")
            
            try:
                # Download photo to temporary file
                photo_file = await photo.get_file()
                
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    await photo_file.download_to_drive(temp_file.name)
                    temp_path = temp_file.name
                
                # Search using SauceNAO
                await search_with_saucenao(status_message, temp_path)
                
            except Exception as e:
                logger.error(f"Auto sauce error: {e}")
                await status_message.edit_text(
                    "❌ Gagal mencari sumber gambar. Coba lagi nanti~",
                    parse_mode='HTML'
                )
            finally:
                # Clean up temporary file
                try:
                    if 'temp_path' in locals():
                        os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
                    
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple ping command to test if the bot is responsive."""
    start_time = time.time()
    message = await update.message.reply_text("Pinging...")
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to ms
    response = ping_response(latency_ms=latency)
    await message.edit_text(
        format_response(response, username=update.effective_user.first_name),
        parse_mode="HTML"
    )
    
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /start command."""
    user = update.effective_user
    response = start_response(username=user.first_name or "user")
    await update.message.reply_text(
        format_response(response, username=user.first_name),
        parse_mode="HTML"
    )
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /start: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command."""
    user = update.effective_user
    response = help_response()
    formatted_help = response.format(username=user.first_name or "user")
    await update.message.reply_html(formatted_help)
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /help: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /reset command to clear conversation context."""
    user = update.effective_user
    memory_manager = context.bot_data.get("memory_manager")
    db_manager = context.bot_data.get("db_manager")
    if not memory_manager or not db_manager:
        logger.error("Memory manager or database manager not found in bot_data")
        await update.message.reply_text(
            "Maaf, terjadi kesalahan sistem. Tolong coba lagi nanti ya~ 😳",
            parse_mode="MarkdownV2"
        )
        return

    success = memory_manager.reset_conversation_context(user.id)
    if success:
        memory_manager.store_message(
            user_id=user.id,
            message="Conversation context has been reset.",
            is_user=False,
            metadata={"type": "system_notification"}
        )
        # FIX: Use db_manager to get relationship info (raw SQL, column user_id)
        user_data = db_manager.get_user_relationship_info(user.id)
        relationship = user_data.get("relationship", {})
        friendship_level = "stranger"
        if relationship:
            # Use mapped relationship level name if available
            friendship_level = relationship.get("name", "stranger").lower()
            # Fallback to old logic if needed
            if friendship_level not in ["close_friend", "friend", "acquaintance", "stranger"]:
                friendship_level = "stranger"
        if friendship_level == "close_friend":
            response = "Baiklah, aku sudah melupakan percakapan kita sebelumnya~ Tapi tentu saja aku masih ingat siapa kamu! ✨"
        elif friendship_level == "friend":
            response = "Hmph! Jadi kamu ingin memulai dari awal? Baiklah, aku sudah reset percakapan kita! 😳"
        else:
            response = "Percakapan kita sudah direset. A-aku harap kita bisa bicara lebih baik kali ini... b-bukan berarti aku peduli atau apa! 💫"
        # FIX: Remove parse_mode from format_response()
        await update.message.reply_text(format_response(response))
        memory_manager.store_message(
            user_id=user.id,
            message=response,
            is_user=False,
            metadata={"type": "reset_response"}
        )
    else:
        await update.message.reply_text(format_response(
            "Maaf, ada kesalahan saat mereset percakapan kita. Bisa coba lagi nanti? 😳"
        ))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /stats command to show user relationship stats."""
    user = update.effective_user
    db_manager = context.bot_data.get("db_manager")
    if not db_manager:
        logger.error("Database manager not found in bot_data")
        await update.message.reply_text(
            "Maaf, terjadi kesalahan sistem. Coba lagi nanti ya~ 😳",
            parse_mode="HTML"
        )
        return

    # Get complete user stats with relationship info
    stats = db_manager.get_user_relationship_info(user.id)
    
    if not stats or not stats.get("relationship"):
        await update.message.reply_text(
            "Belum ada data hubungan. Coba kirim pesan dulu ke Alya ya~ 😳",
            parse_mode="HTML"
        )
        return

    # Debug log to see what's actually in the stats
    logger.debug(f"Stats data for user {user.id}: {stats}")
    
    # Format response using the stats_response formatter
    response = stats_response(
        name=stats.get('name', user.first_name),
        relationship=stats.get("relationship", {}),
        affection=stats.get("affection", {}),
        stats=stats.get("stats", {})
    )
    
    # Send response with HTML formatting
    await update.message.reply_html(response)

async def set_bot_commands(application) -> None:
    """
    Register bot commands with Telegram so they appear in the menu.
    Should be called once at startup or on /start and /help.
    """
    from telegram import BotCommand

    commands = [
        BotCommand("start", "Mulai percakapan dengan Alya"),
        BotCommand("help", "Lihat semua fitur Alya"),
        BotCommand("ping", "Cek respons bot"),
        BotCommand("stats", "Lihat statistik hubungan kamu dengan Alya"),
        BotCommand("reset", "Reset percakapan dan memulai dari awal"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands registered to Telegram menu successfully")
    except Exception as e:
        logger.error(f"Failed to register bot commands: {e}")

def register_commands(application) -> None:
    """Initialize and register all command handlers."""
    application.add_handler(CommandHandler("start", start_command), group=0)
    application.add_handler(CommandHandler("help", help_command), group=0)
    application.add_handler(CommandHandler("ping", ping_command), group=0)
    application.add_handler(CommandHandler("stats", stats_command), group=0)
    application.add_handler(CommandHandler("reset", reset_command), group=0)
    # Register sauce/image handlers via CommandsHandler class
    CommandsHandler(application)
    logger.info("Command handlers registered successfully")
    # Hapus pemanggilan set_bot_commands di sini, cukup di /start dan /help

