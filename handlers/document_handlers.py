"""
Document and Image Handlers for Alya Telegram Bot.

This module provides handlers for processing documents and images,
including analysis with Gemini and reverse image search functionality.
"""

# =============================
# Imports
# =============================
# Standard library
import logging
import asyncio
import tempfile
import re
import os
import traceback
import hashlib
from io import BytesIO

# Third-party libraries
import aiohttp
import json
from PIL import Image
import textract
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import CallbackContext, ConversationHandler

# Local imports
from config.settings import ANALYZE_PREFIX, SAUCE_PREFIX, SAUCENAO_API_KEY
from core import models
from core.models import chat_model
from utils.formatters import format_markdown_response
from utils.cache_manager import response_cache
from utils.saucenao import search_with_saucenao

# =============================
# Logger Configuration
# =============================
logger = logging.getLogger(__name__)

# =============================
# Helper Functions
# =============================
def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return re.sub(r"([_*\[\]()~`>#+=|{}.!-])", r"\\\1", text)

async def download_image(file_id, context):
    """Download an image from Telegram and save to a temporary file."""
    try:
        new_file = await context.bot.get_file(file_id)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        await new_file.download_to_drive(temp_file.name)
        return temp_file.name
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None

async def get_image_from_message(message: Message):
    """Extract image from various message types and download it."""
    if not message:
        return None
    
    try:
        bot = message.get_bot()
        
        if message.photo:
            # Get largest photo
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
            file = await bot.get_file(message.document.file_id)
            
        elif message.animation:
            file = await bot.get_file(message.animation.file_id)
            
        else:
            return None
            
        # Buat nama file unik berdasarkan file_id dan waktu
        file_id_hash = hashlib.md5(file.file_id.encode()).hexdigest()[:10]
        
        # Download file to temporary location - PENTING: delete=False agar file tidak langsung dihapus
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{file_id_hash}.jpg')
        await file.download_to_drive(temp_file.name)
        return temp_file.name
        
    except AttributeError as e:
        logger.error(f"Invalid message object: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None

def get_image_hash(image_path):
    """Generate hash from image file for caching."""
    with open(image_path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
    return file_hash.hexdigest()

# Add this helper function to determine file type
def is_image_file(file_ext):
    """Check if file extension belongs to image file."""
    return file_ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'webp']

# =============================
# Main Document Handler
# =============================
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
            await handle_sauce_command(update, context)
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

# =============================
# Sauce Command Handler
# =============================
async def handle_sauce_command(update, context: CallbackContext = None) -> None:
    """Handle the !sauce command to search for image sources using SauceNAO."""
    # Perbaikan untuk menerima parameter berupa Message atau Update
    if hasattr(update, 'message'):
        # Jika parameter adalah Update object
        msg = update.message
    else:
        # Jika parameter adalah Message object langsung
        msg = update
    
    # tentukan sumber gambar: langsung di msg atau via reply
    if msg.photo or (msg.document and msg.document.mime_type and msg.document.mime_type.startswith('image/')):
        sauce_message = msg
    elif msg.reply_to_message and (
        msg.reply_to_message.photo or 
        (msg.reply_to_message.document and 
         msg.reply_to_message.document.mime_type and 
         msg.reply_to_message.document.mime_type.startswith('image/'))
    ):
        sauce_message = msg.reply_to_message
    else:
        await msg.reply_text("Balas pesan dengan gambar atau kirim gambar dengan caption !sauce untuk mencari sumbernya! 🔍")
        return

    # Konfirmasi pencarian dengan processing message
    processing_message = await msg.reply_text(
        "*Alya-chan* akan mencari sumber gambar menggunakan SauceNAO...\n"
        "Tunggu sebentar ya~ 🔍",
        parse_mode='Markdown'
    )
    
    # Mulai pencarian gambar
    image_path = None
    try:
        # Download gambar - perbaikan disini, simpan file dan pastikan path valid
        image_path = await get_image_from_message(sauce_message)
        
        if not image_path or not os.path.exists(image_path):
            await processing_message.edit_text("Gomennasai! Alya tidak dapat mengunduh gambarnya... 🥺")
            return
        
        # Ubah pesan processing
        await processing_message.edit_text("Mencari sumber gambar dengan SauceNAO... 🔍")
        
        # Panggil SauceNAO API dan perbarui pesan dengan hasilnya
        await search_with_saucenao(processing_message, image_path)
        
    except Exception as e:
        logger.error(f"Error in sauce search: {e}\n{traceback.format_exc()}")
        await processing_message.edit_text(f"Gomennasai! Terjadi kesalahan: {str(e)[:100]}... 😔")
    
    finally:
        # Hapus file temporary
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {e}")

# =============================
# Trace Command Handler
# =============================
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
    
    # Make sure we escape any potential dots in the username
    escaped_username = user.first_name.replace('.', '\\.').replace('-', '\\-')
    
    await message.reply_text(
        f"*Alya\\-chan* akan menganalisis {type_text} dari {escaped_username}\\-kun\\~ ✨\n",
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
        
        # Make sure to properly escape the entire error message for Markdown
        error_str = str(e)
        for char in ['.', '-', '(', ')', '[', ']', '~', '>', '#', '+', '=', '{', '}', '!', '|', '`']:
            error_str = error_str.replace(char, f'\\{char}')
            
        # Also escape the username
        escaped_username = user.first_name.replace('.', '\\.').replace('-', '\\-')
        
        await message.reply_text(
            f"*Gomenasai {escaped_username}\\-kun\\~* 😔\n\nAlya tidak bisa menganalisis file ini\\. Error: {error_str}",
            parse_mode='MarkdownV2'
        )

# =============================
# File Processing
# =============================
async def process_file(message, user, file, file_ext):
    """Process downloaded file for analysis with caching for efficiency."""
    with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}') as temp_file:
        await file.download_to_drive(temp_file.name)
        
        try:
            # Handle image files with Gemini Vision & caching
            if is_image_file(file_ext):
                # Generate hash untuk cek cache
                image_hash = get_image_hash(temp_file.name)
                cache_key = f"img_analysis_{image_hash}"
                
                # Cek cache dulu
                cached_response = response_cache.get(cache_key)
                if (cached_response):
                    return await send_analysis_response(message, user, cached_response)
                
                # Jika tidak ada di cache, proses normal
                image = Image.open(temp_file.name)
                
                # Compress image untuk hemat token jika terlalu besar
                MAX_SIZE = (800, 800)
                if max(image.size) > MAX_SIZE[0]:
                    image.thumbnail(MAX_SIZE)
                
                # Gunakan model yang lebih andal dan ganti ke mode safety yang lebih lenient
                model = genai.GenerativeModel(
                    'gemini-2.0-flash',
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                    ]
                )
                
                # Minimalkan prompt untuk gambar
                image_prompt = """
                Please analyze this image briefly. 
                Describe what you see in the image in a friendly, cute way.
                Be brief (maximum 500 characters).
                """
                
                # Retry Gemini analysis
                max_attempts = 3
                response_text = None
                
                for attempt in range(max_attempts):
                    try:
                        response = model.generate_content([image_prompt, image], stream=False)
                        response_text = response.text
                        response_cache.set(cache_key, response_text)
                        break
                    except asyncio.TimeoutError:
                        logger.warning(f"Response timeout for image analysis (attempt {attempt+1}/{max_attempts})")
                        if attempt == max_attempts - 1:
                            response_text = f"Gomennasai~ Alya butuh waktu lebih lama untuk menganalisis gambar ini 🥺💕."
                    except Exception as img_error:
                        logger.error(f"Error analyzing image (attempt {attempt+1}/{max_attempts}): {img_error}")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(1)
                        else:
                            response_text = f"Alya-chan melihat ada gambar tapi servernya sibuk. Sepertinya ini {file_ext} ya~ 🌸"
                
                if not response_text:
                    response_text = f"Alya mengalami error saat memproses gambar! Maaf ya 🥺💕."
            
            # Handle document files with text extraction + caching
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

                PENTING: JANGAN gunakan format kode (``` atau ` ) dalam responmu karena akan menyebahkan error.
                Gunakan format * untuk bold dan _ untuk italic saja bila perlu.
                Jangan lebih dari 800 karakter. Jadikan singkat dan efektif.
                Isi dokumen:
                {content[:4000]}
                """
                
                chat = chat_model.start_chat(history=[])
                response = chat.send_message(doc_prompt)
                response_text = response.text

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            response_text = f"Alya-chan mengalami kesulitan memproses file ini. Mohon maaf {user.first_name}-kun, Alya akan berusaha lebih baik lagi nanti~ 🌸"
        
        # Format and send the response
        return await send_analysis_response(message, user, response_text)


# ===============================
# Response Formatting
# ===============================
async def send_analysis_response(message, user, response_text):
    """
    Format and send analysis response, handling lengthy responses.
    """
    try:
        formatted_response = format_markdown_response(response_text)
        escaped_username = user.first_name.replace('.', '\\.').replace('-', '\\-')
        
        if len(formatted_response) > 4000:
            parts = [formatted_response[i:i+4000] for i in range(0, len(formatted_response), 4000)]
            header = (
                f"*Rangkuman dari Alya\\-chan untuk {escaped_username}\\-kun* 💕\n\n"
                f"_{len(parts)} bagian rangkuman akan dikirim\\~_ 📝\n\n"
            )
            
            for i, part in enumerate(parts):
                section_header = f"*Bagian {i+1} dari {len(parts)}* 📚\n\n" if i > 0 else header
                await message.reply_text(
                    section_header + part,
                    reply_to_message_id=message.message_id if i == 0 else None,
                    parse_mode='MarkdownV2'
                )
                await asyncio.sleep(1)
        else:
            header = f"*Rangkuman dari Alya\\-chan untuk {escaped_username}\\-kun* 💕\n\n"
            await message.reply_text(
                header + formatted_response,
                reply_to_message_id=message.message_id,
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        # Log error dan kirim pesan friendly
        logger.error(f"Error formatting response: {e}")
        err_msg = (
            "Alya-chan error waktu format/mengirim pesan rangkuman 😵‍💫\n"
            f"Detail: {str(e)[:300]}\n"
            "Coba ulangi lagi nanti ya~"
        )
        await message.reply_text(err_msg)