"""
Callback Handlers for Alya Telegram Bot.

This module handles various button callbacks and interactive elements,
including reverse image search, menu navigation, and user preferences.
"""

import logging
import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import CallbackContext
from telegram.error import BadRequest

from utils.saucenao import reverse_search_image
from utils.formatters import format_markdown_response

logger = logging.getLogger(__name__)

# =========================
# Button Callbacks
# =========================

async def handle_button_callback(update: Update, context: CallbackContext) -> None:
    """
    Process button callback queries from inline keyboards.
    
    Args:
        update: Telegram update object
        context: CallbackContext
    """
    query = update.callback_query
    user = update.effective_user
    callback_data = query.data
    
    try:
        # Always answer the callback query to clear the loading state
        await query.answer()
        
        # Handle image search mode selections
        if callback_data.startswith('img_'):
            image_mode = callback_data.split('_')[1]
            await handle_image_search_callback(query, user, image_mode)
            return
        
        # Handle image source search callbacks
        if callback_data.startswith('sauce_'):
            source_type = callback_data.split('_')[1]
            await handle_sauce_callback(query, user, source_type)
            return
            
        # Handle language selection
        if callback_data.startswith('lang_'):
            lang_code = callback_data.split('_')[1]
            await handle_language_callback(query, context, lang_code)
            return
            
        # Default response for unknown callback
        try:
            await query.edit_message_text(
                f"Gomennasai\\! Alya\\-chan tidak mengerti callback ini\\: `{callback_data}`",
                parse_mode='MarkdownV2'
            )
        except BadRequest as e:
            # Jika pesan tidak dapat diubah karena identik, cukup abaikan
            if "message is not modified" in str(e):
                logger.debug("Message not modified because content is identical")
            else:
                raise e
            
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        try:
            await query.edit_message_text(
                "Gomen ne\\~ Ada error saat memproses perintah\\. \\. \\. 🥺",
                parse_mode='MarkdownV2'
            )
        except BadRequest as e:
            # Jika pesan tidak dapat diubah karena identik, kirim pesan baru saja
            if "message is not modified" in str(e):
                await query.message.reply_text(
                    "Gomen ne\\~ Ada error saat memproses perintah\\. \\. \\. 🥺",
                    parse_mode='MarkdownV2'
                )
            else:
                raise e

# New callback handler for image search modes
async def handle_image_search_callback(query, user, mode):
    """
    Handle image search mode selection callbacks.
    
    Args:
        query: CallbackQuery object
        user: User who triggered the callback
        mode: Selected image search mode (describe/source)
    """
    message = query.message
    original_msg = message.reply_to_message
    
    if not original_msg or not original_msg.photo:
        try:
            await query.edit_message_text(
                "Gomennasai\\! Alya tidak dapat menemukan gambar untuk diproses\\. \\. \\. 🥺",
                parse_mode='MarkdownV2'
            )
        except BadRequest as e:
            if "message is not modified" in str(e):
                await message.reply_text(
                    "Gomennasai\\! Alya tidak dapat menemukan gambar untuk diproses\\. \\. \\. 🥺",
                    parse_mode='MarkdownV2'
                )
            else:
                raise e
        return
    
    # Get largest photo (best quality)
    photo = original_msg.photo[-1]
    
    # Process based on selected mode
    if mode == 'describe':
        # Show processing status
        try:
            await query.edit_message_text(
                f"*{user.first_name}\\-kun*\\~ Alya sedang menganalisis gambar ini\\.\\.\\. 🔎",
                parse_mode='MarkdownV2'
            )
        except BadRequest as e:
            if "message is not modified" in str(e):
                await message.reply_text(
                    f"*{user.first_name}\\-kun*\\~ Alya sedang menganalisis gambar ini\\.\\.\\. 🔎",
                    parse_mode='MarkdownV2'
                )
            else:
                raise e
                
        # Get file and process
        try:
            photo_file = await photo.get_file()
            from handlers.document_handlers import process_file
            await process_file(original_msg, user, photo_file, "jpg")
        except Exception as e:
            logger.error(f"Error in image describe callback: {e}")
            try:
                await query.edit_message_text(
                    f"Gomen ne\\~ Ada error saat menganalisis gambar\\. \\. \\. 🥺",
                    parse_mode='MarkdownV2'
                )
            except BadRequest:
                pass
    
    elif mode == 'source':
        # Redirect to sauce command handler
        from handlers.document_handlers import handle_sauce_command
        await handle_sauce_command(original_msg, user)

