"""
SauceNAO Image Search Utility for Alya Telegram Bot.

This module provides functionality to perform reverse image searches
using the SauceNAO API, primarily for finding anime and manga sources.
"""

import os
import logging
import aiohttp
from typing import Dict, Any
import io

logger = logging.getLogger(__name__)

# =========================
# API Configuration
# =========================

API_BASE_URL = 'https://saucenao.com/search.php'
DEFAULT_NUM_RESULTS = 5
MIN_SIMILARITY_THRESHOLD = 65.0  # Minimum similarity percentage to consider a valid match

# =========================
# Main Functionality
# =========================

async def reverse_search_image(photo_file) -> dict:
    """
    Reverse image search using SauceNAO API.
    
    Args:
        photo_file: Telegram photo file object
        
    Returns:
        Dictionary containing search results or error information
    """
    try:
        # Validate API key
        api_key = os.getenv('SAUCENAO_API_KEY')
        if not api_key:
            raise ValueError("Missing SauceNAO API key")

        # Download image data from Telegram
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Prepare form data with image
        data = aiohttp.FormData()
        data.add_field(
            'file',
            io.BytesIO(photo_bytes),
            filename='image.png',
            content_type='image/png'
        )
        
        # API parameters
        params = {
            'api_key': api_key,
            'output_type': 2,  # JSON response
            'db': 999,         # All databases
            'numres': DEFAULT_NUM_RESULTS,
            'dedupe': 2,       # Deduplicate results
            'hide': 0          # Don't hide anything
        }

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(API_BASE_URL, params=params, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return process_saucenao_results(result)
                
                # Handle error response
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

# =========================
# Result Processing
# =========================

def process_saucenao_results(data: Dict[str, Any]) -> dict:
    """
    Process and format SauceNAO API results.
    
    Args:
        data: Raw API response data
        
    Returns:
        Processed results dictionary with success status
    """
    # Check if results exist
    if not data.get('results'):
        return {
            'success': False,
            'error': 'No results found'
        }

    # Process top results
    processed_results = []
    for result in data['results'][:3]:  # Get top 3 results
        similarity = float(result['header']['similarity'])
        
        # Only include results above the similarity threshold
        if similarity > MIN_SIMILARITY_THRESHOLD:
            processed_results.append({
                'similarity': similarity,
                'thumbnail': result['header'].get('thumbnail'),
                'source': result['data'].get('source') or result['data'].get('title'),
                'url': result['data'].get('ext_urls', ['No URL'])[0],
                'author': result['data'].get('creator') or result['data'].get('member_name'),
                'additional_info': result['data'].get('material') or result['data'].get('characters')
            })

    # Return formatted results
    return {
        'success': True,
        'results': processed_results
    }
