"""
Document and Image Handler for Alya Telegram Bot.

This module processes document and image messages, providing analysis,
text extraction, and source searching capabilities.
"""
import logging
import asyncio
import tempfile
import hashlib
import time
from typing import Optional, Union, Dict, Any, List, Tuple
from pathlib import Path
import tempfile
import os

from telegram import Update, Message, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext 
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest

from core.models import generate_image_analysis, generate_document_analysis
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.media_utils import download_media, extract_text_from_document, cleanup_temp_file
from config.settings import (
    TEMP_DIR,
    MAX_IMAGE_SIZE,
    IMAGE_COMPRESS_QUALITY,
    MAX_DOCUMENT_SIZE,
    ALLOWED_DOCUMENT_TYPES
)

logger = logging.getLogger(__name__)

async def handle_document_image(update: Update, context: CallbackContext) -> None:
    """Handle document/image analysis."""
    if not update.message or not update.effective_user:
        return
        
    # Get chat type and user
    chat_type = update.message.chat.type
    user = update.effective_user
    
    # For group chats, only respond if:
    # 1. Message has valid command prefix in caption
    # 2. Message is replying to bot
    # 3. Bot is mentioned in caption
    if chat_type in ["group", "supergroup"]:
        caption = update.message.caption or ""
        is_reply_to_bot = (
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user and
            update.message.reply_to_message.from_user.id == context.bot.id
        )
        mentions_bot = f"@{context.bot.username}" in caption if context.bot.username else False
        has_command = any(caption.lower().startswith(prefix.lower()) for prefix in ALL_VALID_PREFIXES)
        
        # If none of the conditions are met, ignore the message
        if not (has_command or is_reply_to_bot or mentions_bot):
            return

    # Get command from caption
    command_type = None
    message_text = update.message.caption or ""
    message_text_lower = message_text.lower().strip()
    
    # Check for commands in caption
    if message_text_lower.startswith(("!trace", "/trace")):
        command_type = "trace"
    elif message_text_lower.startswith(("!sauce", "/sauce")):
        command_type = "sauce"
    elif message_text_lower.startswith(("!ocr", "/ocr")):
        command_type = "ocr"
        
    try:
        # Process based on command type
        if command_type in ["trace", "ocr"]:
            await handle_trace_command(update.message, user, context)
        elif command_type == "sauce":
            await handle_sauce_command(update.message, user, context)
        elif update.message.chat.type == "private":
            # Only process as normal chat if in private
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
                f"*Gomenasai {escape_markdown_v2(user.first_name)}\\-kun*\\!\n\n"
                f"Alya tidak bisa mengekstrak teks dari dokumen ini\\. 😔\n"
                f"Coba dokumen lain atau format yang berbeda ya\\?",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
            
        # Generate analysis
        analysis = await generate_document_analysis(extracted_text)
        
        # Format response
        response = format_document_response(
            analysis=analysis,
            username=user.first_name,
            file_name=message.document.file_name,
            extracted_text=extracted_text
        )
        
        await message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    except Exception as e:
        logger.error(f"Error in analyze_with_gemini: {e}")
        await status_msg.edit_text(
            "Maaf, terjadi kesalahan saat menganalisis konten 😔",
            parse_mode=None
        )

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
        logger.error(f"Error analyzing image: {e}")
        raise

def format_document_response(analysis: str, username: str, 
                           file_name: str, extracted_text: str) -> str:
    """Format document analysis with persona touch."""
    # Get document metadata
    metadata = {
        "Nama File": file_name,
        "Tipe": Path(file_name).suffix,
        "Ukuran Teks": f"{len(extracted_text)} karakter",
        "Jumlah Kata": f"{len(extracted_text.split())} kata",
        "Jumlah Baris": f"{len(extracted_text.splitlines())} baris"
    }
    
    # Format with roleplay actions for persona
    response = (
        f"[membuka dokumen dengan teliti]\n\n"
        f"📄 *HASIL ANALISIS DOKUMEN*\n\n"
        f"*Informasi Dokumen:*\n"
    )
    
    # Add metadata
    for key, value in metadata.items():
        response += f"• {escape_markdown_v2(key)}: {escape_markdown_v2(str(value))}\n"
    
    # Add analysis with proper formatting
    response += f"\n*Analisis:*\n\n{escape_markdown_v2(analysis)}"
    
    # Add emotional touch
    response += f"\n\n[menutup dokumen sambil tersenyum]\n\n"
    response += f"Ini hasil analisis Alya untuk {escape_markdown_v2(username)}\\-kun\\! ✨"
    
    return response

