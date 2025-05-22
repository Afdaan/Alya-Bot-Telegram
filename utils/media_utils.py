"""Media Utilities for Alya Bot.

This module provides utilities for downloading and processing media files
from Telegram messages, including images and documents.
"""

import logging
import os
import re
import tempfile
from typing import Optional, Union, List, Dict, Any
from pathlib import Path

import pytesseract
from PIL import Image
from telegram import Message, Document, PhotoSize
from telegram.ext import CallbackContext  # Add this import
from telegram.error import TelegramError

from config.settings import (
    TEMP_DIR,
    MAX_IMAGE_SIZE,
    IMAGE_COMPRESS_QUALITY,
    MAX_DOCUMENT_SIZE,
    ALLOWED_DOCUMENT_TYPES,
    OCR_LANGUAGE
)

logger = logging.getLogger(__name__)


# Try to import optional dependencies
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Import image utilities to ensure no duplication
from utils.image_utils import get_file_hash as image_get_file_hash
from config.settings import OCR_LANGUAGE

logger = logging.getLogger(__name__)

# =========================
# Media File Processing
# =========================

async def get_document_text(file_path: str, file_ext: str) -> str:
    """
    Extract text from document file.
    
    Args:
        file_path: Path to document file
        file_ext: File extension
        
    Returns:
        Extracted text
    """
    try:
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None,
            _extract_text,
            file_path,
            file_ext
        )
        
        return text
    except Exception as e:
        logger.error(f"Error extracting document text: {e}")
        return f"Error extracting text: {str(e)[:100]}..."

def _extract_text(file_path: str, file_ext: str) -> str:
    """
    Extract text from document (sync function for executor).
    
    Args:
        file_path: Path to document file
        file_ext: File extension
        
    Returns:
        Extracted text
    """
    try:
        # Convert file extension to lowercase for consistency
        ext = file_ext.lower()
        
        # Determine extraction method based on file type
        if ext in ['txt', 'md', 'json', 'xml', 'html', 'htm', 'csv']:
            # Simple text file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        elif ext in ['pdf']:
            if PDF_AVAILABLE:
                text = []
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PdfReader(pdf_file)
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text.append(page.extract_text() or '')
                return '\n\n'.join(text)
            else:
                return "PyPDF2 library not installed. Cannot extract text from PDF."
                
        elif ext in ['doc', 'docx', 'odt', 'rtf', 'ppt', 'pptx']:
            if TEXTRACT_AVAILABLE:
                text = textract.process(file_path).decode('utf-8', errors='ignore')
                return text
            else:
                return "Textract library not installed. Cannot extract text from this document format."
            
        else:
            # Unsupported format
            return f"Unsupported document format: {ext}"
            
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return f"Error extracting text: {str(e)[:100]}..."

# =========================
# Media Type Detection
# =========================

def is_image_file(file_ext: str) -> bool:
    """
    Check if file extension belongs to image file.
    
    Args:
        file_ext: File extension
    
    Returns:
        True if file extension is an image type
    """
    return file_ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'tif']

def is_document_file(file_ext: str) -> bool:
    """
    Check if file extension belongs to document file.
    
    Args:
        file_ext: File extension
    
    Returns:
        True if file extension is a document type
    """
    return file_ext.lower() in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'ppt', 'pptx', 'md']

def is_video_file(file_ext: str) -> bool:
    """
    Check if file extension belongs to video file.
    
    Args:
        file_ext: File extension
    
    Returns:
        True if file extension is a video type
    """
    return file_ext.lower() in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm']

def is_audio_file(file_ext: str) -> bool:
    """
    Check if file extension belongs to audio file.
    
    Args:
        file_ext: File extension
    
    Returns:
        True if file extension is an audio type
    """
    return file_ext.lower() in ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac']

def get_file_hash(file_path: str) -> str:
    """
    Generate hash from file for caching.
    
    Args:
        file_path: Path to file
    
    Returns:
        MD5 hash of the file
    """
    # Use the implementation from image_utils to avoid duplication
    return image_get_file_hash(file_path)

def get_content_type(file_ext: str) -> str:
    """
    Determine content type from file extension.
    
    Args:
        file_ext: File extension
    
    Returns:
        Content type category
    """
    ext = file_ext.lower()
    
    if is_image_file(ext):
        return "image"
    elif is_document_file(ext):
        return "document"
    elif is_video_file(ext):
        return "video"
    elif is_audio_file(ext):
        return "audio"
    else:
        return "unknown"