# =========================
# Sauce Callbacks
# =========================

async def handle_sauce_callback(query, user, source_type):
    """
    Process reverse image search callbacks.
    
    Args:
        query: CallbackQuery object
        user: User who triggered the callback
        source_type: Type of source search (anime/lens)
    """
    message = query.message
    original_msg = message.reply_to_message
    
    if not original_msg or not original_msg.photo:
        try:
            await query.edit_message_text(
                "Gomennasai\\! Alya tidak dapat menemukan gambar untuk dicari\\. \\. \\. 🥺",
                parse_mode='MarkdownV2'
            )
        except BadRequest as e:
            if "message is not modified" in str(e):
                await message.reply_text(
                    "Gomennasai\\! Alya tidak dapat menemukan gambar untuk dicari\\. \\. \\. 🥺",
                    parse_mode='MarkdownV2'
                )
            else:
                raise e
        return
    
    # Get largest photo (best quality)
    photo = original_msg.photo[-1]
    
    # Show searching status
    try:
        await query.edit_message_text(
            f"*{user.first_name}\\-kun*\\~ Alya sedang mencari sumber gambarnya\\.\\.\\. 🔍",
            parse_mode='MarkdownV2'
        )
    except BadRequest as e:
        if "message is not modified" in str(e):
            # Jika pesan tidak dapat diubah karena identik, kirim status melalui pesan baru
            status_msg = await message.reply_text(
                f"*{user.first_name}\\-kun*\\~ Alya sedang mencari sumber gambarnya\\.\\.\\. 🔍",
                parse_mode='MarkdownV2'
            )
        else:
            raise e
    
    # Get image file and process
    try:
        photo_file = await photo.get_file()
        
        if source_type == 'anime':
            # Use SauceNAO for anime image search
            sauce_results = await reverse_search_image(photo_file)
            
            if not sauce_results or len(sauce_results) == 0:
                # No results found
                try:
                    await query.edit_message_text(
                        f"*{user.first_name}\\-kun*\\~ Alya tidak menemukan sumber gambar ini\\. \\. \\. 😔",
                        parse_mode='MarkdownV2'
                    )
                except BadRequest as e:
                    if "message is not modified" in str(e):
                        await message.reply_text(
                            f"*{user.first_name}\\-kun*\\~ Alya tidak menemukan sumber gambar ini\\. \\. \\. 😔",
                            parse_mode='MarkdownV2'
                        )
                    else:
                        raise e
                return
                
            # Format and send results
            response = format_sauce_results(sauce_results, user.first_name)
            
            try:
                await query.edit_message_text(
                    response,
                    parse_mode='MarkdownV2',
                    disable_web_page_preview=True
                )
            except BadRequest as e:
                if "message is not modified" in str(e):
                    # Jika konten sama persis, kirim hasil sebagai pesan baru
                    await message.reply_text(
                        response,
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
                else:
                    raise e
                    
        elif source_type == 'lens':
            # Generate Google Lens URL
            file_url = f"https://lens.google.com/uploadbyurl?url={photo_file.file_path}"
            escaped_username = user.first_name.replace('.', '\\.').replace('-', '\\-')
            
            try:
                await query.edit_message_text(
                    f"*{escaped_username}\\-kun*\\~ Kamu bisa mencari dengan Google Lens\\:\n\n"
                    f"[🔎 Buka di Google Lens]({file_url})",
                    parse_mode='MarkdownV2',
                    disable_web_page_preview=True
                )
            except BadRequest as e:
                if "message is not modified" in str(e):
                    await message.reply_text(
                        f"*{escaped_username}\\-kun*\\~ Kamu bisa mencari dengan Google Lens\\:\n\n"
                        f"[🔎 Buka di Google Lens]({file_url})",
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
                else:
                    raise e
    
    except Exception as e:
        logger.error(f"Error in sauce callback: {e}")
        error_msg = "Gomen ne\\~ Ada error saat mencari sumber gambar\\. \\. \\. 🥺"
        
        try:
            await query.edit_message_text(error_msg, parse_mode='MarkdownV2')
        except BadRequest as e:
            if "message is not modified" in str(e):
                await message.reply_text(error_msg, parse_mode='MarkdownV2')
            else:
                raise e

# =========================
# Language Callbacks
# =========================

async def handle_language_callback(query, context, lang_code):
    """
    Process language selection callbacks.
    
    Args:
        query: CallbackQuery object
        context: CallbackContext for state storage
        lang_code: Selected language code
    """
    # Update user's language preference
    # ...existing code...

# =========================
# Helper Functions
# =========================

def format_sauce_results(results, username):
    """
    Format SauceNAO results with proper Markdown escaping.
    
    Args:
        results: List of source matches
        username: User's first name for personalization
        
    Returns:
        Formatted results string with MarkdownV2 escaping
    """
    # Escape username for MarkdownV2
    escaped_username = username.replace('.', '\\.').replace('-', '\\-')
    
    # Start with header
    response = f"*{escaped_username}\\-kun*\\~ Alya menemukan sumber gambar\\! 🎉\n\n"
    
    # Ensure results is a list before slicing
    if not isinstance(results, list):
        # Convert to list if it's not already one
        if hasattr(results, 'items') and callable(getattr(results, 'items')):
            # If it's a dict-like object
            results_list = list(results.items())
        elif hasattr(results, '__iter__'):
            # If it's any other iterable
            results_list = list(results)
        else:
            # If it's neither iterable nor dict-like
            results_list = [results]
    else:
        results_list = results
    
    # Get maximum 3 results safely
    display_results = results_list[:min(3, len(results_list))]
    
    # Add results with similarity
    for i, result in enumerate(display_results):
        try:
            # Get values safely, handling different result formats
            if isinstance(result, dict):
                title = result.get('title', 'Unknown Title')
                source = result.get('source', 'Unknown Source')
                url = result.get('url', 'Unknown')
                similarity = result.get('similarity', 0)
            else:
                # If not a dict, use string representation
                title = str(result)
                source = "Unknown Source"
                url = "Unknown"
                similarity = 0
            
            # Escape text for MarkdownV2
            safe_title = title.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('*', '\\*')
            safe_source = source.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('*', '\\*')
            
            response += f"*Hasil #{i+1}* \\({similarity}% match\\)\n"
            response += f"📌 *{safe_title}*\n"
            response += f"🔍 {safe_source}\n"
            
            # Add URL with markdown link if available and valid
            if url and url != 'Unknown':
                # Make sure URL is properly formatted for Markdown
                url_parts = url.split('://')
                if len(url_parts) > 1:
                    # Format as link only if it has proper protocol
                    response += f"🔗 [Lihat Sumber]({url})\n"
                else:
                    # Otherwise just show the URL text
                    safe_url = url.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!')
                    response += f"🔗 URL: {safe_url}\n"
            
            response += "\n"
        except Exception as e:
            logger.error(f"Error formatting result {i}: {e}")
            response += f"*Hasil #{i+1}*: Error formatting result\n\n"
    
    # Add footer with tip
    response += "_Klik link di atas untuk melihat sumber aslinya\\~_ ✨"
    return response