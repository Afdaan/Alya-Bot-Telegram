"""
Command Handlers for Alya Telegram Bot.

This module provides handlers for various slash commands
and special command patterns recognized by the bot.
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext

from config.settings import (
    CHAT_PREFIX, 
    ANALYZE_PREFIX, 
    SAUCE_PREFIX,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES
)
from core.models import user_chats
from core.search_engine import SearchEngine
from utils.language_handler import get_response

logger = logging.getLogger(__name__)

# Initialize search engine
search_engine = SearchEngine()

# =========================
# Basic Commands
# =========================

async def start(update: Update, context: CallbackContext) -> None:
    """
    Handle /start command to initiate conversation with the bot.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    try:
        # Get localized response
        response = get_response("start", context)
        
        await update.message.reply_text(
            response,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # Fallback to plain text if markdown parsing fails
        await update.message.reply_text(
            f"Konnichiwa! Alya-chan di sini! 🌸",
            parse_mode=None
        )

async def help_command(update: Update, context: CallbackContext) -> None:
    """
    Handle /help command to show available commands.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    # Comprehensive help text with command categories
    help_text = (
        "*Konnichiwa\\!* 🌸 *Alya\\-chan di sini\\~*\n\n"
        "Ini adalah perintah yang bisa kamu gunakan:\n\n"
        "*Basic Commands:*\n"
        "`/start` \\- Mulai berbicara dengan Alya\\-chan\n"
        "`/help` \\- Bantuan dari Alya\\-chan\n"
        "`/reset` \\- Hapus history chat\n"
        "`/ping` \\- Cek status bot\n\n"
        
        "*Chat Commands:*\n"
        "\\- Chat Private: _Langsung kirim pesan ke Alya\\-chan_\n"
        f"\\- Chat Grup: Gunakan `{CHAT_PREFIX}` di awal pesan\n"
        f"Contoh: `{CHAT_PREFIX} Ohayou Alya\\-chan\\~`\n\n"
        
        "*Image/Document Analysis:*\n"
        f"\\- Kirim gambar/dokumen dengan caption `{ANALYZE_PREFIX}`\n"
        f"Contoh: `{ANALYZE_PREFIX} Tolong analisis gambar ini`\n\n"
        
        "*Reverse Image Search:*\n"
        f"\\- Kirim gambar dengan caption `{SAUCE_PREFIX}`\n"
        f"Contoh: `{SAUCE_PREFIX}` untuk mencari sumber gambar anime/artwork\n\n"
        
        "*Smart Search:*\n"
        "\\- Command: `!search <query>`\n"
        "\\- Detail search: `!search -d <query>`\n"
        "\\- Contoh: `!search jadwal KRL lempuyangan jogja`\n"
        "\\- Alya juga bisa langsung menjawab pertanyaan informasi faktual\n"
        f"\\- Contoh: `{CHAT_PREFIX} carikan jadwal kereta dari Bandung ke Jakarta`\n\n"
        
        "*Roasting Mode:*\n"
        "1\\. Roast Biasa:\n"
        f"`{CHAT_PREFIX} roast <username> [keywords]`\n"
        "2\\. Roast GitHub:\n"
        f"`{CHAT_PREFIX} roast github <username>`\n"
        "Contoh: `!ai roast username wibu nolep`\n\n"
        
        "_Prefix Commands:_\n"
        f"`{CHAT_PREFIX}` \\- Untuk chat dengan Alya di grup\n"
        f"`{ANALYZE_PREFIX}` \\- Analisis gambar/dokumen\n"
        f"`{SAUCE_PREFIX}` \\- Cari source gambar\n"
        "`!search` \\- Cari informasi di internet\n"
        f"`{CHAT_PREFIX} roast` \\- Mode toxic queen\n\n"
        
        "_Fitur Smart:_\n"
        "\\- Alya bisa mencari informasi faktual otomatis\n"
        "\\- Tanya tentang jadwal, berita, cuaca, atau informasi lainnya\n"
        "\\- Support pencarian pintar tentang: jadwal kereta, pesawat, bus, dll\n"
        "\\- Akan otomatis mencari di internet dan merangkum hasilnya\n\n"
        
        "_Yoroshiku onegaishimasu\\!_ ✨"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='MarkdownV2'
    )

async def reset_command(update: Update, context: CallbackContext) -> None:
    """
    Handle /reset command to clear chat history.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user_id = update.effective_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    
    await update.message.reply_text(
        get_response("reset", context),
        parse_mode='MarkdownV2'
    )

# =========================
# Search Command
# =========================

async def handle_search(update: Update, context: CallbackContext):
    """
    Handle search requests with web search functionality.
    
    Supports both !search prefix and /search command with
    detailed search option.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    # Extract search query
    if update.message.text and update.message.text.startswith('!search'):
        query = update.message.text.replace('!search', '', 1).strip()
    else:
        # For /search command (if still used)
        query = ' '.join(context.args)
    
    # Show usage if no query provided
    if not query:
        await update.message.reply_text(
            get_response("search_usage", context),
            parse_mode='MarkdownV2'
        )
        return

    # Check if detailed search is requested
    detailed = any(flag in query.lower() for flag in ['-d', '--detail', 'detail'])
    if detailed:
        query = query.replace('-d', '').replace('--detail', '').replace('detail', '').strip()

    # Send searching message
    await update.message.reply_text(
        get_response("searching", context),
        parse_mode='MarkdownV2'
    )
    
    # Perform search and send results
    result = await search_engine.search(query, detailed=detailed)
    await update.message.reply_text(result, parse_mode='HTML')