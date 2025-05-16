"""
Command Handlers for Alya Telegram Bot.

This module provides handlers for various slash commands
and special command patterns recognized by the bot.
"""

import logging
import random  # Add missing import for random module
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  # Added missing import for buttons
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
from utils.rate_limiter import limiter
import asyncio
import subprocess
import os
from config.logging_config import log_command  # Add this import
import time
from utils.context_manager import context_manager

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

async def update_command(update: Update, context: CallbackContext) -> None:
    """Update bot from specified git branch."""
    if update.effective_user.id not in DEVELOPER_IDS:
        await update.message.reply_text("Sorry, this command is for developers only! 🚫")
        return
        
    try:
        # Get branch name from command arguments
        args = context.args
        branch = args[0] if args else "main"
        
        # Send initial status
        status_msg = await update.message.reply_text(f"🔄 Updating from branch: {branch}...")
        
        # Check if branch exists
        check_branch = subprocess.run(
            ["git", "fetch", "origin", branch], 
            capture_output=True, 
            text=True
        )
        if check_branch.returncode != 0:
            await status_msg.edit_text(f"❌ Branch '{branch}' not found!")
            return
            
        # Fetch updates
        fetch = subprocess.run(
            ["git", "fetch", "origin", branch],
            capture_output=True,
            text=True
        )
        
        # Reset to origin/branch
        reset = subprocess.run(
            ["git", "reset", "--hard", f"origin/{branch}"],
            capture_output=True,
            text=True
        )
        
        if fetch.returncode != 0 or reset.returncode != 0:
            await status_msg.edit_text("❌ Update failed! Check logs for details.")
            logger.error(f"Git fetch output: {fetch.stderr}")
            logger.error(f"Git reset output: {reset.stderr}")
            return
            
        # Update successful
        await status_msg.edit_text(
            f"✅ Successfully updated to latest {branch}!\n"
            "🔄 Restarting bot...\n\n"
            f"Fetch output:\n{fetch.stdout}\n"
            f"Reset output:\n{reset.stdout}"
        )
        
        # Restart bot
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        logger.error(f"Update error: {e}")
        await update.message.reply_text(f"❌ Error during update: {str(e)}")

# =========================
# Search Command
# =========================

