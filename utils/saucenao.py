import os
import logging
import aiohttp
from typing import Dict, Any
import io

logger = logging.getLogger(__name__)

async def reverse_search_image(photo_file) -> dict:
    """Reverse image search using SauceNAO API."""
    try:
        api_key = os.getenv('SAUCENAO_API_KEY')
        if not api_key:
            raise ValueError("Missing SauceNAO API key")

        # Correctly download image data from Telegram
        photo_bytes = await photo_file.download_as_bytearray()
        
        # API configuration
        url = 'https://saucenao.com/search.php'
        data = aiohttp.FormData()
        data.add_field(
            'file',
            io.BytesIO(photo_bytes),
            filename='image.png',
            content_type='image/png'
        )
        
        params = {
            'api_key': api_key,
            'output_type': 2,
            'db': 999,
            'numres': 5,
            'dedupe': 2,
            'hide': 0
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return process_saucenao_results(result)
                return {
                    'success': False,
                    'error': f"API Error: {response.status}"
                }

    except Exception as e:
        logger.error(f"Reverse search error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def process_saucenao_results(data: Dict[str, Any]) -> dict:
    """Process and format SauceNAO API results."""
    if not data.get('results'):
        return {
            'success': False,
            'error': 'No results found'
        }

    processed_results = []
    for result in data['results'][:3]:  # Get top 3 results
        similarity = float(result['header']['similarity'])  # Convert to float
        if similarity > 65.0:  # Now comparing float to float
            processed_results.append({
                'similarity': similarity,  # Store as float
                'thumbnail': result['header'].get('thumbnail'),
                'source': result['data'].get('source') or result['data'].get('title'),
                'url': result['data'].get('ext_urls', ['No URL'])[0],
                'author': result['data'].get('creator') or result['data'].get('member_name'),
                'additional_info': result['data'].get('material') or result['data'].get('characters')
            })

    return {
        'success': True,
        'results': processed_results
    }
