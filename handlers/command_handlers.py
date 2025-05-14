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
from utils.formatters import format_markdown_response

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

async def handle_search(update: Update, context: CallbackContext) -> None:
    """
    Handle search command with web search capabilities.
    
    Args:
        update: Telegram Update object
        context: CallbackContext for state management
    """
    try:
        # Perbaikan: pastikan context.args adalah list sebelum join
        if not context.args:
            # Jika pesan langsung dimulai dengan '!search' tanpa spasi, ambil query dari text penuh
            if update.message.text.startswith('!search'):
                # Skip '!search ' prefix (7 karakter) untuk ambil query
                query = update.message.text[7:].strip()
            else:
                query = ""
        else:
            # Jika args ada, join seperti biasa
            query = " ".join(context.args)
        
        # If no query provided, show usage info
        if not query:
            usage_msg = get_response("search_usage", context)
            await update.message.reply_text(
                usage_msg,
                parse_mode='MarkdownV2'
            )
            return
        
        # Log untuk debugging
        logger.info(f"Search query: '{query}'")
        
        # Determine if this is a detailed search
        is_detailed = query.startswith("-d ") or query.startswith("--detail ")
        if is_detailed:
            query = query.replace("-d ", "", 1).replace("--detail ", "", 1).strip()
        
        # Send searching indicator message
        searching_msg = get_response("searching", context)
        msg = await update.message.reply_text(
            searching_msg,
            parse_mode='MarkdownV2'
        )
        
        # Execute search
        try:
            search_result_tuple = await search_engine.search(query, detailed=is_detailed)
            
            # Validasi return value dari search()
            if not isinstance(search_result_tuple, tuple) or len(search_result_tuple) != 2:
                logger.error(f"Invalid search result format: {type(search_result_tuple)}")
                search_results = f"Error: Format hasil pencarian tidak valid"
                image_results = None
            else:
                search_results, image_results = search_result_tuple
                
        except Exception as search_err:
            logger.error(f"Search execution error: {search_err}")
            search_results = "Error saat melakukan pencarian."
            image_results = None
        
        # Pastikan search_results adalah string
        if not isinstance(search_results, str):
            logger.error(f"Unexpected search results type: {type(search_results)}")
            search_results = "Error: Hasil pencarian tidak valid"
        
        # Format search results for Markdown
        safe_results = format_markdown_response(search_results)
        
        # If we have image results, send them
        if image_results and len(image_results) > 0:
            # First send the text results
            await msg.edit_text(
                safe_results,
                parse_mode='MarkdownV2',
                disable_web_page_preview=True
            )
            
            # Then send up to 3 images
            for i, img in enumerate(image_results[:3]):
                try:
                    # Escape text for markdown
                    safe_title = img['title'].replace('.', '\\.').replace('-', '\\-').replace('!', '\\!')
                    safe_source = img['source'].replace('.', '\\.').replace('-', '\\-').replace('!', '\\!')
                    
                    caption = f"*{safe_title}*\nSumber: {safe_source}"
                    
                    # Try with full URL first
                    try:
                        await update.message.reply_photo(
                            img['url'], 
                            caption=caption,
                            parse_mode='MarkdownV2'
                        )
                    except Exception as img_error:
                        # If full URL fails, try thumbnail
                        try:
                            logger.warning(f"Failed to send image, trying thumbnail: {str(img_error)}")
                            if img.get('thumbnail') and img['thumbnail'] != img['url']:
                                await update.message.reply_photo(
                                    img['thumbnail'], 
                                    caption=caption,
                                    parse_mode='MarkdownV2'
                                )
                        except Exception as thumb_error:
                            logger.error(f"Failed to send thumbnail: {str(thumb_error)}")
                            # If both fail, continue to next image
                except Exception as e:
                    logger.error(f"Error sending image result: {str(e)}")
        else:
            # No images, just send the text results
            await msg.edit_text(
                safe_results,
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)  # Log full traceback
        await update.message.reply_text(
            "Oops\\! Ada masalah saat melakukan pencarian\\. Silakan coba lagi nanti\\.",
            parse_mode='MarkdownV2'
        )