"""
Google Lens helper functions.
Handles temporary image hosting and URL generation for Google Lens searches.
"""

import logging
import aiohttp
import tempfile
import os
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

async def get_image_url(photo_file) -> str:
    """
    Get shareable URL for an image to use with Google Lens.
    Currently using Telegraph API as temporary image host.
    
    Args:
        photo_file: Telegram photo file object
        
    Returns:
        Public URL of uploaded image
    """
    try:
        # Download image
        image_data = await photo_file.download_as_bytearray()
        
        # Optimize image
        with Image.open(BytesIO(image_data)) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Resize if too large
            if max(img.size) > 2000:
                img.thumbnail((2000, 2000))
                
            # Save optimized image
            output = BytesIO()
            img.save(output, format='JPEG', quality=85)
            image_data = output.getvalue()
        
        # Upload to Telegraph
        async with aiohttp.ClientSession() as session:
            # First get access token
            async with session.get('https://api.telegra.ph/createAccount', 
                params={'short_name': 'AliaBot'}) as resp:
                token_data = await resp.json()
                if not token_data.get('ok'):
                    raise Exception("Failed to get Telegraph token")
                token = token_data['result']['access_token']
            
            # Upload image
            files = {'file': ('image.jpg', image_data, 'image/jpeg')}
            async with session.post('https://telegra.ph/upload', data=files) as resp:
                upload_data = await resp.json()
                if not upload_data:
                    raise Exception("Failed to upload image")
                
                # Get image URL
                image_path = upload_data[0]['src']
                return f"https://telegra.ph{image_path}"
                
    except Exception as e:
        logger.error(f"Error getting image URL: {e}")
        return None

async def search_google_lens(image_url: str) -> str:
    """
    Generate Google Lens search URL for an image.
    
    Args:
        image_url: Public URL of the image to search
        
    Returns:
        Google Lens search URL
    """
    if not image_url:
        return None
        
    # Format Google Lens URL
    return f"https://lens.google.com/uploadbyurl?url={image_url}"