# =========================
# File Handling
# =========================

def get_filename_from_path(file_path: str) -> str:
    """
    Extract filename from path.
    
    Args:
        file_path: File path
    
    Returns:
        Filename without directory
    """
    return os.path.basename(file_path)

def get_extension(file_path: str) -> str:
    """
    Get file extension from path.
    
    Args:
        file_path: Path to file
    
    Returns:
        File extension without dot
    """
    _, ext = os.path.splitext(file_path)
    return ext[1:] if ext.startswith('.') else ext

def create_temp_copy(file_path: str, prefix: str = "alya_") -> Optional[str]:
    """
    Create temporary copy of file.
    
    Args:
        file_path: Source file path
        prefix: Prefix for temp file
    
    Returns:
        Path to temp file or None if error
    """
    try:
        ext = get_extension(file_path)
        temp_fd, temp_path = tempfile.mkstemp(suffix=f'.{ext}', prefix=prefix)
        os.close(temp_fd)
        
        with open(file_path, 'rb') as src_file, open(temp_path, 'wb') as dst_file:
            dst_file.write(src_file.read())
            
        return temp_path
    except Exception as e:
        logger.error(f"Error creating temp copy: {e}")
        return None

async def extract_text_from_document(file_path: str, mime_type: str) -> str:
    """
    Extract text from a document file.

    Args:
        file_path: Path to the document file
        mime_type: MIME type of the document
        
    Returns:
        str: Extracted text from the document or error message
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return "Error: File not found"
            
        # Determine extraction method based on mime type
        if mime_type == 'application/pdf':
            if not PDF_AVAILABLE:
                return "PyPDF2 library not installed. Cannot extract text from PDF."
                
            text = []
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text() or ''
                    text.append(page_text)
            
            extracted_text = '\n\n'.join(text)
        
        elif 'word' in mime_type:
            if not TEXTRACT_AVAILABLE:
                return "Textract library not installed. Cannot extract text from Word document."
                
            extracted_text = textract.process(file_path).decode('utf-8', errors='ignore')
            
        elif mime_type in ['text/plain', 'text/markdown', 'text/csv', 'text/html']:
            # Simple text file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                extracted_text = f.read()
                
        else:
            # Try generic extraction
            if TEXTRACT_AVAILABLE:
                try:
                    extracted_text = textract.process(file_path).decode('utf-8', errors='ignore')
                except:
                    return f"Unsupported document format: {mime_type}"
            else:
                return f"Cannot extract text from {mime_type} without textract library."
                
        return extracted_text
    except Exception as e:
        logger.error(f"Error extracting text from document: {e}")
        return f"Error extracting text: {str(e)}"

def extract_text_from_image(image_path: str, language: str = OCR_LANGUAGE) -> Dict[str, Any]:
    """
    Extract text from an image using OCR.
    
    Args:
        image_path: Path to image file
        language: OCR language (default from settings)
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return {"error": "Image file not found"}
        
    result = {
        "text": "",
        "language": language,
        "confidence": 0.0,
        "success": False,
        "word_count": 0
    }
    
    # Check if OCR is available
    if not OCR_AVAILABLE:
        logger.warning("OCR functionality requires pytesseract package")
        result["error"] = "OCR functionality requires pytesseract package"
        return result
    
    try:
        # Open image
        img = Image.open(image_path)
        
        # Perform OCR
        ocr_config = f'--oem 3 --psm 6 -l {language}'
        ocr_data = pytesseract.image_to_data(img, config=ocr_config, output_type=pytesseract.Output.DICT)
        
        # Extract text
        extracted_text = pytesseract.image_to_string(img, config=ocr_config)
        
        # Clean up text
        extracted_text = extracted_text.strip()
        
        # Calculate confidence
        conf_values = [int(conf) for conf in ocr_data['conf'] if conf != '-1']
        avg_confidence = sum(conf_values) / len(conf_values) if conf_values else 0.0
        
        # Populate result
        result["text"] = extracted_text
        result["confidence"] = avg_confidence / 100.0  # Convert to 0-1 range
        result["success"] = bool(extracted_text)
        result["word_count"] = len(extracted_text.split())
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}")
        result["error"] = str(e)
        return result

