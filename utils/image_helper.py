import os
import logging
import tempfile
from telegram import Message

logger = logging.getLogger(__name__)

async def download_image(file_id, context):
    """Download an image from Telegram and save to a temporary file"""
    try:
        new_file = await context.bot.get_file(file_id)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        await new_file.download_to_drive(temp_file.name)
        return temp_file.name
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None

async def get_image_from_message(message: Message):
    """Extract image from various message types and download it"""
    if not message:
        return None
        
    if message.photo:
        # Get largest photo
        photo = message.photo[-1]
        return await download_image(photo.file_id, message.get_bot())
        
    elif message.document and message.document.mime_type.startswith('image/'):
        return await download_image(message.document.file_id, message.get_bot())
        
    elif message.animation:
        return await download_image(message.animation.file_id, message.get_bot())
        
    return None
