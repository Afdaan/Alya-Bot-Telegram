"""
Callback Handlers for Alya Telegram Bot.

This module handles various button callbacks and interactive elements,
including reverse image search, menu navigation, and user preferences.
"""

import logging
import asyncio
import os
import tempfile
import time  # Add missing import
from typing import Optional, Dict, Any, Tuple, List  # Add missing import

from telegram import Update, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.error import BadRequest

from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.context_manager import context_manager
from utils.image_utils import analyze_image  # Use image_utils instead
from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

# =========================
# Button Callback Handler
# =========================

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """
    Process button callback queries from inline keyboards.
    
    Routes callbacks to appropriate handlers based on callback data prefix
    rather than using regex pattern matching.
    
    Args:
        update: Telegram update object
        context: CallbackContext
    """
    query = update.callback_query
    
    # Early return if no callback data
    if not query or not query.data:
        logger.warning("Received callback without data")
        return
        
    callback_data = query.data
    user = update.effective_user
    
    try:
        # Always answer the callback query first to clear loading state
        await query.answer()
        
        # Parse callback data
        callback_parts = callback_data.split('_', 1)
        callback_type = callback_parts[0]
        callback_args = callback_parts[1] if len(callback_parts) > 1 else None
        
        # Route to appropriate handler based on prefix
        if callback_type == "img":
            await handle_image_mode_callback(query, user, callback_args)
        elif callback_type == "sauce":
            await handle_source_search_callback(query, user, callback_args)
        elif callback_type == "lang":
            await handle_language_callback(query, context, callback_args)
        elif callback_type == "search":
            await handle_search_callback(query, user, callback_args)
        elif callback_type == "page":
            await handle_pagination_callback(query, context, callback_args)
        elif callback_type == "persona":
            # Import persona handler
            from handlers.persona_handlers import handle_persona_callback
            await handle_persona_callback(query, context, callback_args)
        else:
            # Unknown callback type
            logger.warning(f"Unknown callback type: {callback_type}")
            try:
                await query.edit_message_text(
                    f"Gomennasai\\! Alya\\-chan tidak mengerti callback ini\\: `{escape_markdown_v2(callback_data)}`",
                    parse_mode='MarkdownV2'
                )
            except BadRequest as e:
                # Ignore "message is not modified" errors
                if "message is not modified" not in str(e):
                    raise
                    
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        try:
            # Generic error message for all callback errors
            await query.edit_message_text(
                "Gomen ne\\~ Ada error saat memproses perintah\\. \\. \\. 🥺",
                parse_mode='MarkdownV2'
            )
        except BadRequest as e:
            # If message can't be modified, send a new message
            if "message is not modified" in str(e):
                await query.message.reply_text(
                    "Gomen ne\\~ Ada error saat memproses perintah\\. \\. \\. 🥺",
                    parse_mode='MarkdownV2'
                )
            else:
                raise

# =========================
# Image Mode Callbacks
# =========================