def format_image_response(analysis: str, username: str, image_info: Dict[str, str]) -> str:
    """Format image analysis with persona touch."""
    response = (
        f"[mengamati gambar dengan seksama]\n\n"
        f"📸 *HASIL ANALISIS GAMBAR*\n\n"
        f"*Informasi Gambar:*\n"
    )
    
    # Add image metadata
    for key, value in image_info.items():
        response += f"• {escape_markdown_v2(key)}: {escape_markdown_v2(str(value))}\n"
    
    # Add analysis with proper escape
    response += f"\n*Analisis:*\n\n{escape_markdown_v2(analysis)}"
    
    # Add emotional touch
    response += f"\n\n[selesai menganalisis dengan puas]\n\n"
    response += f"Bagaimana menurut {escape_markdown_v2(username)}\\-kun\\? ✨"
    
    return response

def get_image_metadata(file_path: str) -> Dict[str, str]:
    """Get image metadata like dimensions, format etc."""
    from PIL import Image
    
    try:
        with Image.open(file_path) as img:
            return {
                "Dimensi": f"{img.width}x{img.height} px",
                "Format": img.format or "Unknown",
                "Mode": img.mode
            }
    except Exception as e:
        logger.error(f"Error handling document callback: {e}")
        try:
            await callback_query.answer("Error processing request", show_alert=True)
        except Exception:
            pass

"""
Document and Image Analysis Handlers.

This module handles document analysis, OCR, and image processing
using Google Gemini API with proper error handling and retries.
"""

import logging
import asyncio
import os
import re
from typing import Optional, Dict, Any, Union

from google.generativeai import GenerativeModel
import PIL.Image

from core.models import convert_safety_settings, get_current_gemini_key
from config.settings import DEFAULT_MODEL, IMAGE_MODEL

logger = logging.getLogger(__name__)

async def analyze_with_gemini_api(
    content: Union[str, PIL.Image.Image],
    prompt: str,
    image_mode: bool = False,
    retry_count: int = 0
) -> str:
    """
    Generic analyzer using Gemini API with proper error handling.
    
    Args:
        content: Text content or PIL Image to analyze
        prompt: Analysis prompt
        image_mode: Whether to use image model
        retry_count: Number of retries attempted
        
    Returns:
        Analysis result text
        
    Raises:
        RuntimeError: If analysis fails after retries
    """
    try:
        current_key = get_current_gemini_key()
        model = genai.GenerativeModel(
            model_name=IMAGE_MODEL if image_mode else DEFAULT_MODEL,
            generation_config={
                "max_output_tokens": 1500,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40
            },
            safety_settings=convert_safety_settings()
        )
        
        response = await asyncio.to_thread(
            model.generate_content,
            [prompt, content] if image_mode else prompt
        )
        
        if not response or not response.text:
            raise RuntimeError("Empty response from Gemini")
            
        result = response.text
        return result[:4000]
        
    except Exception as e:
        if retry_count < 3 and any(x in str(e).lower() for x in ["quota", "rate", "429"]):
            logger.info(f"Retrying analysis after error: {e}")
            return await analyze_with_gemini_api(
                content=content,
                prompt=prompt,
                image_mode=image_mode,
                retry_count=retry_count + 1
            )
        raise

async def generate_document_analysis(text_content: str) -> str:
    """Generate analysis of document text using Gemini."""
    try:
        truncated_text = text_content[:8000] + "..." if len(text_content) > 8000 else text_content
            
        prompt = """
        Analisis dokumen berikut dengan detail dan rangkum dengan jelas:
        
        ```
        {text}
        ```
        """
        
        return await analyze_with_gemini_api(truncated_text, prompt.format(text=truncated_text))
        
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return f"<i>Tidak dapat menganalisis dokumen: {str(e)[:100]}...</i>"

async def generate_image_analysis(image_path: str, custom_prompt: Optional[str] = None) -> str:
    """Generate analysis of image using Gemini."""
    try:
        image = PIL.Image.open(image_path)
        default_prompt = """
        Analisis gambar ini dengan detail secara menyeluruh.
        Jelaskan apa yang kamu lihat, termasuk objek, warna, suasana, dan konteks.
        Berikan analisis yang lengkap namun ringkas.
        """
        
        return await analyze_with_gemini_api(
            content=image,
            prompt=custom_prompt or default_prompt,
            image_mode=True
        )
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return f"<i>Tidak dapat menganalisis gambar: {str(e)[:100]}...</i>"