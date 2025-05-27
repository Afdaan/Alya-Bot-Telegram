import random
import logging
import os
import tempfile
import time
from typing import Dict, Any, Optional
from telegram import Update, Message
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from config.settings import SAUCENAO_PREFIX
from utils.saucenao import search_with_saucenao
from core.gemini_client import GeminiClient
from typing import Dict, Any, Optional, Callable, Awaitable, List, Union
from telegram.ext import CommandHandler as TelegramCommandHandler
from telegram.ext import ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class CommandsHandler:
    """A class to handle all bot commands centrally with proper structure."""
    
    def __init__(self, application) -> None:
        """Initialize the command handler with the application.
        
        Args:
            application: Telegram bot application instance
        """
        self.application = application
        # Pastikan handler langsung diregister saat init
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
        self.application.add_handler(CommandHandler("ping", self.ping_command))
        
        # Log all registered commands
        logger.info(f"Registered sauce and utility commands successfully")
        
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Simple ping command to test if the bot is responsive.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        start_time = time.time()
        message = await update.message.reply_text("Pinging...")
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000  # Convert to ms
        
        await message.edit_text(
            f"🏓 Pong! Latency: {latency:.2f}ms\n"
            f"Bot is running and responding."
        )
    
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


def register_commands(application) -> None:
    """Initialize and register all command handlers.
    
    Args:
        application: Telegram bot application instance
    """
    # Create command handler instance which will register all handlers
    CommandsHandler(application)
    logger.info("Command handlers registered successfully")