async def compress_image(image_path: str, quality: int = 85) -> Optional[str]:
    """
    Compress image to reduce size while maintaining readability.
    
    Args:
        image_path: Path to image file
        quality: JPEG quality level (1-100)
        
    Returns:
        Path to compressed image or None if error
    """
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None
    
    try:
        # Check if PIL is available
        if 'PIL' not in globals() and Image is None:
            logger.warning("PIL not available. Cannot compress image.")
            return image_path
            
        # Create output filename
        filename, ext = os.path.splitext(image_path)
        output_path = f"{filename}_compressed{ext}"
        
        # Open image
        img = Image.open(image_path)
        
        # Save with compression
        img.save(output_path, optimize=True, quality=quality)
        
        # Return compressed path only if file size was reduced
        original_size = os.path.getsize(image_path)
        compressed_size = os.path.getsize(output_path)
        
        if compressed_size < original_size:
            return output_path
        else:
            # Remove compressed file and return original if no size reduction
            os.remove(output_path)
            return image_path
            
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return image_path  # Return original on error


async def download_media(
    message: Message,
    context: Optional[CallbackContext] = None,  # Make context optional
    allowed_types: Optional[List[str]] = None,
    max_size: int = MAX_DOCUMENT_SIZE,
    temp_dir: Union[str, Path] = TEMP_DIR
) -> Optional[str]:
    """Download media from Telegram message safely.
    
    Args:
        message: Telegram message containing media
        context: Optional callback context
        allowed_types: List of allowed mime types
        max_size: Maximum file size in bytes
        temp_dir: Directory for temporary files

    Returns:
        Path to downloaded file or None if failed
    """
    try:
        # Get file object
        if message.document:
            file = message.document
            mime_type = file.mime_type
            if allowed_types and mime_type not in allowed_types:
                logger.warning(f"Invalid mime type: {mime_type}")
                return None
        elif message.photo:
            file = message.photo[-1]  # Get largest photo
        else:
            logger.warning("No media found in message")
            return None

        # Check file size safely - fix NoneType comparison issue
        if max_size and hasattr(file, 'file_size') and file.file_size:
            if int(file.file_size) > int(max_size):
                logger.warning(f"File too large: {file.file_size} bytes > {max_size} bytes")
                return None

        # Create temp file path
        temp_path = Path(temp_dir) / f"media_{message.message_id}"
        
        # Get bot instance - try context first, then message
        bot = context.bot if context else message.bot
        if not bot:
            raise ValueError("No bot instance available")

        # Download file
        file_obj = await bot.get_file(file.file_id)
        await file_obj.download_to_drive(str(temp_path))

        # Verify download
        if not os.path.exists(temp_path):
            raise FileNotFoundError("Downloaded file not found")

        return str(temp_path)

    except TelegramError as e:
        logger.error(f"Telegram error downloading media: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None

async def extract_text_from_document(file_path: str) -> Optional[str]:
    """
    Extract text from document using OCR.

    Args:
        file_path: Path to document file

    Returns:
        Extracted text or None if failed
    """
    try:
        # Handle image files with OCR
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang=OCR_LANGUAGE)
            return text.strip()

        # Handle PDF files (requires pdf2image)
        elif file_path.lower().endswith('.pdf'):
            from pdf2image import convert_from_path
            
            pages = convert_from_path(file_path)
            text_parts = []
            
            for page in pages:
                text = pytesseract.image_to_string(page, lang=OCR_LANGUAGE)
                text_parts.append(text.strip())
                
            return "\n\n".join(text_parts)

        # Handle text files directly
        elif file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()

        else:
            logger.warning(f"Unsupported file type for text extraction: {file_path}")
            return None

    except Exception as e:
        logger.error(f"Error extracting text from document: {e}")
        return None

def get_image_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get image metadata like dimensions, format etc.

    Args:
        file_path: Path to image file

    Returns:
        Dictionary of image metadata
    """
    try:
        with Image.open(file_path) as img:
            return {
                "Dimensi": f"{img.width}x{img.height} px",
                "Format": img.format or "Unknown",
                "Mode": img.mode,
                "Size": os.path.getsize(file_path) // 1024  # KB
            }
    except Exception as e:
        logger.error(f"Error getting image metadata: {e}")
        return {
            "Error": "Could not read image metadata"
        }

def cleanup_temp_file(file_path: Optional[str]) -> None:
    """
    Clean up temporary file safely.

    Args:
        file_path: Path to file to delete
    """
    if not file_path:
        return
        
    try:
        os.unlink(file_path)
    except Exception as e:
        logger.warning(f"Error cleaning up temp file {file_path}: {e}")