async def handle_image_mode_callback(query, user, mode: str) -> None:
    """
    Handle image search mode selection callbacks.
    
    Args:
        query: CallbackQuery object
        user: User who triggered the callback
        mode: Selected image search mode
    """
    message = query.message
    
    # Get original message (the one being replied to)
    original_msg = message.reply_to_message
    if not original_msg or not original_msg.photo:
        await handle_missing_image_error(query, message)
        return
    
    # Get largest photo (best quality)
    photo = original_msg.photo[-1]
    
    # Process based on selected mode
    if mode == "describe":
        # Confirm processing
        await edit_or_reply(query, message, 
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Alya sedang menganalisis gambar ini\\.\\.\\. 🔎",
            parse_mode='MarkdownV2'
        )
        
        # Process image
        try:
            photo_file = await photo.get_file()
            from handlers.document_handlers import process_file
            await process_file(original_msg, user, photo_file, "jpg")
        except Exception as e:
            logger.error(f"Error in image describe callback: {e}")
            await edit_or_reply(query, message,
                f"Gomen ne\\~ Ada error saat menganalisis gambar\\. \\. \\. 🥺\n\n"
                f"Error: {escape_markdown_v2(str(e)[:100])}",
                parse_mode='MarkdownV2'
            )
            
    elif mode == "source":
        # Handle source search
        from handlers.document_handlers import handle_sauce_command
        await handle_sauce_command(original_msg, user)
        
    elif mode == "ocr":
        # Handle OCR (text extraction) using Gemini instead of OCR-specific module
        await edit_or_reply(query, message, 
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Alya sedang mengekstrak teks dari gambar\\.\\.\\. 🔎",
            parse_mode='MarkdownV2'
        )
        
        try:
            # Download image
            photo_file = await photo.get_file()
            temp_path = None
            
            try:
                # Create temp file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                os.close(temp_fd)
                
                # Download image
                await photo_file.download_to_drive(temp_path)
                
                # Use analyze_image from document_handlers with OCR-focused prompt
                from handlers.document_handlers import analyze_with_gemini
                
                ocr_prompt = """
                Extract and return ONLY the text visible in this image.
                Format the text exactly as it appears.
                Preserve line breaks and paragraph structure.
                If there is no text visible, simply respond with "No text detected in this image."
                DO NOT include any analysis or description of the image itself.
                """
                
                # Extract text using Gemini
                extracted_text = await analyze_with_gemini(temp_path, ocr_prompt)
                
                # Check if text was found
                if not extracted_text or "No text detected" in extracted_text:
                    await edit_or_reply(query, message,
                        f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Alya tidak menemukan teks dalam gambar ini\\. 🤔",
                        parse_mode='MarkdownV2'
                    )
                else:
                    # Format extracted text
                    response = (
                        f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Alya menemukan teks berikut dalam gambar\\:\n\n"
                        f"```\n{escape_markdown_v2(extracted_text)}\n```"
                    )
                    
                    # Handle long text
                    if len(response) > 4000:
                        response = response[:3950] + "\n\n_Text too long\\, truncated\\._"
                    
                    await edit_or_reply(query, message, response, parse_mode='MarkdownV2')
                    
            finally:
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        logger.error(f"Failed to remove temp file: {e}")
                        
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            await edit_or_reply(query, message,
                f"Gomen ne\\~ Ada error saat mengekstrak teks\\. \\. \\. 🥺\n\n"
                f"Error: {escape_markdown_v2(str(e)[:100])}",
                parse_mode='MarkdownV2'
            )
    else:
        # Unknown mode
        logger.warning(f"Unknown image mode: {mode}")
        await edit_or_reply(query, message,
            f"Gomennasai\\! Alya tidak mengenali mode gambar: `{escape_markdown_v2(mode)}`",
            parse_mode='MarkdownV2'
        )

async def handle_missing_image_error(query, message) -> None:
    """
    Handle error when image is missing for processing.
    
    Args:
        query: CallbackQuery object
        message: Message object
    """
    await edit_or_reply(query, message,
        "Gomennasai\\! Alya tidak dapat menemukan gambar untuk diproses\\. \\. \\. 🥺",
        parse_mode='MarkdownV2'
    )

# =========================
# Source Search Callbacks
# =========================