@log_command(logger)
async def handle_search(update: Update, context: CallbackContext) -> None:
    """
    Handle search command with natural language understanding.
    
    Args:
        update: Telegram Update object
        context: CallbackContext for state management
    """
    # Check rate limit
    if not await limiter.acquire_with_feedback(update, context, "search"):
        return

    try:
        # Extract query dari pesan user
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
        
        # Log query untuk debugging
        logger.info(f"Search query: '{query}'")
        
        # Cek apakah user mengirim gambar dengan pencarian
        has_image = False
        image_file = None
        
        # Jika pesan adalah reply ke gambar, ambil gambar tersebut
        if update.message.reply_to_message and update.message.reply_to_message.photo:
            has_image = True
            photo = update.message.reply_to_message.photo[-1]  # Ambil yang paling besar
            image_file = await photo.get_file()
            
            # Deteksi mode untuk pesan dengan gambar
            if "describe" in query.lower() or "analisis" in query.lower() or "jelaskan" in query.lower():
                # Mode 1: Analyze image dengan Gemini Vision
                # Konfirmasi ke user
                await update.message.reply_text(
                    "💡 *Mode Describe* terdeteksi\\! Alya akan menganalisis gambar ini\\.\\.\\.",
                    parse_mode='MarkdownV2'
                )
                
                # Gunakan document_handlers untuk analisis
                from handlers.document_handlers import get_image_hash, process_file
                await process_file(update.message.reply_to_message, update.effective_user, image_file, "jpg")
                return
                
            elif "source" in query.lower() or "sumber" in query.lower() or "sauce" in query.lower():
                # Mode 2: Mencari sumber gambar
                # Konfirmasi ke user
                await update.message.reply_text(
                    "💡 *Mode Source Search* terdeteksi\\! Alya akan mencari sumber gambar ini\\.\\.\\.",
                    parse_mode='MarkdownV2'
                )
                
                # Gunakan SauceNAO API atau Google Lens
                from handlers.document_handlers import handle_sauce_command
                await handle_sauce_command(update.message.reply_to_message, update.effective_user)
                return
                
            else:
                # Default: Konfirmasi mode yang tersedia
                keyboard = [
                    [
                        InlineKeyboardButton("📝 Describe (Analisis Gambar)", callback_data=f"img_describe"),
                        InlineKeyboardButton("🔍 Find Source (Cari Sumber)", callback_data=f"img_source")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"*{update.effective_user.first_name}\\-kun\\~* Alya melihat kamu ingin mencari dengan gambar\\!\n\n"
                    "Silakan pilih mode pencarian yang kamu inginkan:",
                    reply_markup=reply_markup,
                    parse_mode='MarkdownV2'
                )
                return
        
        # Determine if this is a detailed search
        is_detailed = query.startswith("-d ") or query.startswith("--detail ")
        if is_detailed:
            query = query.replace("-d ", "", 1).replace("--detail ", "", 1).strip()
        
        # Send searching indicator message - Variasikan pesan menunggu
        searching_msgs = [
            "🔍 Sedang mencari informasi\\.\\.\\.",
            "🔎 Mencari hasil terbaik untuk kamu\\.\\.\\.", 
            "🧐 Memindai internet untuk informasi\\.\\.\\.",
            "⏳ Mencari data terbaru\\.\\.\\."
        ]
        searching_msg = random.choice(searching_msgs)
        
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
                search_text = f"Error: Format hasil pencarian tidak valid"
                image_results = None
            else:
                search_text, image_results = search_result_tuple
                
        except Exception as search_err:
            logger.error(f"Search execution error: {search_err}")
            search_text = "Error saat melakukan pencarian."
            image_results = None
        
        # Pastikan search_results adalah string
        if not isinstance(search_text, str):
            logger.error(f"Unexpected search results type: {type(search_text)}")
            search_text = "Error: Hasil pencarian tidak valid"
        
        # PERBAIKAN: Use plain text mode for search results instead of markdown
        # This avoids issues with escape sequences showing up in the text
        if image_results and len(image_results) > 0:
            try:
                # Send text results with plain text mode
                await msg.edit_text(
                    search_text,  # No escape needed for plain text
                    parse_mode=None,  # Use plain text mode
                    disable_web_page_preview=True
                )
                
                # Add a divider to indicate image results are coming
                await update.message.reply_text(
                    "📸 Hasil Gambar:",
                    parse_mode=None
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                # Fallback: Send as new message if edit fails
                await update.message.reply_text(
                    search_text,
                    parse_mode=None,
                    disable_web_page_preview=True
                )
            
            # Then send up to 3 images
            for i, img in enumerate(image_results[:3]):
                try:
                    # Escape text for markdown - dengan ESCAPE TOTAL
                    safe_title = escape_telegram_text(img['title'])
                    safe_source = escape_telegram_text(img['source'])
                    
                    caption = f"*{safe_title}*\nSumber: {safe_source}"
                    
                    # IMPROVED IMAGE HANDLING: Use a better approach for image URLs
                    image_sent = False
                    
                    # Try sending image with better error handling and URL validation
                    for url_field in ['url', 'thumbnail', 'image_url', 'source_url']:
                        if not image_sent and url_field in img and img[url_field]:
                            try:
                                url = img[url_field]
                                
                                # Skip URLs that don't start with http(s)
                                if not (url.startswith('http://') or url.startswith('https://')):
                                    continue
                                    
                                # Try sending image
                                await update.message.reply_photo(
                                    url,
                                    caption=caption,
                                    parse_mode='MarkdownV2'
                                )
                                image_sent = True
                                break
                            except Exception as url_error:
                                logger.warning(f"Failed to send image with {url_field}: {str(url_error)}")
                                # Continue to next URL field
                    
                    # If all attempts failed, send just caption with link
                    if not image_sent and 'url' in img:
                        url = img['url']
                        if url.startswith('http://') or url.startswith('https://'):
                            try:
                                # Send text with clickable link
                                link_text = f"{caption}\n\n🔗 [Lihat Gambar]({url})"
                                await update.message.reply_text(
                                    link_text,
                                    parse_mode='MarkdownV2',
                                    disable_web_page_preview=False  # Show preview for this one
                                )
                            except Exception as link_error:
                                logger.error(f"Failed to send link: {str(link_error)}")
                                
                except Exception as e:
                    logger.error(f"Error sending image result: {str(e)}")
        else:
            # No images, just send the text results
            try:
                await msg.edit_text(
                    search_text,
                    parse_mode=None  # Use plain text mode
                )
            except Exception as e:
                # If editing fails (e.g. due to markdown errors), try to send plain text
                logger.error(f"Failed to edit message with results: {e}")
                await msg.edit_text(
                    "Hasil pencarian tidak dapat diformat dengan benar. Berikut hasil mentah:\n\n" + search_text[:3800],
                    parse_mode=None  # No parse mode = plain text
                )
        
        # Simpan context search
        context_data = {
            'command': 'search',
            'timestamp': int(time.time()),
            'query': query,
            'has_image': has_image if 'has_image' in locals() else False,
            'is_detailed': is_detailed if 'is_detailed' in locals() else False,
        }
        
        # Tambahkan result summary jika ada
        if 'search_text' in locals() and search_text:
            # Simpan ringkasan hasil (max 300 char)
            context_data['result_summary'] = search_text[:300] + ('...' if len(search_text) > 300 else '')
            
        # Tambahkan flag image results jika ada
        if 'image_results' in locals() and image_results:
            context_data['has_image_results'] = True
            context_data['image_count'] = len(image_results)
            
        # Save ke database
        context_manager.save_context(
            update.effective_user.id, 
            update.effective_chat.id,
            'search',
            context_data
        )
            
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)  # Log full traceback
        await update.message.reply_text(
            "Oops\\! Ada masalah saat melakukan pencarian\\. Silakan coba lagi nanti\\.",
            parse_mode='MarkdownV2'
        )

def escape_markdown_v2(text):
    """
    Escape all special characters in text for MarkdownV2 format.
    
    Args:
        text: Text to escape
        
    Returns:
        Properly escaped text for MarkdownV2
    """
    if not text:
        return ""
        
    # Daftar karakter yang perlu di-escape untuk MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Escape semua karakter khusus
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text

def escape_telegram_text(text):
    """
    Super-safe function to escape ALL Telegram MarkdownV2 special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Text with all special characters escaped
    """
    if text is None:
        return ""
        
    if not isinstance(text, str):
        text = str(text)
    
    # First escape backslash itself
    text = text.replace('\\', '\\\\')
    
    # Then escape all other special characters
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', 
                       '-', '=', '|', '{', '}', '.', '!']
    
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
        
    return text