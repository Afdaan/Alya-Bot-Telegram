"""
Document and Image Handlers for Alya Telegram Bot.

This module provides handlers for processing documents and images,
including analysis with Gemini and reverse image search functionality.
"""

import logging
import asyncio
import tempfile
from io import BytesIO
from PIL import Image
import textract
import google.generativeai as genai

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from config.settings import ANALYZE_PREFIX, SAUCE_PREFIX

from core.models import chat_model
from utils.formatters import format_markdown_response
from utils.saucenao import reverse_search_image

logger = logging.getLogger(__name__)

# =========================
# Main Document Handler
# =========================

async def handle_document_image(update: Update, context: CallbackContext) -> None:
    """
    Handle document and image analysis requests.
    
    Processes incoming photos and documents with appropriate analysis
    based on caption prefixes or chat type.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    try:
        message = update.message
        user = update.effective_user
        
        if not message:
            return
            
        # Check command type from caption
        caption = message.caption or ""
        is_sauce = caption.startswith(SAUCE_PREFIX)
        is_trace = caption.startswith(ANALYZE_PREFIX)
        
        # Sauce command: Find source of image using SauceNAO
        if message.photo and is_sauce:
            await handle_sauce_command(message, user)
            return
            
        # Trace command: Analyze image/document content using Gemini
        if (message.photo or message.document) and (is_trace or message.chat.type == "private"):
            await handle_trace_command(message, user)
            return

    except Exception as e:
        logger.error(f"Error processing document/image: {e}")
        await message.reply_text(
            "Gomen ne\\~ Alya kesulitan memproses file ini\\. \\. \\. 🥺",
            parse_mode='MarkdownV2'
        )

# =========================
# Sauce Command Handler
# =========================

async def handle_sauce_command(message, user):
    """
    Handle reverse image search command.
    
    Provides options for finding the source of an image using
    either SauceNAO (for anime) or Google Lens (for general images).
    
    Args:
        message: Telegram message with image
        user: User who sent the message
    """
    if not message.photo:
        await message.reply_text(
            "Gomen ne\\~ Alya butuh gambar untuk dicari sumbernya\\. \\. \\. 🥺",
            parse_mode='MarkdownV2'
        )
        return

    # Create buttons for search options
    keyboard = [
        [
            InlineKeyboardButton("🔍 SauceNAO (Anime)", callback_data=f"sauce_anime"),
            InlineKeyboardButton("🔎 Google Lens", callback_data=f"sauce_lens")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send response with search options
    await message.reply_text(
        f"*{user.first_name}\\-kun\\~* Alya\\-chan akan bantu cari sumber gambarnya\\!\n\n"
        "• *SauceNAO* \\- Untuk anime/manga/fanart\n"
        "• *Google Lens* \\- Untuk gambar umum\n\n"
        "_Pilih metode pencarian ya\\~_ ✨",
        reply_markup=reply_markup,
        reply_to_message_id=message.message_id,
        parse_mode='MarkdownV2'
    )

# =========================
# Trace Command Handler
# =========================

async def handle_trace_command(message, user):
    """
    Handle document/image analysis with Gemini.
    
    Processes images or documents and generates analysis using
    the appropriate model.
    
    Args:
        message: Telegram message with image/document
        user: User who sent the message
    """
    # Inform user that analysis is starting
    type_text = "gambar" if message.photo else "dokumen"
    await message.reply_text(
        f"*Alya\\-chan* akan menganalisis {type_text} dari {user.first_name}\\-kun\\~ ✨\n",
        parse_mode='MarkdownV2'
    )
    
    try:
        # Process photos with validation
        if message.photo:
            is_private = message.chat.type == "private"
            has_valid_caption = message.caption and message.caption.startswith(ANALYZE_PREFIX)
            
            # Skip if not private chat and no valid caption
            if not (is_private or has_valid_caption):
                return
                
            # Get analysis instructions from caption if any
            analysis_prompt = ""
            if message.caption:
                analysis_prompt = message.caption.replace(ANALYZE_PREFIX, "", 1).strip()
                
            file = await message.photo[-1].get_file()
            file_ext = "jpg"
            
        # Process documents with validation
        elif message.document:
            if not (message.caption and message.caption.startswith(ANALYZE_PREFIX)):
                return
                
            file = await message.document.get_file()
            file_ext = message.document.file_name.split('.')[-1].lower()
        else:
            return

        # Process the file based on type
        await process_file(message, user, file, file_ext)
        
    except Exception as e:
        logger.error(f"Error in trace command: {e}")
        await message.reply_text(
            f"*Gomenasai {user.first_name}\\-kun\\~* 😔\n\nAlya tidak bisa menganalisis file ini\\. Error: {str(e)}",
            parse_mode='MarkdownV2'
        )

# =========================
# File Processing
# =========================

async def process_file(message, user, file, file_ext):
    """
    Process downloaded file for analysis.
    
    Handles different file types (images, documents) and generates
    appropriate analysis using AI models.
    
    Args:
        message: Original Telegram message
        user: User who sent the message
        file: Downloaded Telegram file
        file_ext: File extension
    """
    with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}') as temp_file:
        await file.download_to_drive(temp_file.name)
        
        # Handle image files with Gemini Vision
        if file_ext in ['jpg', 'jpeg', 'png']:
            image = Image.open(temp_file.name)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            image_prompt = f"""
            Sebagai Alya-chan, tolong analisis gambar ini dengan detail ya!
            Berikan penjelasan dengan gaya yang manis dan mudah dimengerti~
            User: {user.first_name}-kun

            Format output yang diinginkan:
            1. Deskripsi umum gambar
            2. Detail penting yang terlihat
            3. Kesimpulan atau insight
            """
            
            response = model.generate_content([image_prompt, image])
        
        # Handle document files with text extraction
        else:
            # Try to extract text from document
            try:
                content = textract.process(temp_file.name).decode('utf-8')
            except Exception as e:
                logger.error(f"Textract error: {e}")
                content = None
                
                # Try multiple encodings if initial extraction fails
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        with open(temp_file.name, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue

            # Handle case where no text could be extracted
            if not content:
                raise ValueError("Tidak bisa membaca isi dokumen")
            
            # Generate document summary
            doc_prompt = f"""
            Alya-chan akan merangkum dokumen ini untuk {user.first_name}-kun dengan format yang rapi~!

            Format rangkuman yang diinginkan:
            1. Judul atau Topik Utama
            2. Poin-poin Penting (3-5 poin)
            3. Ringkasan Singkat
            4. Kesimpulan

            Gunakan emoji yang sesuai dan bahas dengan gaya yang manis~!
            
            Isi dokumen:
            {content[:4000]}
            """
            
            chat = chat_model.start_chat(history=[])
            response = chat.send_message(doc_prompt)

    # Format and send the response
    await send_analysis_response(message, user, response.text)

# =========================
# Response Formatting
# =========================

async def send_analysis_response(message, user, response_text):
    """
    Format and send analysis response, handling lengthy responses.
    
    Args:
        message: Original Telegram message
        user: User who sent the message
        response_text: Analysis text to send
    """
    # Format response for Markdown
    formatted_response = format_markdown_response(response_text)
    
    # Split and send if response is too long
    if len(formatted_response) > 4000:
        parts = [formatted_response[i:i+4000] for i in range(0, len(formatted_response), 4000)]
        header = (
            f"*Rangkuman dari Alya\\-chan untuk {user.first_name}\\-kun* 💕\n\n"
            f"_{len(parts)} bagian rangkuman akan dikirim\\~_ 📝\n\n"
        )
        
        for i, part in enumerate(parts):
            section_header = f"*Bagian {i+1} dari {len(parts)}* 📚\n\n" if i > 0 else header
            await message.reply_text(
                section_header + part,
                reply_to_message_id=message.message_id if i == 0 else None,
                parse_mode='MarkdownV2'
            )
            await asyncio.sleep(1)  # Delay to prevent flood
    else:
        # Send as a single message if not too long
        header = f"*Rangkuman dari Alya\\-chan untuk {user.first_name}\\-kun* 💕\n\n"
        await message.reply_text(
            header + formatted_response,
            reply_to_message_id=message.message_id,
            parse_mode='MarkdownV2'
        )