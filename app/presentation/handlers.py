"""
Telegram bot handlers for presentation layer.
"""
import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters

from ..core.conversation import ConversationUseCase
from config.settings import settings

logger = logging.getLogger(__name__)


class TelegramHandlers:
    """Telegram bot handlers."""
    
    def __init__(self, conversation_use_case: ConversationUseCase):
        self.conversation_use_case = conversation_use_case
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        if not user:
            return
        
        welcome_message = """
🌸 **Привет! Aku Alya!** 🌸

Halo~ Aku Alya, gadis yang... eh, b-bukan berarti aku senang kamu datang atau apa! 😤

**Cara menggunakan:**
- Ketik `{prefix} [pesan]` untuk berbicara denganku
- Atau reply pesan ini langsung!

Jangan pikir aku akan selalu ramah ya... дурак! 💫

*Tapi... selamat datang~ ✨*
        """.format(prefix=settings.command_prefix)
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = f"""
**🌸 Alya Bot Commands 🌸**

**Basic Commands:**
• `/start` - Mulai percakapan dengan Alya
• `/help` - Tampilkan bantuan ini
• `/stats` - Lihat statistik percakapan
• `/language` - Ganti bahasa (ID/EN)

**Chat dengan Alya:**
• `{settings.command_prefix} [pesan]` - Chat dengan Alya
• Reply pesan Alya langsung di grup

**Contoh:**
• `{settings.command_prefix} Halo Alya!`
• `{settings.command_prefix} Apa kabar?`

Jangan lupa, aku tsundere... jadi kadang aku dingin tapi sebenernya peduli kok! 😊
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command."""
        # This would need to be implemented with user repository
        stats_message = """
**📊 Statistik Percakapan 📊**

• Level Hubungan: Stranger
• Poin Affection: 0
• Total Interaksi: 0
• Bahasa: Indonesia

*Mulai chat denganku untuk meningkatkan level hubungan kita!* ✨
        """
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def conversation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle conversation messages."""
        user = update.effective_user
        message = update.message
        
        if not user or not message or not message.text:
            return
        
        try:
            # Extract message text
            text = message.text.strip()
            
            # Remove command prefix if present
            if text.startswith(settings.command_prefix):
                text = text[len(settings.command_prefix):].strip()
            
            if not text:
                await self._send_help_message(update)
                return
            
            # Show typing action
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            
            # Prepare user data
            user_data = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code or "id"
            }
            
            # Process message
            response = await self.conversation_use_case.process_message(
                user_id=user.id,
                text=text,
                telegram_user_data=user_data
            )
            
            # Send response
            await message.reply_text(
                response.content,
                parse_mode='Markdown' if self._has_markdown(response.content) else None
            )
            
        except Exception as e:
            logger.error(f"Error in conversation handler: {e}")
            await self._send_error_message(update)
    
    async def _send_help_message(self, update: Update) -> None:
        """Send help message when empty command is used."""
        help_text = f"""
Eh? Mau ngomong apa? 😅

Contoh: `{settings.command_prefix} Halo Alya!`

Atau ketik `/help` untuk bantuan lengkap!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _send_error_message(self, update: Update) -> None:
        """Send error message."""
        error_text = """
Eh... что?! Ada yang error nih... 😳

B-bukan salahku ya! Sistemnya lagi bermasalah... дурак teknologi! 💫

Coba lagi nanti ya~
        """
        await update.message.reply_text(error_text)
    
    def _has_markdown(self, text: str) -> bool:
        """Check if text contains markdown formatting."""
        markdown_chars = ['*', '_', '`', '[']
        return any(char in text for char in markdown_chars)
    
    def get_handlers(self):
        """Get list of handlers for the bot."""
        return [
            # Command handlers
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("stats", self.stats_command),
            
            # Conversation handlers
            MessageHandler(
                filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
                self.conversation_handler
            ),
            MessageHandler(
                filters.TEXT & filters.ChatType.GROUPS & (
                    filters.Regex(f"^{settings.command_prefix}") | filters.REPLY
                ),
                self.conversation_handler
            ),
        ]
