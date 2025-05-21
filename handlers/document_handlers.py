"""
Document and Image Handler for Alya Telegram Bot.

This module processes document and image messages, providing analysis,
text extraction, and source searching capabilities.
"""
import logging
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

    message = update.message
    user = update.effective_user
    temp_file = None
    
    try:
        # Show typing action
        await message.chat.send_action(ChatAction.TYPING)
        
        # Download media with context
        temp_file = await download_media(
            message=message,
            context=context,  # Pass context here
            allowed_types=None,
            max_size=None
        )
        
        if not temp_file:
            await message.reply_text(
                f"Maaf {escape_markdown_v2(user.first_name)}\\-kun, file tidak bisa diproses\\.\\.\\. 😔",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        # Generate analysis
        analysis = await generate_image_analysis(temp_file)
        
        # Format and send response
        response = format_markdown_response(analysis)
        await message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

    except Exception as e:
        logger.error(f"Error processing media: {e}")
        error_msg = str(e)[:100].replace('-', '\\-')  # Escape hyphens
        await message.reply_text(
            f"Maaf {escape_markdown_v2(user.first_name)}\\-kun, terjadi error: {escape_markdown_v2(error_msg)}\\.\\.\\. 😔",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    finally:
        # Safe cleanup
        if temp_file:
            cleanup_temp_file(temp_file)

async def handle_document(message: Message, user: User, file_path: str, context: CallbackContext) -> None:
    """Handle document analysis with text extraction."""
    try:
        # Extract text from document
        extracted_text = await extract_text_from_document(file_path)
        
        if not extracted_text:
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
        logger.error(f"Error analyzing document: {e}")
        raise

async def handle_image(message: Message, user: User, file_path: str, context: CallbackContext) -> None:
    """Handle image analysis with persona-driven responses."""
    try:
        # Generate analysis
        analysis = await generate_image_analysis(file_path)
        
        # Format response
        response = format_image_response(
            analysis=analysis,
            username=user.first_name,
            image_info=get_image_metadata(file_path)
        )
        
        await message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
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
        logger.error(f"Error getting image metadata: {e}")
        return {
            "Info": "Tidak dapat membaca metadata"
        }

# Bridge handlers for commands
async def handle_trace_command(update: Update, context: CallbackContext) -> None:
    """Bridge handler for trace command."""
    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text(
            "Reply ke gambar yang mau dianalisis ya\\! 🤗",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
        
    # Pass to main handler
    update.message = update.message.reply_to_message
    await handle_document_image(update, context)

async def handle_sauce_command(update: Update, context: CallbackContext) -> None:
    """Bridge handler for sauce command."""
    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text(
            "Reply ke gambar yang mau dicari sumbernya ya\\! 🤗",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
        
    # Pass to main handler with sauce flag
    update.message = update.message.reply_to_message
    context.user_data['sauce_search'] = True
    await handle_document_image(update, context)