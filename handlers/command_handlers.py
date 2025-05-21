"""
Command Handlers for Alya Telegram Bot.

This module provides handlers for various slash commands
using semantic intent understanding rather than regex matching.
"""

# Standard library imports
import logging
import random
import sys
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from config.help_text import HELP_TEXT

# Third-party imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes, Application, CommandHandler

# Local imports
from config.settings import (
    CHAT_PREFIX, 
    ANALYZE_PREFIX, 
    SAUCE_PREFIX,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    DEVELOPER_IDS
)
from core.models import user_chats
from core.search_engine import SearchEngine
from utils.language_handler import get_response, get_language
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.natural_parser import extract_command_parts, check_message_intent
from utils.rate_limiter import limiter, rate_limited
from utils.context_manager import context_manager
import asyncio
import subprocess
import time
from config.logging_config import log_command

from utils.fact_extractor import fact_extractor
from core.mood_manager import mood_manager

# Setup logger
logger = logging.getLogger(__name__)

# Initialize search engine
search_engine = SearchEngine()

# Record process start time
process_start_time = time.time()

# =========================
# Basic Commands
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.effective_user:
        return
        
    user = update.effective_user
    username = user.first_name
    
    # Import here to avoid circular imports
    from utils.formatters import format_markdown_response
    from core.personas import persona_manager
    
    # Set default persona for new users
    user_persona = persona_manager.get_current_persona(user.id)
    if not user_persona:
        persona_manager.set_persona(user.id, "tsundere")
    
    # Get welcome message based on persona
    persona = persona_manager.get_current_persona(user.id)
    
    welcome_message = (
        f"*Halo, {username}!*\n\n"
        "Aku Alya, bot Telegram yang bisa mengobrol denganmu dengan kepribadian AI~ ✨\n\n"
        "Kamu bisa:\n"
        "• Mengobrol langsung di chat personal\n"
        "• Di grup, gunakan awalan `!ai` atau mention aku\n"
        "• Ganti kepribadianku dengan `/persona`\n"
        "• Analisis gambar dengan `!trace`\n"
        "• Cari sumber gambar dengan `!sauce`\n\n"
        "Coba ajak aku bicara sekarang!"
    )
    
    # Format with Markdown V2 safety
    safe_message = format_markdown_response(welcome_message, username)
    
    await update.message.reply_text(
        safe_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.effective_user:
        return
        
    user = update.effective_user
    username = user.first_name
    
    # Import here to avoid circular imports
    from utils.formatters import format_markdown_response
    
    # Format with Markdown V2 safety
    safe_message = format_markdown_response(help_text, username)
    
    await update.message.reply_text(
        safe_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )

@log_command(logger)
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /reset command to clear chat history.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.first_name
    
    # Clear in-memory chat history if exists
    if user_id in user_chats:
        user_chats[user_id] = {}
    
    # Clear persistent context
    try:
        context_manager.clear_chat_history(user_id, chat_id)
        await update.message.reply_text(
            f"*{escape_markdown_v2(username)}\\-kun*\\~ Riwayat chat sudah dibersihkan\\! 🧹",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error in reset command: {e}")
        await update.message.reply_text(
            f"Gomenasai\\! Ada error saat membersihkan riwayat chat\\: {escape_markdown_v2(str(e))}",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Simple ping command to check if bot is alive.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    await update.message.reply_text("Pong! ✨")

def format_uptime(seconds: int) -> str:
    """Format seconds into days, hours, minutes, seconds string."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)

# =========================
# Search Command
# =========================

@log_command(logger)
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle search command with semantic understanding.
    
    Args:
        update: Telegram Update object
        context: CallbackContext for state management
    """
    # Check rate limit
    user_id = update.effective_user.id if update.effective_user else None
    
    # Rate limiting - Only pass user_id, not other arguments
    allowed, wait_time = await limiter.acquire_with_feedback(user_id)
    if not allowed:
        wait_msg = f"Tunggu {wait_time:.1f} detik sebelum mencoba lagi."
        await update.message.reply_text(wait_msg, parse_mode=None)
        return

    try:
        # Extract query using more robust method
        message_text = update.message.text.strip()
        
        # PERBAIKAN: Deteksi lebih baik untuk berbagai format perintah search
        if message_text.startswith("!search") or message_text.startswith("/search"):
            prefix = "!search" if message_text.startswith("!search") else "/search"
            query = message_text[len(prefix):].strip()
        else:
            # FIX: Perbaiki cara akses context.args yang benar 
            query = " ".join(context.args) if hasattr(context, 'args') and context.args else ""
        
        # If no query provided, show usage info
        if not query:
            usage_msg = get_response("search_usage", context)
            await update.message.reply_text(
                usage_msg,
                parse_mode='MarkdownV2'
            )
            return
        
        logger.info(f"Search query: '{query}'")
        
        # Check for image search via reply
        has_image = False
        image_file = None
        
        if update.message.reply_to_message and update.message.reply_to_message.photo:
            has_image = True
            photo = update.message.reply_to_message.photo[-1]
            image_file = await photo.get_file()
            
            # Detect intent from query without regex
            query_lower = query.lower()
            
            # Handle image description request
            if any(keyword in query_lower for keyword in ["describe", "analisis", "jelaskan", "what is this"]):
                await update.message.reply_text(
                    "💡 *Mode Describe* terdeteksi\\! Alya akan menganalisis gambar ini\\.\\.\\.",
                    parse_mode='MarkdownV2'
                )
                from handlers.document_handlers import process_file
                await process_file(update.message.reply_to_message, update.effective_user, image_file, "jpg")
                return
            
            # Handle image source search request
            elif any(keyword in query_lower for keyword in ["source", "sumber", "sauce", "origin", "asal"]):
                await update.message.reply_text(
                    "💡 *Mode Source Search* terdeteksi\\! Alya akan mencari sumber gambar ini\\.\\.\\.",
                    parse_mode='MarkdownV2'
                )
                from handlers.document_handlers import handle_sauce_command
                await handle_sauce_command(update.message.reply_to_message, update.effective_user)
                return
            
            else:
                # Default: Show options
                keyboard = [
                    [
                        InlineKeyboardButton("📝 Describe (Analisis Gambar)", callback_data=f"img_describe"),
                        InlineKeyboardButton("🔍 Find Source (Cari Sumber)", callback_data=f"img_source")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"*{escape_markdown_v2(update.effective_user.first_name)}\\-kun\\~* Alya melihat kamu ingin mencari dengan gambar\\!\n\n"
                    "Silakan pilih mode pencarian yang kamu inginkan:",
                    reply_markup=reply_markup,
                    parse_mode='MarkdownV2'
                )
                return
        
        # Determine if detailed search without regex
        is_detailed = query.startswith("-d ") or query.startswith("--detail ")
        if is_detailed:
            query = query.replace("-d ", "", 1).replace("--detail ", "", 1).strip()
        
        # Send searching indicator with randomized message
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
        
        # Execute search with proper error handling
        try:
            search_result_tuple = await search_engine.search(query, detailed=is_detailed)
            
            # Validate return value
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
        
        # Ensure search_results is a string
        if not isinstance(search_text, str):
            logger.error(f"Unexpected search results type: {type(search_text)}")
            search_text = "Error: Hasil pencarian tidak valid"
        
        # Send results with appropriate formatting
        await send_search_results(update, msg, search_text, image_results)
        
        # Save context safely
        try:
            # Store search context
            context_data = {
                'command': 'search',
                'timestamp': int(time.time()),
                'query': query,
                'has_image': bool(has_image),
                'is_detailed': bool(is_detailed),
                'result_summary': str(search_text)[:300] + ('...' if len(search_text) > 300 else ''),
                'has_image_results': bool(image_results),
                'image_count': len(image_results) if image_results else 0
            }
            
            context_manager.save_context(
                update.effective_user.id,
                update.effective_chat.id,
                'search',
                context_data
            )
            logger.debug(f"Search context saved for query: {query}")
        except Exception as e:
            logger.error(f"Error saving search context: {e}")
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        await update.message.reply_text(
            "Oops\\! Ada masalah saat melakukan pencarian\\. Silakan coba lagi nanti\\.",
            parse_mode='MarkdownV2'
        )

async def send_search_results(update: Update, msg, search_text: str, image_results: Optional[List[Dict[str, str]]]):
    """
    Send search results with appropriate formatting.
    
    Args:
        update: Telegram Update object
        msg: Message to edit with results
        search_text: Formatted search results text
        image_results: Optional list of image results
    """
    try:
        # Extract URLs for buttons if they exist
        url_buttons = []
        if "__URLS__" in search_text:
            parts = search_text.split("__URLS__")
            search_text = parts[0]  # Get clean text without URLs marker
            
            # Extract URL data
            if len(parts) > 1:
                url_data = parts[1]
                url_pairs = url_data.split(',')
                for pair in url_pairs:
                    if '|' in pair:
                        try:
                            title, url = pair.split('|', 1)
                            
                            # PERBAIKAN: Validasi URL harus diawali dengan http:// atau https://
                            if url and not url.startswith(('http://', 'https://')):
                                url = 'https://' + url
                                
                            # PERBAIKAN: Sanitasi title agar tidak mengganggu URL
                            title = title.strip()[:15]  # Batasi panjang title
                            url_buttons.append((title, url))
                        except Exception as e:
                            logger.warning(f"Error parsing URL pair '{pair}': {e}")
        
        # Clean and format search text    
        formatted_text = clean_search_text(search_text)
        
        # Create inline keyboard if we have URLs
        reply_markup = None
        if url_buttons:
            keyboard = []
            for i, (title, url) in enumerate(url_buttons, 1):
                try:
                    # PERBAIKAN: Benerin format button - pakai nomer link saja
                    button_text = f"🔗 Link #{i}"
                    keyboard.append([InlineKeyboardButton(button_text, url=url)])
                except Exception as e:
                    logger.warning(f"Error creating button for URL '{url}': {e}")
            
            if keyboard:  # Only create markup if we have valid buttons
                reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit message with formatted text and buttons
        await msg.edit_text(
            formatted_text,
            parse_mode=None,
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        
        # If there are image results, send them in a cleaner format
        if image_results and len(image_results) > 0:
            # Filter valid images and extract useful information
            valid_images = []
            for img in image_results[:3]:  # Limit to 3 images
                # Check if the image has required fields
                image_url = (img.get('url') or img.get('thumbnail') or 
                            img.get('image_url') or img.get('source_url'))
                
                if not image_url:
                    continue
                    
                # PERBAIKAN: Validasi URL
                if not image_url.startswith(('http://', 'https://')):
                    image_url = 'https://' + image_url
                    
                valid_images.append({
                    'title': img.get('title', 'No title')[:50],  # Limit length
                    'source': img.get('source', 'Unknown source')[:30],  # Limit length
                    'url': image_url
                })
            
            # Only proceed if we have valid images
            if valid_images:
                # Create aesthetically pleasing image result message
                image_caption = "<b>📸 HASIL GAMBAR</b>\n\n"
                
                # Format each image info
                for i, img in enumerate(valid_images, 1):
                    image_caption += f"<b>#{i}</b> {img['title']}\n"
                    image_caption += f"<i>Sumber:</i> {img['source']}\n\n"
                
                # Add footer with prettified format
                image_caption += "<i>Klik button di bawah untuk melihat gambar asli</i> 🔍"
                
                # Create a keyboard with image links - improved formatting
                keyboard = []
                for i, img in enumerate(valid_images, 1):
                    # Create clearer button labels
                    button_text = f"🖼️ Lihat Gambar #{i}"
                    keyboard.append([InlineKeyboardButton(button_text, url=img['url'])])
                
                # Add search on Google Images button for better UX
                search_query = update.message.text.replace("!search", "").strip()
                google_images_url = f"https://www.google.com/search?q={search_query}&tbm=isch"
                keyboard.append([InlineKeyboardButton("🔎 Lihat lebih banyak di Google Images", url=google_images_url)])
                
                # Try to send first image with thumbnail
                try:
                    first_img_url = valid_images[0]['url']
                    
                    # Send a single image with info about all images
                    await update.message.reply_photo(
                        photo=first_img_url,
                        caption=image_caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.HTML
                    )
                except Exception as img_error:
                    logger.warning(f"Failed to send image results: {img_error}")
                    # Fallback to just text with links if image sending fails
                    await update.message.reply_text(
                        image_caption + "\n\n<i>Tidak dapat menampilkan preview gambar</i>",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
    except Exception as e:
        logger.error(f"Error sending search results: {e}")
        # Fallback to simple text display
        try:
            await msg.edit_text(
                "Hasil pencarian tidak dapat diformat dengan benar. Berikut hasil mentah:\n\n" + 
                search_text[:3800],
                parse_mode=None
            )
        except Exception as e2:
            logger.error(f"Even fallback failed: {e2}")

def clean_search_text(text: str) -> str:
    """
    Clean and format search result text.
    
    Args:
        text: Raw search result text
    Returns:
        Cleaned and formatted text
    """
    lines = text.splitlines()
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        # Bold the title "Results for..."
        if line.startswith("Results for "):
            cleaned_lines.append(f"🔍 {line}")
            continue
        
        # Use emoji indicators for different types of results
        if any(x in line.lower() for x in ["wikipedia", "wiki"]):
            cleaned_lines.append(f"📄 {line}")
        elif "github" in line.lower():
            cleaned_lines.append(f"💻 {line}")
        elif any(x in line.lower() for x in ["berita", "news", "artikel"]):
            cleaned_lines.append(f"📰 {line}")
        else:
            cleaned_lines.append(line)
    
    # Join and clean up excessive newlines
    result = "\n".join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)  # Replace 3+ newlines with 2
    
    # Ensure a clean header
    if not result.startswith("🔍"):
        result = "🔍 Hasil pencarian:\n\n" + result
        
    return result

# Tambahkan fungsi register_command_handlers yang kurang
def register_command_handlers(app: Application) -> None:
    """
    Register all command handlers.
    
    Args:
        app: Telegram application instance
    """
    # Basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("search", handle_search))
    app.add_handler(CommandHandler("memory", memory_command))
    
    # Additional handlers can be registered here
    
    logger.info("Command handlers registered successfully")

@log_command(logger)
async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory command to show memory stats and facts."""
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    if not user:
        return
        
    try:
        # Get stats
        memory_stats = context_manager.get_memory_stats(user.id)
        
        # Get user facts
        personal_facts = fact_extractor.get_user_facts(user.id)
        facts_text = "\n".join([
            f"• {k}: {v}" for k, v in personal_facts.items()
        ]) if personal_facts else "Belum ada fakta tersimpan"
        
        # Get recent topics
        recent_topics = context_manager.get_recent_topics(user.id, limit=5)
        topics_text = "\n".join([f"• {topic}" for topic in recent_topics]) if recent_topics else "Belum ada topik tercatat"
        
        # Format memory info with Russian expressions for emotional touch
        memory_info = (
            f"*память\\!* _{escape_markdown_v2('Informasi memori untuk')}_ *{escape_markdown_v2(user.first_name)}\\-kun*\n\n"
            f"💭 *Stats:*\n"
            f"• Messages: {memory_stats.get('total_messages', 0)}\n"
            f"• Memory age: {memory_stats.get('memory_age', 'N/A')}\n"
            f"• Usage: {memory_stats.get('memory_usage_percent', 0)}%\n\n"
            f"📝 *Personal Facts:*\n{escape_markdown_v2(facts_text)}\n\n"
            f"🗂 *Recent Topics:*\n{escape_markdown_v2(topics_text)}\n\n"
            f"*хорошо\\!* _{escape_markdown_v2('Ini informasi yang Alya ingat tentangmu~')}_"
        )
        
        await update.message.reply_text(
            memory_info,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    except Exception as e:
        logger.error(f"Error in memory command: {e}")
        await update.message.reply_text(
            f"Maaf {user.first_name}-kun, ada error: {str(e)[:100]}... 😔"
        )

# IMPORTANT: Don't add handlers here - move to setup_handlers() in core/bot.py