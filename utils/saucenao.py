"""
SauceNAO API Handler for Alya Telegram Bot.

This module provides reverse image searching capabilities using SauceNAO API,
specifically targeted at anime, manga, and related artwork.
"""

import os
import logging
import aiohttp
from typing import List, Dict, Any, Optional
import json
import re

logger = logging.getLogger(__name__)

# Get API key from environment
SAUCENAO_API_KEY = os.getenv("SAUCENAO_API_KEY")
SAUCENAO_BASE_URL = "https://saucenao.com/search.php"

async def reverse_search_image(photo_file) -> List[Dict[str, Any]]:
    """
    Search for image source using SauceNAO API.
    
    Args:
        photo_file: Telegram photo file object
        
    Returns:
        List of results with title, similarity score, and source link
    """
    try:
        if not SAUCENAO_API_KEY:
            logger.error("SauceNAO API key is missing")
            return []
            
        # Download the photo file
        file_content = await photo_file.download_as_bytearray()
        
        # Prepare the API request
        params = {
            'api_key': SAUCENAO_API_KEY,
            'output_type': 2,  # JSON response
            'numres': 5  # Number of results
        }
        
        # Prepare the file for upload
        data = aiohttp.FormData()
        data.add_field('file', file_content, 
                      filename='image.png',
                      content_type='image/png')
        
        # Make the API request
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # FIX: Corrected variable name from SAUCENA_BASE_URL to SAUCENAO_BASE_URL
            async with session.post(SAUCENAO_BASE_URL, 
                                  data=data, 
                                  params=params) as response:
                                  
                if response.status != 200:
                    logger.error(f"SauceNAO API error: {response.status}")
                    return []
                    
                result_data = await response.json()
                
        # Process results
        results = []
        
        if 'results' not in result_data:
            logger.warning("No results in SauceNAO response")
            return []
            
        # Make sure results is actually a list
        sauce_results = result_data.get('results', [])
        if not isinstance(sauce_results, list):
            logger.error(f"Expected results to be list, got {type(sauce_results)}")
            return []
        
        # Process each result to extract useful information
        for result in sauce_results:
            try:
                # Extract header info
                header = result.get('header', {})
                similarity = float(header.get('similarity', 0))
                
                # Skip low similarity results
                if similarity < 50:
                    continue
                    
                # Extract source info based on data type
                data = result.get('data', {})
                
                # Determine title and source based on available fields
                title = (
                    data.get('title') or
                    data.get('source') or
                    data.get('created_at') or
                    data.get('jp_name') or
                    header.get('index_name', 'Unknown')
                )
                
                # Determine source
                source = (
                    data.get('source') or
                    data.get('author_name') or
                    data.get('member_name') or
                    data.get('creator') or
                    "Unknown Source"
                )
                
                # Find URL - check multiple possible locations
                url = None
                if 'ext_urls' in data and isinstance(data['ext_urls'], list) and len(data['ext_urls']) > 0:
                    url = data['ext_urls'][0]
                elif 'source_url' in data:
                    url = data['source_url']
                    
                # Clean up title and source
                title = _clean_text(title)
                source = _clean_text(source)
                
                results.append({
                    'title': title,
                    'similarity': similarity,
                    'source': source,
                    'url': url
                })
                
            except Exception as e:
                logger.error(f"Error processing SauceNAO result: {e}")
                continue
                
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Always return a list for consistency
        return results if results else []
        
    except Exception as e:
        logger.error(f"Error in reverse_search_image: {e}")
        return []

def _clean_text(text: str) -> str:
    """
    Clean and normalize text from SauceNAO results.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return "Unknown"
    
    # Convert to string if not already
    text = str(text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate if too long
    if len(text) > 50:
        text = text[:47] + "..."
    
    return text
