"""
Document and Image Handler for Alya Telegram Bot.

This module processes document and image messages, providing analysis,
text extraction, and source searching capabilities.
"""

import os
import re
import logging
import asyncio
import tempfile
import hashlib
from typing import Optional, Union, Dict, Any, List, Tuple
from pathlib import Path

from telegram import Update, Message, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from telegram.error import BadRequest

from config.settings import (
    ANALYZE_PREFIX,
    SAUCE_PREFIX,
    MAX_IMAGE_SIZE,
    MAX_DOCUMENT_SIZE,
    OCR_LANGUAGE,
    ALLOWED_DOCUMENT_TYPES,
    IMAGE_COMPRESS_QUALITY,
    SAUCENAO_API_KEY,
    IMAGE_FORMATS,
    GROUP_CHAT_REQUIRES_PREFIX,  # Import ini penting
    CHAT_PREFIX,                 # Import ini penting
    ADDITIONAL_PREFIXES          # Import ini penting
)
from utils.media_utils import extract_text_from_document, compress_image, get_extension, is_image_file
from utils.image_utils import analyze_image, get_image_data, get_dominant_colors
from utils.formatters import escape_markdown_v2, format_markdown_response
from utils.saucenao import search_with_saucenao

# Setup logger
logger = logging.getLogger(__name__)

# List of supported image extensions
SUPPORTED_IMAGE_FORMATS = IMAGE_FORMATS if IMAGE_FORMATS else ['jpeg', 'jpg', 'png', 'webp', 'gif', 'tiff']

# Semua kemungkinan prefiks untuk chat dari dokumen - akan digunakan untuk deteksi
ALL_VALID_PREFIXES = [CHAT_PREFIX.lower(), ANALYZE_PREFIX.lower(), SAUCE_PREFIX.lower()] + \
                     [prefix.lower() for prefix in ADDITIONAL_PREFIXES] + \
                     ["!trace", "!sauce", "!ocr", "/trace", "/sauce", "/ocr"]

