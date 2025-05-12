import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from config.settings import CHAT_PREFIX, ANALYZE_PREFIX  # Add ANALYZE_PREFIX import
from core.models import user_chats

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("Chat dengan Alya 💬", callback_data='chat'),
            InlineKeyboardButton("Buat Gambar 🎨", callback_data='image')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        f"*Konnichiwa {user.first_name}\\-san\\!* 🌸\n\n"
        "Alya\\-chan di sini\\~ Aku sangat senang bisa berbicara denganmu tentang shio\\!\n"
        "_Apa yang ingin kamu ketahui hari ini?_\n\n"
        "Pilih mode yang kamu inginkan:"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "*Konnichiwa\\!* 🌸 *Alya\\-chan di sini\\~*\n\n"
        "Ini adalah perintah yang bisa kamu gunakan:\n\n"
        "`/start` \\- Mulai berbicara dengan Alya\\-chan\n"
        "`/help` \\- Bantuan dari Alya\\-chan\n"
        "`/mode` \\- Ubah mode chat atau gambar\n"
        "`/reset` \\- Hapus history chat\n\n"
        "*Mode Chat:* \n"
        "\\- Chat Private: _Langsung kirim pesan ke Alya\\-chan_\n"
        f"\\- Chat Grup: Gunakan `{CHAT_PREFIX}` \n"
        f"Contoh: `{CHAT_PREFIX} Bagaimana shio kuda tahun ini?`\n\n"
        "*Analisis Dokumen/Gambar:*\n"
        f"\\- Kirim dokumen/gambar dengan caption `{ANALYZE_PREFIX}`\n"
        f"Contoh: `{ANALYZE_PREFIX} Tolong analisis gambar ini`\n\n"
        "_Yoroshiku onegaishimasu\\!_ ✨"
    )
    await update.message.reply_text(
        help_text,
        parse_mode='MarkdownV2'
    )

async def mode_command(update: Update, context: CallbackContext) -> None:
    """Change the bot mode."""
    keyboard = [
        [
            InlineKeyboardButton("Chat Mode", callback_data='chat'),
            InlineKeyboardButton("Image Generation", callback_data='image')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Pilih mode yang ingin Anda gunakan:",
        reply_markup=reply_markup
    )

async def reset_command(update: Update, context: CallbackContext) -> None:
    """Reset chat history."""
    user_id = update.effective_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    
    await update.message.reply_text("History chat telah dihapus!")