async def handle_source_search_callback(query, user, search_type: str) -> None:
    """
    Process reverse image search callbacks.
    
    Args:
        query: CallbackQuery object
        user: User who triggered the callback
        search_type: Type of source search 
    """
    message = query.message
    original_msg = message.reply_to_message
    
    # Check if image exists
    if not original_msg or not original_msg.photo:
        await handle_missing_image_error(query, message)
        return
    
    # Get largest photo
    photo = original_msg.photo[-1]
    
    # Show search status
    await edit_or_reply(query, message,
        f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Alya sedang mencari sumber gambarnya\\.\\.\\. 🔍",
        parse_mode='MarkdownV2'
    )
    
    # Process search based on type
    try:
        file = await photo.get_file()
        
        if search_type == "anime":
            # Handle anime source search
            from utils.saucenao import search_with_saucenao
            
            # Download image
            temp_path = None
            
            try:
                # Create temp file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                os.close(temp_fd)
                
                # Download image
                await file.download_to_drive(temp_path)
                
                # Search with SauceNAO
                await search_with_saucenao(message, temp_path)
                
            finally:
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        logger.error(f"Failed to remove temp file: {e}")
                        
        elif search_type == "lens":
            # Generate Google Lens URL
            google_lens_url = f"https://lens.google.com/uploadbyurl?url={file.file_path}"
            
            await edit_or_reply(query, message,
                f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Kamu bisa mencari dengan Google Lens\\:\n\n"
                f"[🔎 Buka di Google Lens]({escape_markdown_v2(google_lens_url)})",
                parse_mode='MarkdownV2',
                disable_web_page_preview=True
            )
            
        else:
            # Unknown search type
            logger.warning(f"Unknown source search type: {search_type}")
            await edit_or_reply(query, message,
                f"Gomennasai\\! Alya tidak mengenali tipe pencarian: `{escape_markdown_v2(search_type)}`",
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error in sauce callback: {e}")
        await edit_or_reply(query, message,
            f"Gomen ne\\~ Ada error saat mencari sumber gambar\\. \\. \\. 🥺\n\n"
            f"Error: {escape_markdown_v2(str(e)[:100])}",
            parse_mode='MarkdownV2'
        )

# =========================
# Language Callbacks
# =========================

async def handle_language_callback(query, context: CallbackContext, lang_code: str) -> None:
    """
    Process language selection callbacks.
    
    Args:
        query: CallbackQuery object
        context: CallbackContext for state storage
        lang_code: Selected language code
    """
    message = query.message
    user = query.from_user
    
    # Validate language code
    if lang_code not in SUPPORTED_LANGUAGES:
        await edit_or_reply(query, message,
            f"Gomennasai\\! Alya tidak mendukung bahasa dengan kode: `{escape_markdown_v2(lang_code)}`",
            parse_mode='MarkdownV2'
        )
        return
    
    # Update user language preference
    user_id = user.id
    
    # Store in context manager
    language_context = {
        'timestamp': int(time.time()),
        'language': lang_code,
        'set_by_user_id': user_id,
        'set_by_username': user.username or user.first_name,
    }
    
    try:
        context_manager.save_context(user_id, message.chat_id, 'language', language_context)
        logger.info(f"User {user_id} set language to {lang_code}")
        
        # Update message to confirm change
        language_name = SUPPORTED_LANGUAGES[lang_code]
        await edit_or_reply(query, message,
            f"*Bahasa berhasil diubah\\!* ✅\n\n"
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Alya akan menggunakan bahasa "
            f"{escape_markdown_v2(language_name)} \\({escape_markdown_v2(lang_code)}\\) sekarang\\.",
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error setting language: {e}")
        await edit_or_reply(query, message,
            "Gomen ne\\~ Ada error saat mengubah bahasa\\. \\. \\. 🥺",
            parse_mode='MarkdownV2'
        )

# =========================
# Search Callbacks
# =========================

async def handle_search_callback(query, user, search_type: str) -> None:
    """
    Handle search-related callbacks.
    
    Args:
        query: CallbackQuery object
        user: User who triggered the callback
        search_type: Type of search action
    """
    message = query.message
    
    if search_type == "web":
        # Show web search interface
        keyboard = [
            [
                InlineKeyboardButton("🔍 Regular Search", callback_data="search_regular"),
                InlineKeyboardButton("🔎 Detail Search", callback_data="search_detail")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await edit_or_reply(query, message,
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Pilih jenis pencarian yang kamu inginkan\\:",
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
    elif search_type in ["regular", "detail"]:
        # Provide search instructions
        is_detailed = search_type == "detail"
        detail_flag = "-d " if is_detailed else ""
        await edit_or_reply(query, message,
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Gunakan format berikut untuk pencarian\\:\n\n"
            f"`!search {detail_flag}<kata kunci>`\n\n"
            f"Contoh: `!search {detail_flag}jadwal kereta api bandung jakarta`",
            parse_mode='MarkdownV2'
        )
    else:
        # Unknown search type
        logger.warning(f"Unknown search type: {search_type}")
        await edit_or_reply(query, message,
            f"Gomennasai\\! Alya tidak mengenali tipe pencarian: `{escape_markdown_v2(search_type)}`",
            parse_mode='MarkdownV2'
        )

# =========================
# Pagination Callbacks
# =========================

async def handle_pagination_callback(query, context: CallbackContext, page_data: str) -> None:
    """
    Handle pagination for search results or other paginated content.
    
    Args:
        query: CallbackQuery object
        context: CallbackContext for state storage
        page_data: Page data in format "type:id:page"
    """
    message = query.message
    user = query.from_user
    
    try:
        # Parse page data
        page_parts = page_data.split(':')
        if len(page_parts) < 3:
            logger.warning(f"Invalid page data: {page_data}")
            await edit_or_reply(query, message,
                "Gomennasai\\! Data halaman tidak valid\\.",
                parse_mode='MarkdownV2'
            )
            return
            
        content_type = page_parts[0]
        content_id = page_parts[1]
        page_num = int(page_parts[2])
        
        # Handle based on content type
        if content_type == "search":
            # Get search results from context
            search_context = context_manager.get_context(user.id, message.chat_id, 'search')
            if not search_context:
                await edit_or_reply(query, message,
                    "Gomennasai\\! Alya tidak menemukan hasil pencarian sebelumnya\\.",
                    parse_mode='MarkdownV2'
                )
                return
                
            # Get results and paginate
            results = search_context.get('results', [])
            max_page = (len(results) - 1) // 5 + 1
            page_num = max(1, min(page_num, max_page))
            
            # Display results for this page
            start_idx = (page_num - 1) * 5
            end_idx = min(start_idx + 5, len(results))
            page_results = results[start_idx:end_idx]
            
            # Format results
            results_text = f"*Hasil Pencarian (Halaman {page_num}/{max_page})*\n\n"
            
            for idx, result in enumerate(page_results, start=start_idx+1):
                title = escape_markdown_v2(result.get('title', 'No title'))
                snippet = escape_markdown_v2(result.get('snippet', 'No description'))
                link = escape_markdown_v2(result.get('link', '#'))
                
                results_text += (
                    f"{idx}\\. *{title}*\n"
                    f"_{snippet}_\n"
                    f"[🔗 Link]({link})\n\n"
                )
            
            # Create pagination buttons
            keyboard = []
            nav_buttons = []
            
            if page_num > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page:search:{content_id}:{page_num-1}"))
                
            if page_num < max_page:
                nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page:search:{content_id}:{page_num+1}"))
                
            if nav_buttons:
                keyboard.append(nav_buttons)
                
            markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # Update message
            await edit_or_reply(query, message, results_text, 
                                reply_markup=markup, 
                                parse_mode='MarkdownV2')
            
        else:
            # Unknown pagination type
            logger.warning(f"Unknown pagination content type: {content_type}")
            await edit_or_reply(query, message,
                f"Gomennasai\\! Alya tidak mengenali tipe konten: `{escape_markdown_v2(content_type)}`",
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error in pagination: {e}")
        await edit_or_reply(query, message,
            "Gomen ne\\~ Ada error saat memproses pagination\\. \\. \\. 🥺",
            parse_mode='MarkdownV2'
        )

# =========================
# Helper Functions
# =========================

async def edit_or_reply(query, message, text: str, **kwargs) -> None:
    """
    Edit message or reply if editing fails.
    
    Args:
        query: CallbackQuery object
        message: Original message
        text: New text content
        **kwargs: Additional arguments for edit/reply
    """
    try:
        await message.edit_text(text, **kwargs)
    except BadRequest as e:
        # If message can't be modified, send a new message
        if "message is not modified" in str(e):
            logger.debug("Message not modified (identical content)")
        else:
            logger.error(f"Failed to edit message: {e}")
            await message.reply_text(text, **kwargs)
    except Exception as e:
        logger.error(f"Error in edit_or_reply: {e}")
        # Try simpler message as fallback
        try:
            await message.reply_text(
                "Terjadi kesalahan saat memproses pesan. Silakan coba lagi.",
                parse_mode=None
            )
        except Exception:
            pass

def format_sauce_results(results: List[Dict[str, Any]], username: str) -> str:
    """
    Format SauceNAO results with proper Markdown escaping.
    
    Args:
        results: List of source matches
        username: User's first name for personalization
        
    Returns:
        Formatted results string with MarkdownV2 escaping
    """
    # Escape username for MarkdownV2
    escaped_username = escape_markdown_v2(username)
    
    # Start with header
    response = f"*{escaped_username}\\-kun*\\~ Alya menemukan sumber gambar\\! 🎉\n\n"
    
    # Ensure results is a list
    if not isinstance(results, list):
        results = [results] if results else []
    
    # Get maximum 3 results
    display_results = results[:min(3, len(results))]
    
    if not display_results:
        return f"*{escaped_username}\\-kun*\\~ Alya tidak menemukan sumber gambar ini\\. 😔"
    
    # Add results with similarity
    for i, result in enumerate(display_results):
        try:
            # Get values safely
            title = result.get('title', 'Unknown title')
            source = result.get('source', 'Unknown source')
            similarity = result.get('similarity', 0)
            url = result.get('url', '')
            
            # Escape text for MarkdownV2
            safe_title = escape_markdown_v2(title)
            safe_source = escape_markdown_v2(source)
            
            response += f"*Hasil #{i+1}* \\({similarity}% match\\)\n"
            response += f"📌 *{safe_title}*\n"
            response += f"🔍 {safe_source}\n"
            
            # Add URL with markdown link if available
            if url and url != 'Unknown':
                safe_url = escape_markdown_v2(url)
                response += f"🌐 [Lihat Sumber]({safe_url})\n"
                
            response += "\n"
        except Exception as e:
            logger.error(f"Error formatting result {i}: {e}")
            response += f"*Hasil #{i+1}*: Error formatting result\n\n"
    
    # Add footer with tip
    response += "_Klik link di atas untuk melihat sumber aslinya\\~_ ✨"
    return response