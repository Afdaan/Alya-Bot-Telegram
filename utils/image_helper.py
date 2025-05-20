"""
Telegram Image Helper for Alya Bot.

This module provides utilities for downloading and processing 
images directly from Telegram messages.
"""

import os
import logging
import tempfile
from typing import Optional, Union
from telegram import Message, Bot, File

logger = logging.getLogger(__name__)

async def download_image(file_id: str, bot: Bot) -> Optional[str]:
    """
    Download an image from Telegram and save to a temporary file.
    
    Args:
        file_id: Telegram file ID
        bot: Telegram Bot instance
        
    Returns:
        Path to downloaded image or None if failed
    """
    try:
        new_file = await bot.get_file(file_id)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(temp_fd)
        
        await new_file.download_to_drive(temp_path)
        logger.debug(f"Downloaded image to {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None

async def get_image_from_message(message: Message) -> Optional[str]:
    """
    Extract image from various message types and download it.
    
    Args:
        message: Telegram Message object
        
    Returns:
        Path to downloaded image or None if no image found
    """
    if not message:
        return None
    
    try:
        bot = message.get_bot()
        file_id = None
        
        # Get file ID from different message types
        if message.photo:
            # Get largest photo
            file_id = message.photo[-1].file_id
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
            file_id = message.document.file_id
        elif message.animation:
            file_id = message.animation.file_id
            
        # Download if we have a file ID
        if file_id:
            return await download_image(file_id, bot)
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting image from message: {e}")
        return None

async def get_video_from_message(message: Message) -> Optional[str]:
    """
    Extract video from message and download it.
    
    Args:
        message: Telegram Message object
        
    Returns:
        Path to downloaded video or None if no video found
    """
    if not message:
        return None
        
    try:
        bot = message.get_bot()
        file_id = None
        
        # Get file ID from different message types
        if message.video:
            file_id = message.video.file_id
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('video/'):
            file_id = message.document.file_id
            
        # Download if we have a file ID
        if file_id:
            new_file = await bot.get_file(file_id)
            temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4')
            os.close(temp_fd)
            
            await new_file.download_to_drive(temp_path)
            return temp_path
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting video from message: {e}")
        return None