async def handle_document_image(update: Update, context: CallbackContext) -> None:
    """
    Handle document and image messages.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.message:
        return
        
    # Check for the !trace or !sauce command
    command = None
    command_type = None
    message_text = update.message.caption or ""
    
    # Check if we're in a group chat
    is_private_chat = update.message.chat.type == "private"
    has_valid_prefix = False
    
    # PERBAIKAN: Untuk grup, periksa prefix yang valid
    if not is_private_chat:
        caption_lower = message_text.lower().strip()
        
        # Cek apakah ada prefix yang valid
        has_valid_prefix = any(caption_lower.startswith(prefix) for prefix in ALL_VALID_PREFIXES)
        
        # Kalo di grup dan butuh prefix tapi gak ada prefix yang valid, JANGAN PROSES
        if GROUP_CHAT_REQUIRES_PREFIX and not has_valid_prefix:
            # Hanya log untuk debug
            logger.debug(f"Ignoring document/image in group without valid prefix. Caption: '{message_text[:30]}...'")
            return

    # Continued checking for specific commands
    if message_text.startswith(ANALYZE_PREFIX):
        command = message_text[len(ANALYZE_PREFIX):].strip()
        command_type = "trace"
    elif message_text.startswith(SAUCE_PREFIX):
        command = message_text[len(SAUCE_PREFIX):].strip()
        command_type = "sauce"
        
    user = update.effective_user
    
    try:
        # Process based on command type
        if command_type == "trace":
            await handle_trace_command(update.message, user, context)
        elif command_type == "sauce":
            await handle_sauce_command(update.message, user, context)
        else:
            # PERBAIKAN: Untuk grup, jangan proses jika tidak ada command yang valid
            if not is_private_chat and GROUP_CHAT_REQUIRES_PREFIX and not has_valid_prefix:
                return
                
            # Just process normally for private chat or valid prefix in group
            await process_document_media(update.message, user, context)
    except Exception as e:
        logger.error(f"Error in document/media handling: {e}")
        try:
            await update.message.reply_text(
                "Maaf, terjadi kesalahan saat memproses dokumen/gambar.",
                parse_mode=None
            )
        except Exception:
            pass

async def process_document_media(message: Message, user: User, context: CallbackContext) -> None:
    """
    Process document or media message.
    
    Args:
        message: Telegram message with document/media
        user: User who sent the message
        context: Callback context
    """
    try:
        # PERBAIKAN: Cek dulu apakah ini grup atau private chat
        is_private_chat = message.chat.type == "private"
        caption_text = (message.caption or "").lower().strip()
        has_valid_prefix = any(caption_text.startswith(prefix) for prefix in ALL_VALID_PREFIXES)
        
        # Untuk grup, jangan proses jika tidak ada prefix yang valid
        if not is_private_chat and GROUP_CHAT_REQUIRES_PREFIX and not has_valid_prefix:
            logger.debug(f"Ignoring document/image in group without valid prefix. Caption: '{caption_text[:30]}...'")
            return
            
        # Check for photo
        if message.photo:
            # Hanya proses jika ada caption dengan prefix khusus
            # Atau ini adalah private chat
            if is_private_chat or has_valid_prefix:
                # Download photo for processing
                temp_path = await download_image_from_message(message, context)
                
                if temp_path:
                    # Process image
                    try:
                        analysis_result = await analyze_image(temp_path)
                        if analysis_result:
                            # Format response with HTML
                            response = f"<b>Analisis Gambar:</b>\n\n{analysis_result}"
                            await message.reply_text(response, parse_mode=ParseMode.HTML)
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_path)
                        except Exception as e:
                            logger.error(f"Error cleaning up temp file: {e}")
            else:
                # Grup tanpa prefix yang valid, jangan proses
                return
                
        # Check for document
        elif message.document:
            # Extract document details
            mime_type = message.document.mime_type
            file_size = message.document.file_size
            
            # Check if document is processable
            if not mime_type or not file_size:
                return
                
            # Check if it's an image
            is_image = mime_type.startswith('image/')
            
            # Check size limit
            if file_size > MAX_DOCUMENT_SIZE:
                await message.reply_text(
                    "Ukuran dokumen terlalu besar. Maksimum 10MB.",
                    parse_mode=None
                )
                return
                
            if is_image:
                # Hanya proses jika ini private chat atau ada prefix valid di grup
                if is_private_chat or has_valid_prefix:
                    # Download and process image
                    temp_path = await download_image_from_message(message, context)
                    
                    if temp_path:
                        try:
                            analysis_result = await analyze_image(temp_path)
                            if analysis_result:
                                # Format response with HTML
                                response = f"<b>Analisis Gambar:</b>\n\n{analysis_result}"
                                await message.reply_text(response, parse_mode=ParseMode.HTML)
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(temp_path)
                            except Exception as e:
                                logger.error(f"Error cleaning up temp file: {e}")
                else:
                    # Grup tanpa prefix valid, jangan proses
                    return
                                
            elif mime_type in ALLOWED_DOCUMENT_TYPES:
                # Hanya proses jika ini private chat atau ada prefix valid di grup
                if is_private_chat or has_valid_prefix:
                    # Process as text document
                    await message.reply_text(
                        "Memproses dokumen...",
                        parse_mode=None
                    )
                    
                    # Download and process document
                    file = await context.bot.get_file(message.document.file_id)
                    
                    # Use appropriate extension
                    if mime_type == 'application/pdf':
                        extension = '.pdf'
                    elif 'word' in mime_type:
                        extension = '.docx' 
                    else:
                        extension = '.txt'
                        
                    fd, temp_path = tempfile.mkstemp(suffix=extension)
                    os.close(fd)
                    
                    await file.download_to_drive(temp_path)
                    
                    # Extract text
                    try:
                        text_content = await extract_text_from_document(temp_path, mime_type)
                        
                        if text_content and len(text_content.strip()) > 0:
                            # Truncate if too long
                            if len(text_content) > 4000:
                                text_content = text_content[:4000] + "... [teks terpotong]"
                                
                            # Send text content using HTML parse mode
                            await message.reply_text(
                                f"<b>Teks dari dokumen:</b>\n\n{text_content}",
                                parse_mode=ParseMode.HTML
                            )
                        else:
                            await message.reply_text(
                                "Tidak dapat mengekstrak teks dari dokumen ini.",
                                parse_mode=None
                            )
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_path)
                        except Exception as e:
                            logger.error(f"Error cleaning up temp file: {e}")
                else:
                    # Grup tanpa prefix valid, jangan proses
                    return
    except Exception as e:
        logger.error(f"Error processing document/media: {e}")
        try:
            await message.reply_text(
                "Maaf, terjadi kesalahan saat memproses dokumen/media.",
                parse_mode=None
            )
        except Exception:
            pass

async def handle_trace_command(message: Message, user: User, context: CallbackContext) -> None:
    """
    Handle trace (image analysis) command for both images and documents.
    
    Args:
        message: Telegram message with image or document
        user: User who sent the message
        context: Callback context
    """
    try:
        # Send initial processing message
        status_msg = await message.reply_text(
            "Menganalisis konten... 🔍",
            parse_mode=None
        )
        
        # Determine the content type
        if message.photo:
            # Process image
            temp_path = await download_image_from_message(message, context)
            
            if not temp_path:
                await status_msg.edit_text(
                    "Alya membutuhkan gambar untuk dianalisis. Kirimkan gambar atau balas pesan dengan gambar.",
                    parse_mode=None
                )
                return
                
            # Use Gemini for image analysis
            await analyze_with_gemini(status_msg, temp_path, "image", context)
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Error removing temp image: {e}")
                
        elif message.document:
            # Check if it's a supported document type
            mime_type = message.document.mime_type
            file_name = message.document.file_name
            file_ext = get_extension(file_name) if file_name else ""
            
            # Check if it's an image document
            if mime_type and mime_type.startswith('image/'):
                # Process as image
                temp_path = await download_image_from_message(message, context)
                
                if temp_path:
                    # Use Gemini for image analysis
                    await analyze_with_gemini(status_msg, temp_path, "image", context)
                    
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logger.error(f"Error removing temp image: {e}")
            
            # Check if it's a text document
            elif mime_type in ALLOWED_DOCUMENT_TYPES:
                # Download document
                file = await context.bot.get_file(message.document.file_id)
                
                # Use appropriate extension
                if mime_type == 'application/pdf':
                    extension = '.pdf'
                elif 'word' in mime_type:
                    extension = '.docx'
                else:
                    extension = '.txt'
                    
                fd, temp_path = tempfile.mkstemp(suffix=extension)
                os.close(fd)
                
                await file.download_to_drive(temp_path)
                
                # Extract text and analyze
                try:
                    text_content = await extract_text_from_document(temp_path, mime_type)
                    
                    if text_content and len(text_content.strip()) > 0:
                        # Analyze text document with Gemini
                        await analyze_with_gemini(status_msg, temp_path, "document", context, text_content)
                    else:
                        # Failed to extract any text
                        await status_msg.edit_text(
                            "Tidak dapat mengekstrak teks dari dokumen ini untuk dianalisis.",
                            parse_mode=None
                        )
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logger.error(f"Error removing temp document: {e}")
            else:
                # Unsupported document type
                await status_msg.edit_text(
                    f"Maaf, format dokumen '{mime_type or file_ext}' tidak didukung untuk analisis. " +
                    "Gunakan gambar, PDF, atau dokumen teks.",
                    parse_mode=None
                )
        else:
            # No media attached
            await status_msg.edit_text(
                "Alya membutuhkan gambar atau dokumen untuk dianalisis. " +
                "Gunakan command ini dengan mengirim atau reply ke gambar/dokumen.",
                parse_mode=None
            )
            
    except Exception as e:
        logger.error(f"Error in trace command: {e}")
        try:
            await message.reply_text(
                "Maaf, terjadi kesalahan saat menganalisis media.",
                parse_mode=None
            )
        except Exception:
            pass

async def analyze_with_gemini(
    status_msg: Message, 
    file_path: str, 
    content_type: str, 
    context: CallbackContext,
    text_content: Optional[str] = None
) -> None:
    """
    Analyze content with Gemini AI.
    
    Args:
        status_msg: Status message to update
        file_path: Path to the file
        content_type: Type of content ('image' or 'document')
        context: CallbackContext
        text_content: Extracted text content for documents
    """
    try:
        await status_msg.edit_text(
            f"Memproses {content_type}... Ini akan memakan waktu beberapa detik.",
            parse_mode=None
        )
        
        # Import Gemini analysis functions
        from core.models import generate_image_analysis, generate_document_analysis
        
        if content_type == "image":
            # Get basic metadata
            img_data = get_image_data(file_path)
            
            # Get color information
            colors = get_dominant_colors(file_path)
            
            # Extract and format dominant colors
            color_info = "\n\n<b>Warna Dominan:</b>\n"
            if colors and len(colors) > 0:
                for i, color in enumerate(colors[:3], 1):
                    color_info += f"{i}. RGB: {color}\n"
            else:
                color_info += "Tidak dapat mengekstrak warna dominan.\n"
                
            # Format image metadata
            img_info = "\n<b>Informasi Gambar:</b>\n"
            img_info += f"• Dimensi: {img_data.get('width', 0)}x{img_data.get('height', 0)} px\n"
            img_info += f"• Format: {img_data.get('format', 'unknown')}\n"
            img_info += f"• Mode: {img_data.get('mode', 'unknown')}\n"
            
            # Get advanced analysis from Gemini
            try:
                gemini_analysis = await generate_image_analysis(file_path)
                
                # Format the complete response with HTML
                response = f"<b>Hasil Analisis Gambar:</b>\n\n{gemini_analysis}{color_info}{img_info}"
            except Exception as gemini_error:
                logger.error(f"Error with Gemini image analysis: {gemini_error}")
                
                # Fall back to basic analysis
                basic_analysis = await analyze_image(file_path)
                response = f"<b>Hasil Analisis Gambar:</b>\n\n{basic_analysis}{color_info}{img_info}"
        else:
            # Document analysis
            try:
                # Get document metadata
                file_size = os.path.getsize(file_path)
                
                # PERBAIKAN: Ambil nama file yang asli dari message, bukan nama temporary
                if status_msg.reply_to_message and status_msg.reply_to_message.document:
                    file_name = status_msg.reply_to_message.document.file_name
                else:
                    # Fallback ke nama file temporary kalau tidak bisa mendapatkan nama asli
                    file_name = os.path.basename(file_path)
                    
                file_ext = os.path.splitext(file_name)[1].lower()
                
                # Format document info with HTML for better presentation
                doc_info = "\n\n<b>Informasi Dokumen:</b>\n"
                doc_info += f"<b>• Nama File:</b> {file_name}\n"
                doc_info += f"<b>• Tipe:</b> {file_ext}\n"
                doc_info += f"<b>• Ukuran:</b> {file_size / 1024:.1f} KB\n"
                
                # Text content stats
                if text_content:
                    word_count = len(text_content.split())
                    line_count = len(text_content.splitlines())
                    doc_info += f"<b>• Kata:</b> {word_count}\n"
                    doc_info += f"<b>• Baris:</b> {line_count}\n"
                    
                    # Analyzing document with Gemini
                    await status_msg.edit_text(
                        "Menganalisis dokumen dengan Gemini AI...",
                        parse_mode=None
                    )
                    
                    # Process document with cleaned HTML
                    gemini_analysis = await generate_document_analysis(text_content)
                    
                    # Format the complete response with HTML
                    response = f"<b>📄 HASIL ANALISIS DOKUMEN</b>\n\n{gemini_analysis}{doc_info}"
                    
                    # Apply thorough sanitization of HTML to ensure compatibility with Telegram
                    response = sanitize_html_response(response)
                else:
                    response = f"<b>📄 HASIL ANALISIS DOKUMEN</b>\n\nTidak dapat mengekstrak teks untuk dianalisis.{doc_info}"
            except Exception as doc_error:
                logger.error(f"Error with document analysis: {doc_error}")
                response = f"<b>📄 HASIL ANALISIS DOKUMEN</b>\n\nTerjadi kesalahan saat menganalisis dokumen."
        
        # Handle response length - telegram has limits
        if len(response) > 4096:
            response = response[:4090] + "..."
            
        # Try sending with HTML, but fall back to plain text if needed
        try:
            await status_msg.edit_text(
                response,
                parse_mode=ParseMode.HTML
            )
        except BadRequest as e:
            logger.warning(f"HTML parsing failed: {e}")
            # Coba lagi dengan menghapus HTML tags
            try:
                # Hapus semua HTML tag
                plain_response = re.sub(r'<[^>]*>', '', response)
                await status_msg.edit_text(
                    plain_response,
                    parse_mode=None
                )
            except Exception as final_err:
                logger.error(f"Final error sending response: {final_err}")
                # Fallback paling sederhana
                await status_msg.edit_text(
                    "Maaf, terjadi error saat menampilkan analisis.",
                    parse_mode=None
                )
                
    except Exception as e:
        logger.error(f"Error in analyze_with_gemini: {e}")
        await status_msg.edit_text(
            f"Terjadi kesalahan saat menganalisis: {str(e)[:100]}...",
            parse_mode=None
        )

def sanitize_html_response(text: str) -> str:
    """
    Sanitize HTML response to ensure compatibility with Telegram HTML parsing.
    
    Args:
        text: Text with HTML formatting
        
    Returns:
        Sanitized text compatible with Telegram HTML parsing
    """
    # Telegram hanya mendukung tag <b>, <i>, <u>, <s>, <code>, <pre>, <a>

    # 1. Fix incomplete tags di akhir text (seperti "</u")
    text = re.sub(r'</?[a-zA-Z0-9]*$', '', text)
    
    # 2. Ganti tag-tag yang tidak didukung dengan format yang lebih sederhana
    text = text.replace('<ul>', '')
    text = text.replace('</ul>', '')
    text = text.replace('<li>', '• ')
    text = text.replace('</li>', '\n')
    text = text.replace('<p>', '')
    text = text.replace('</p>', '\n\n')
    
    # 3. Hitung berapa banyak tag yang dibuka dan ditutup
    supported_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a']
    for tag in supported_tags:
        # Hitung tag pembuka
        open_tags = len(re.findall(f'<{tag}[^>]*>', text))
        # Hitung tag penutup
        close_tags = len(re.findall(f'</{tag}>', text))
        # Tambahkan tag penutup jika kurang
        if open_tags > close_tags:
            text += f'</{tag}>' * (open_tags - close_tags)
        # Hapus tag penutup yang berlebihan (dari belakang)
        elif close_tags > open_tags:
            for _ in range(close_tags - open_tags):
                last_idx = text.rfind(f'</{tag}>')
                if last_idx >= 0:
                    text = text[:last_idx] + text[last_idx + len(f'</{tag}>'):]
    
    # 4. Hapus semua tag yang tidak didukung
    all_tags = re.findall(r'</?([a-zA-Z0-9]+)[^>]*>', text)
    for tag in set(all_tags):
        if tag.lower() not in supported_tags:
            text = re.sub(f'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
            text = re.sub(f'</{tag}>', '', text, flags=re.IGNORECASE)
    
    # 5. Perbaiki masalah umum HTML
    text = text.replace('&nbsp;', ' ')
    text = text.replace('\n\n\n\n', '\n\n')
    text = text.replace('\n\n\n', '\n\n')
    
    # 6. Final check: duplikat tag di akhir
    text = re.sub(r'(</?[a-zA-Z0-9]+>)\1+', r'\1', text)
    
    # Jangan pakai HTMLParser - terlalu kompleks dan bisa bikin stripping agresif
    # Yang penting pastikan semua tag HTML didukung dan seimbang
    
    return text

async def handle_sauce_command(message: Message, user: User, context: CallbackContext) -> None:
    """
    Handle sauce (reverse image search) command.
    
    Args:
        message: Telegram message with image
        user: User who sent the message
        context: Callback context
    """
    try:
        # Send initial processing message
        status_msg = await message.reply_text(
            "Mencari sumber gambar ini... 🔎",
            parse_mode=None
        )
            
        # Download the image
        temp_path = await download_image_from_message(message, context)
        
        if not temp_path:
            await status_msg.edit_text(
                "Alya membutuhkan gambar untuk dicari sumbernya! Kirimkan gambar atau reply pesan dengan gambar.",
                parse_mode=None
            )
            return
            
        # Log hash for debugging but don't show to user
        try:
            with open(temp_path, 'rb') as f:
                img_hash = hashlib.md5(f.read()).hexdigest()[:10]
                logger.info(f"Processing image with hash: {img_hash}")
        except Exception as e:
            logger.error(f"Failed to hash image: {e}")
            
        # Update status
        await status_msg.edit_text(
            "Mencari sumber gambar...",
            parse_mode=None
        )
            
        # Search for the sauce
        try:
            await search_with_saucenao(status_msg, temp_path)
        except Exception as e:
            logger.error(f"Error in sauce search: {e}")
            try:
                await status_msg.edit_text(
                    "Error mencari sumber image. Coba lagi nanti atau gunakan reverse image search lain.",
                    parse_mode=None
                )
            except Exception as edit_error:
                logger.error(f"Error updating error message: {edit_error}")
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except Exception as e:
            logger.error(f"Error cleaning up temp file: {e}")
            
    except Exception as e:
        logger.error(f"Error processing document/image: {e}")
        try:
            await message.reply_text(
                "Maaf, terjadi kesalahan saat memproses gambar.",
                parse_mode=None
            )
        except Exception:
            pass

async def download_image_from_message(message: Message, context: CallbackContext) -> Optional[str]:
    """
    Download image from a message.
    
    Args:
        message: Message object containing image
        context: CallbackContext
        
    Returns:
        Path to downloaded image file or None if failed
    """
    try:
        bot = context.bot
        
        # Download photo
        if message.photo:
            # Get largest photo
            photo = message.photo[-1]
            photo_file = await bot.get_file(photo.file_id)
            file_path = f"temp_{photo.file_unique_id}.jpg"
            await photo_file.download_to_drive(file_path)
            return file_path
            
        # Download document
        elif message.document and is_image_file(get_extension(message.document.file_name)):
            doc_file = await bot.get_file(message.document.file_id)
            file_path = f"temp_{message.document.file_unique_id}.{get_extension(message.document.file_name)}"
            await doc_file.download_to_drive(file_path)
            return file_path
            
        return None
        
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None

def validate_command_prefix(message: Message) -> bool:
    """
    Validate that a message contains a valid command prefix.
    
    Args:
        message: Telegram message to check
        
    Returns:
        True if message has valid command prefix, False otherwise
    """
    if not message:
        return False
        
    # Cek jika ini adalah hasil dari command handler (/trace, /sauce, dll)
    # Dalam kasus ini, message.caption mungkin None tapi tetap valid
    if hasattr(message, 'via_bot') and message.via_bot:
        return True
        
    # Periksa caption untuk command prefix
    caption = message.caption
    if not caption:
        return False
        
    caption_lower = caption.lower().strip()
    valid_prefixes = [
        ANALYZE_PREFIX.lower(), 
        SAUCE_PREFIX.lower(),
        "!trace", 
        "!sauce", 
        "!ocr", 
        "/trace", 
        "/sauce", 
        "/ocr"
    ]
    
    # Cek apakah caption dimulai dengan prefix valid
    return any(caption_lower.startswith(prefix) for prefix in valid_prefixes)

async def store_media_context(
    message: Message, 
    user_id: int, 
    context_type: str, 
    additional_data: Optional[dict] = None
) -> None:
    """
    Store media related context for persistence.
    
    Args:
        message: Message containing media
        user_id: User ID
        context_type: Type of context (trace, sauce, etc.)
        additional_data: Optional additional context data
    """
    try:
        chat_id = message.chat.id
        
        # Basic context data
        context_data = {
            'command': context_type,
            'timestamp': int(time.time()),
            'chat_id': chat_id,
            'message_id': message.message_id,
            'has_photo': bool(message.photo),
            'has_document': bool(message.document),
            'caption': message.caption,
        }
        
        # Add any additional data provided
        if additional_data:
            context_data.update(additional_data)
        
        # Save to context manager
        context_manager.save_context(user_id, chat_id, f'media_{context_type}', context_data)
        logger.debug(f"Stored {context_type} context for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error saving media context: {e}")

async def handle_document_callback(update: Update, context: CallbackContext) -> None:
    """
    Handle document-related callback queries.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.callback_query:
        return
        
    callback_query = update.callback_query
    callback_data = callback_query.data
    
    try:
        # Extract command and potential parameters
        parts = callback_data.split('_')
        if len(parts) < 1:
            return
            
        command = parts[0]
        
        # Handle different commands
        if command == 'sauce' or command == 'sauce_nao':
            # Get the message with image (the one being replied to)
            message = callback_query.message.reply_to_message
            if message:
                await handle_sauce_command(message, update.effective_user, context)
            else:
                await callback_query.answer("Error: Image not found", show_alert=True)
                
        elif command == 'img_describe':
            # Get the original message with image
            message = callback_query.message.reply_to_message
            if message:
                await handle_trace_command(message, update.effective_user, context)
            else:
                await callback_query.answer("Error: Image not found", show_alert=True)
                
        elif command == 'img_source':
            # Similar to sauce command
            message = callback_query.message.reply_to_message
            if message:
                await handle_sauce_command(message, update.effective_user, context)
            else:
                await callback_query.answer("Error: Image not found", show_alert=True)
                
        # Acknowledge the callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error handling document callback: {e}")
        try:
            await callback_query.answer("Error processing request", show_alert=True)
        except Exception:
            pass