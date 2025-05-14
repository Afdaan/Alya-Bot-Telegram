"""
Search Engine module for Alya Telegram Bot.

This module provides web search capabilities using Google Custom Search API,
including query optimization, structured data extraction, and response formatting.
"""

import os
import aiohttp
import logging
import asyncio
import re
import random
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

class SearchEngine:
    """Handles web searches using Google Custom Search API with formatting capabilities."""
    
    def __init__(self):
        """Initialize the search engine with API credentials from environment."""
        # Support for multiple API keys to handle rate limits
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    def _load_api_keys(self):
        """Load multiple API keys from environment variables."""
        # Primary API key
        primary_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        api_keys = [primary_key] if primary_key else []
        
        # Additional API keys (GOOGLE_SEARCH_API_KEY_2, GOOGLE_SEARCH_API_KEY_3, etc.)
        for i in range(2, 11):  # Support up to 10 API keys
            key = os.getenv(f'GOOGLE_SEARCH_API_KEY_{i}')
            if key:
                api_keys.append(key)
                
        logger.info(f"Loaded {len(api_keys)} Google Search API keys")
        return api_keys
        
    def _get_next_api_key(self):
        """Get the next available API key using round-robin selection."""
        if not self.api_keys:
            return None
            
        # Round-robin selection
        api_key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return api_key
    
    async def search(self, query: str, detailed: bool = False) -> Tuple[str, Optional[List[Dict]]]:
        """
        Search the web for information and format results.
        
        Args:
            query: The search query
            detailed: Whether to return detailed results with more entries
            
        Returns:
            Tuple of (formatted search results text, image results list or None)
        """
        # Try each API key until one works or all fail
        images_data = None
        
        # Jika tidak ada API key yang tersedia
        if not self.api_keys:
            return "Maaf, API key untuk pencarian tidak tersedia. Silakan hubungi developer.", None
        
        for attempt in range(max(1, len(self.api_keys))):  # Pastikan minimal 1 attempt
            try:
                if not query or not isinstance(query, str):
                    logger.error(f"Invalid query: {query}")
                    return "Maaf, tidak dapat memproses query pencarian.", None

                # Clean and optimize the query
                cleaned_query = self._optimize_query(query)
                
                # Get next API key
                api_key = self._get_next_api_key()
                
                if not api_key or not self.search_engine_id:
                    logger.error("Missing API key or search engine ID")
                    return "Maaf, fitur pencarian sedang tidak tersedia.", None
                
                # Configure search parameters with image search enabled
                params = {
                    'key': api_key,
                    'cx': self.search_engine_id,
                    'q': cleaned_query,
                    'num': 5 if detailed else 3,
                    'gl': 'id',  # Set geography to Indonesia
                    'lr': 'lang_id',  # Prefer Indonesian results
                    'searchType': 'image' if 'gambar' in query.lower() or 'foto' in query.lower() else None,
                }
                
                # Remove None values from params
                params = {k: v for k, v in params.items() if v is not None}
                
                # Add timeout to prevent hanging
                timeout = aiohttp.ClientTimeout(total=15)  # 15 seconds timeout
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    try:
                        async with session.get(self.base_url, params=params) as response:
                            if response.status == 429:  # Too Many Requests (Rate Limit)
                                logger.warning(f"Rate limit hit for API key {self.current_key_index}, trying next key")
                                continue  # Try next API key
                                
                            if response.status != 200:
                                logger.error(f"Search API error: {response.status}")
                                return f"Maaf, terjadi error saat mencari informasi (Status: {response.status}) 😢", None
                                
                            result = await response.json()
                            
                            if 'items' not in result:
                                return f"Maaf, tidak menemukan hasil yang relevan untuk '{query}' 😔", None

                            # Try to find images in the search results
                            image_results = self._extract_image_data(result, params.get('searchType') == 'image')

                            # Extract structured data when possible
                            structured_data = self._extract_structured_data(result)
                            if structured_data:
                                return structured_data, image_results

                            # Format results
                            return self._format_search_results(result, query, detailed), image_results
                    
                    except asyncio.TimeoutError:
                        logger.error("Search timeout")
                        continue  # Try next API key on timeout
                    
                    except Exception as e:
                        logger.error(f"Search request error with API key {self.current_key_index}: {e}")
                        continue  # Try next API key on error

            except Exception as e:
                logger.error(f"Search error: {e}")
                continue  # Try next API key
        
        # If we've exhausted all API keys
        return "Maaf, pencarian mencapai batas kuota. Silakan coba lagi nanti 🙏", None
        
    def _extract_image_data(self, result, is_image_search=False) -> Optional[List[Dict]]:
        """
        Extract image URLs and data from search results.
        
        Args:
            result: Raw API response from Google
            is_image_search: Whether the original search was an image search
            
        Returns:
            List of image data (url, title, source) or None
        """
        try:
            images = []
            
            # For dedicated image searches
            if is_image_search and 'items' in result:
                for item in result['items'][:3]:  # Limit to 3 images
                    if 'link' in item:
                        image_data = {
                            'url': item.get('link'),
                            'title': item.get('title', 'No title'),
                            'source': item.get('displayLink', 'Unknown source'),
                            'thumbnail': item.get('image', {}).get('thumbnailLink', item.get('link'))
                        }
                        images.append(image_data)
                
                return images if images else None
            
            # For regular searches, try to extract images from pagemap
            elif 'items' in result:
                for item in result['items']:
                    if 'pagemap' in item and 'cse_image' in item['pagemap']:
                        for image in item['pagemap']['cse_image'][:1]:  # Just take the first image
                            if 'src' in image:
                                image_data = {
                                    'url': image.get('src'),
                                    'title': item.get('title', 'No title'),
                                    'source': item.get('displayLink', 'Unknown source'),
                                    'thumbnail': image.get('src')  # Use same URL as thumbnail
                                }
                                images.append(image_data)
                                
                                # Limit to 3 images maximum
                                if len(images) >= 3:
                                    break
                
                return images if images else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image data: {e}")
            return None

    def _optimize_query(self, query: str) -> str:
        """
        Optimize the search query for better results.
        
        Removes filler words and adds relevant keywords based on topic detection.
        
        Args:
            query: Original search query
            
        Returns:
            Optimized search query
        """
        if not query:
            return ""
            
        # Remove filler words
        fillers = [
            "tolong", "coba", "bantu", "bisa", "minta", "alya", "dong", "ya", "kak",
            "mbak", "mas", "bro", "sis", "sayang", "beb", "deh", "sih", "ai", "carikan"
        ]
        
        query_lower = query.lower()
        for filler in fillers:
            if f" {filler} " in f" {query_lower} ":
                query_lower = query_lower.replace(f" {filler} ", " ")
        
        # Add relevant keywords based on topic detection
        if "jadwal" in query_lower and "kereta" in query_lower:
            query_lower += " jadwal resmi kai"
        elif "jadwal" in query_lower and any(word in query_lower for word in ["pesawat", "flight"]):
            query_lower += " schedule timetable"
            
        return query_lower

    def _extract_structured_data(self, result):
        """
        Extract structured data like schedules or timetables when available.
        
        Args:
            result: Raw API response from Google
            
        Returns:
            Formatted structured data or None if not available
        """
        try:
            # Check for special featured snippets
            if 'items' in result and len(result['items']) > 0:
                item = result['items'][0]
                
                # Look for structured data in rich snippets
                if 'pagemap' in item:
                    pagemap = item['pagemap']
                    
                    # Check for event data
                    if 'event' in pagemap:
                        events = pagemap['event']
                        if events:
                            structured_data = "📅 Jadwal/Event yang ditemukan:\n\n"
                            for event in events[:3]:  # Limit to 3 events
                                name = event.get('name', 'Unknown')
                                start_date = event.get('startdate', 'Unknown')
                                location = event.get('location', 'Unknown')
                                structured_data += f"• {name}\n  📆 {start_date}\n  📍 {location}\n\n"
                            return structured_data
                            
            return None
                    
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return None
            
    def _format_search_results(self, result, query, detailed):
        """
        Format search results into a readable response.
        
        Args:
            result: Raw API response from Google
            query: Original search query
            detailed: Whether to include additional details
            
        Returns:
            Formatted search results as string
        """
        response_text = f"Hasil pencarian untuk '{query}':\n\n"
                        
        for item in result['items']:
            title = item.get('title', 'No title')
            snippet = item.get('snippet', 'No description')
            link = item.get('link', '#')
            
            # Clean up the snippet
            snippet = snippet.replace('...', '').strip()
            
            response_text += f"📌 {title}\n"
            response_text += f"💡 {snippet}\n"
            response_text += f"🔗 {link}\n\n"

            # Add additional info if detailed
            if detailed and 'pagemap' in item:
                if 'metatags' in item['pagemap']:
                    meta = item['pagemap']['metatags'][0]
                    if 'og:description' in meta:
                        response_text += f"📝 Detail:\n{meta['og:description']}\n\n"

        return response_text
