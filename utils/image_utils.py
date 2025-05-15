import aiohttp
import logging
import random

logger = logging.getLogger(__name__)

# Common modern user agents for better compatibility
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0",
]

async def download_image(url: str) -> bytes:
    """Download image from URL with better error handling and user agent rotation."""
    try:
        async with aiohttp.ClientSession() as session:
            # Add robust headers
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'image/webp,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache'
            }
            
            async with session.get(url, 
                                 headers=headers, 
                                 timeout=30,
                                 ssl=False) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to download image. Status: {response.status}")
                    raise Exception(f"HTTP {response.status}")
                    
    except Exception as e:
        logger.error(f"Image download error: {str(e)}")
        return None