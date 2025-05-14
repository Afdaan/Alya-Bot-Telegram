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
from utils.query_processor import process_query

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
        
        # Intent patterns - untuk mengenali maksud user
        self.profile_patterns = {
            'github': r'(?:profile|profil|akun|user|username|cari)\s+(?:github|gh)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?(@?\w+)["\']?',
            'instagram': r'(?:profile|profil|akun|user|username|cari)\s+(?:instagram|ig|insta)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?(@?\w+)["\']?',
            'twitter': r'(?:profile|profil|akun|user|username|cari)\s+(?:twitter|x|tweet|tw)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?(@?\w+)["\']?',
            'facebook': r'(?:profile|profil|akun|user|username|cari)\s+(?:facebook|fb|meta)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?(@?\w+)["\']?',
            'tiktok': r'(?:profile|profil|akun|user|username|cari)\s+(?:tiktok|tt|tik tok)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?(@?\w+)["\']?',
            'linkedin': r'(?:profile|profil|akun|user|username|cari)\s+(?:linkedin|linked in|li)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?([\w\.-]+)["\']?',
            'youtube': r'(?:channel|profil|akun|user|username|cari)\s+(?:youtube|yt)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|)\s*["\']?([\w\s\.-]+)["\']?'
        }
        
        # Platform URL templates - untuk membuat URL spesifik platform
        self.platform_urls = {
            'github': "https://github.com/{username}",
            'instagram': "https://www.instagram.com/{username}/",
            'twitter': "https://twitter.com/{username}",
            'facebook': "https://facebook.com/{username}",
            'tiktok': "https://tiktok.com/@{username}",
            'linkedin': "https://linkedin.com/in/{username}",
            'youtube': "https://youtube.com/@{username}"
        }
        
        # Intent detection untuk jenis pencarian khusus
        self.search_intents = {
            'image_search': r'(?:cari|carikan|search|tampilkan|tunjukkan|lihat)\s+(?:gambar|foto|image|picture|pic)\s+(?:dari|tentang|dari|untuk|of|about|)\s*(.*?)(?:\s|$)',
            'location_search': r'(?:cari|carikan|lokasi|alamat|tempat|dimana)\s+(?:lokasi|alamat|tempat|letak|posisi)\s+(?:dari|untuk|of|about|)\s*(.*?)(?:\s|$)',
            'definition_search': r'(?:apa itu|apakah|definisi|arti|pengertian|maksud|jelaskan)\s+(.*?)(?:\s|$|\?)',
            'schedule_search': r'(?:jadwal|schedule|jam|waktu)\s+(.*?)(?:\s|$)',
            'news_search': r'(?:berita|kabar|news|artikel)\s+(?:terbaru|latest|tentang|mengenai|about|)\s*(.*?)(?:\s|$)'
        }
        
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
        # Process query with natural language understanding
        optimized_query, query_metadata = process_query(query)
        
        # Intent detection & query reformulation
        intent_data = self._detect_intent(query)
        
        # Use the processed query if available
        if 'intent' in query_metadata and query_metadata['intent'] != 'general':
            reformulated_query = optimized_query
            # Log the query transformation for debugging
            logger.info(f"Transformed query: '{query}' → '{reformulated_query}' (Intent: {query_metadata['intent']})")
        else:
            # Custom handling untuk platform profile search
            if intent_data['intent'] == 'profile_search' and 'direct_url' in intent_data:
                platform = intent_data['entities']['platform']
                username = intent_data['entities']['username']
                direct_url = intent_data['direct_url']
                
                # Buat respons khusus profil dengan direct URL
                profile_response = f"*Profil yang ditemukan:*\n\n"
                profile_response += f"🔍 *Platform*: {platform.capitalize()}\n"
                profile_response += f"👤 *Username*: {username}\n"
                profile_response += f"🔗 *Link*: {direct_url}\n\n"
                
                # Tambahkan informasi tentang platform
                if platform == 'github':
                    profile_response += f"*Info*: GitHub adalah platform hosting kode dan pengembangan software kolaboratif.\n"
                elif platform == 'instagram':
                    profile_response += f"*Info*: Instagram adalah media sosial untuk berbagi foto dan video.\n"
                # dan seterusnya untuk platform lain...
                
                # Tetap lakukan pencarian untuk mendapatkan informasi tambahan
                reformulated_query = f"{platform} {username} profile"
            else:
                # Gunakan query yang sudah direformulasi untuk pencarian
                reformulated_query = intent_data['reformulated_query']
        
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
                cleaned_query = reformulated_query
                
                # Get next API key
                api_key = self._get_next_api_key()
                
                if not api_key or not self.search_engine_id:
                    logger.error("Missing API key or search engine ID")
                    return "Maaf, fitur pencarian sedang tidak tersedia.", None
                
                # Configure search parameters with improved settings for global search
                params = {
                    'key': api_key,
                    'cx': self.search_engine_id,
                    'q': cleaned_query,
                    'num': 5 if detailed else 3,
                    # Remove regional restrictions for global search
                    'gl': 'us',        # US-based search (standard)
                    'hl': 'id',        # UI language for user 
                    'safe': 'off',     # Less content filtering
                }
                
                # For specific searches, add specialized parameters
                if any(word in query.lower() for word in ['gambar', 'foto', 'image', 'picture', 'pic']):
                    params['searchType'] = 'image'
                    params['imgSize'] = 'large'    # Prefer large images
                    params['imgType'] = 'photo'    # Prefer photos over clipart
                
                # For news searches
                if any(word in query.lower() for word in ['berita', 'news', 'artikel', 'terbaru', 'update']):
                    params['sort'] = 'date'        # Sort by date for news
                
                # For video searches
                if any(word in query.lower() for word in ['video', 'youtube', 'tiktok', 'reels']):
                    params['videoSyndicated'] = 'true'  # Include syndicated videos
                
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
                        }
                        
                        # Add multiple potential image URLs for fallback
                        if 'image' in item:
                            if 'thumbnailLink' in item['image']:
                                image_data['thumbnail'] = item['image']['thumbnailLink']
                            if 'contextLink' in item['image']:
                                image_data['context_url'] = item['image']['contextLink']
                        
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
                                }
                                
                                # Try to get multiple image sizes/sources for fallback
                                if 'pagemap' in item and 'cse_thumbnail' in item['pagemap']:
                                    if item['pagemap']['cse_thumbnail'] and len(item['pagemap']['cse_thumbnail']) > 0:
                                        if 'src' in item['pagemap']['cse_thumbnail'][0]:
                                            image_data['thumbnail'] = item['pagemap']['cse_thumbnail'][0]['src']
                                            
                                # Try to extract image URLs from other potential locations
                                if 'pagemap' in item and 'metatags' in item['pagemap']:
                                    metatags = item['pagemap']['metatags'][0] if item['pagemap']['metatags'] else {}
                                    for key in ['og:image', 'twitter:image', 'image']:
                                        if key in metatags:
                                            image_data['image_url'] = metatags[key]
                                            break
                                
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
            "mbak", "mas", "bro", "sis", "sayang", "beb", "deh", "sih", "ai", "carikan",
            "search", "cari", "carikan", "mencari"
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
        elif "profil" in query_lower or "profile" in query_lower:
            # Coba ekstrak username dari query
            username_match = re.search(r'(?:username|user|nama)[\s:]+([a-zA-Z0-9_.-]+)', query_lower)
            if username_match:
                username = username_match.group(1)
                query_lower = f"{username} profile account"
        
        return query_lower

    def _detect_intent(self, query: str) -> dict:
        """
        Detect intent and extract entities from natural language query.
        
        Args:
            query: User query in natural language
            
        Returns:
            Dict with detected intent, entities, and reformulated query
        """
        query_lower = query.lower()
        result = {
            'intent': 'general_search',
            'entities': {},
            'reformulated_query': query
        }
        
        # Cek profile search patterns
        for platform, pattern in self.profile_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                username = match.group(1)
                # Hapus @ jika ada di depan username
                if username.startswith('@'):
                    username = username[1:]
                
                result['intent'] = 'profile_search'
                result['entities'] = {
                    'platform': platform,
                    'username': username
                }
                
                # Reformulate query based on platform
                if platform in self.platform_urls:
                    # Langsung target URL profil
                    result['reformulated_query'] = f"{platform} {username} profile"
                    result['direct_url'] = self.platform_urls[platform].format(username=username)
                return result
        
        # Cek search intent khusus
        for intent_name, pattern in self.search_intents.items():
            match = re.search(pattern, query_lower)
            if match:
                # Extract entity (topic/subject pencarian)
                subject = match.group(1).strip()
                
                result['intent'] = intent_name
                result['entities'] = {'subject': subject}
                
                # Reformulasi query berdasarkan intent
                if intent_name == 'image_search':
                    result['reformulated_query'] = f"{subject} images pictures"
                elif intent_name == 'location_search':
                    result['reformulated_query'] = f"{subject} location address map"
                elif intent_name == 'definition_search':
                    result['reformulated_query'] = f"{subject} definition meaning explanation"
                elif intent_name == 'schedule_search':
                    result['reformulated_query'] = f"{subject} schedule timetable jadwal resmi"
                elif intent_name == 'news_search':
                    result['reformulated_query'] = f"{subject} news latest update berita terbaru"
                else:
                    # Default optimization
                    result['reformulated_query'] = subject
                
                return result
        
        # Fallback: clean & optimize general query
        result['reformulated_query'] = self._optimize_query(query)
        return result

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
        # Escape query for markdown safety
        safe_query = query.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('_', '\\_')
        safe_query = safe_query.replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(')
        safe_query = safe_query.replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>')
        safe_query = safe_query.replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|')
        safe_query = safe_query.replace('{', '\\{').replace('}', '\\}')
        
        response_text = f"Hasil pencarian untuk '{safe_query}':\n\n"
                    
        for item in result['items']:
            # Safely handle and escape all fields
            title = self._escape_markdown(item.get('title', 'No title'))
            snippet = self._escape_markdown(item.get('snippet', 'No description'))
            link = self._escape_markdown(item.get('link', '#'))
            
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
                        extra_details = self._escape_markdown(meta['og:description'])
                        response_text += f"📝 Detail:\n{extra_details}\n\n"
        
        return response_text

    def _escape_markdown(self, text):
        """
        Escape all special Markdown V2 characters in text.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for MarkdownV2 format
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Order matters! Escape backslash first
        escaped = text.replace('\\', '\\\\')
        
        # Then escape all other special characters - make sure to include the pipe character
        for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
            escaped = escaped.replace(char, f'\\{char}')
        
        return escaped