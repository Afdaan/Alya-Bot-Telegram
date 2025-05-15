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
import warnings
from googleapiclient.discovery import build
from googleapiclient import _auth

# Disable cache warning
warnings.filterwarnings('ignore', message='file_cache is unavailable when using oauth2client >= 4.0.0')

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
        
        # Enhanced intent patterns with more natural language variations for profile searches
        self.profile_patterns = {
            # More natural language variations for GitHub profile searches
            'github': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:github|gh|git)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?\s*["\']?(@?\w+)["\']?',
            
            # Enhanced Instagram profile searches
            'instagram': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan|stalking)\s+(?:instagram|ig|insta|instagramnya|ignya)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id|punya)?\s*["\']?(@?\w+)["\']?',
            
            # Enhanced Twitter/X profile searches
            'twitter': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:twitter|x|tweet|tw|twt|tweets)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?\s*["\']?(@?\w+)["\']?',
            
            # Enhanced Facebook profile searches
            'facebook': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:facebook|fb|meta|facebooknya|fbnya)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?\s*["\']?(@?\w+)["\']?',
            
            # Enhanced TikTok profile searches
            'tiktok': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:tiktok|tt|tik tok|tiktoknya|ttnya)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?\s*["\']?(@?\w+)["\']?',
            
            # Enhanced LinkedIn profile searches
            'linkedin': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:linkedin|linked in|li|linkedinnya)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?\s*["\']?([\w\.-]+)["\']?',
            
            # Enhanced YouTube channel searches
            'youtube': r'(?:channel|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:youtube|yt|youtubenya|ytnya)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id|channel)?\s*["\']?([\w\s\.-]+)["\']?',
            
            # Add new platforms
            'reddit': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:reddit|rddt|redd|subreddit|r/)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id|u/|user)?\s*["\']?([\w\.-]+)["\']?',
            
            'pinterest': r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)\s+(?:pinterest|pin|pins)\s+(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?\s*["\']?([\w\.-]+)["\']?',
            
            # Generic username search pattern that will be used as fallback
            'generic': r'(?:username|user|profile|akun|profil|cari|search)\s+(?:di|on|at|in|untuk|untuk platform|platform)?\s*([a-zA-Z0-9_]+)\s+(?:username|user|nama|name|id|dengan username|dengan nama|dengan id)?\s*["\']?(@?[\w\.-]+)["\']?'
        }
        
        # Platform URL templates - untuk membuat URL spesifik platform
        self.platform_urls = {
            'github': "https://github.com/{username}",
            'instagram': "https://www.instagram.com/{username}/",
            'twitter': "https://twitter.com/{username}",
            'facebook': "https://facebook.com/{username}",
            'tiktok': "https://tiktok.com/@{username}",
            'linkedin': "https://linkedin.com/in/{username}",
            'youtube': "https://youtube.com/@{username}",
            'reddit': "https://reddit.com/user/{username}",
            'pinterest': "https://pinterest.com/{username}"
        }
        
        # Intent detection untuk jenis pencarian khusus
        self.search_intents = {
            'image_search': r'(?:cari|carikan|search|tampilkan|tunjukkan|lihat)\s+(?:gambar|foto|image|picture|pic)\s+(?:dari|tentang|dari|untuk|of|about|)\s*(.*?)(?:\s|$)',
            'location_search': r'(?:cari|carikan|lokasi|alamat|tempat|dimana)\s+(?:lokasi|alamat|tempat|letak|posisi)\s+(?:dari|untuk|of|about|)\s*(.*?)(?:\s|$)',
            'definition_search': r'(?:apa itu|apakah|definisi|arti|pengertian|maksud|jelaskan)\s+(.*?)(?:\s|$|\?)',
            'schedule_search': r'(?:jadwal|schedule|jam|waktu)\s+(.*?)(?:\s|$)',
            'news_search': r'(?:berita|kabar|news|artikel)\s+(?:terbaru|latest|tentang|mengenai|about|)\s*(.*?)(?:\s|$)'
        }
        
        # Initialize service with memory cache
        self._init_search_service()
        
    def _init_search_service(self):
        """Initialize search service with memory cache."""
        # Use memory cache instead of file cache
        self.service = build(
            "customsearch", 
            "v1", 
            developerKey=self._get_next_api_key(),
            cache_discovery=False  # Disable file caching
        )

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
        try:
            # Process query with natural language understanding and intent detection
            intent_data = self._detect_intent(query)
            
            # Use detected intent to optimize search
            if intent_data['intent'] == 'profile_search' and 'entities' in intent_data:
                # Handle profile search specifically
                platform = intent_data['entities'].get('platform')
                username = intent_data['entities'].get('username')
                
                if platform and username:
                    # Generate profile-specific response
                    formatted_text = f"Profile search for {username} on {platform}:\n\n"
                    
                    # If we have a direct URL template for this platform, provide it
                    if platform in self.platform_urls:
                        profile_url = self.platform_urls[platform].format(username=username)
                        formatted_text += f"Direct link: {profile_url}\n\n"
                    
                    # Also do a web search for more information
                    reformulated_query = f"{platform} {username} profile account"
                else:
                    # Use original query if incomplete intent detection
                    reformulated_query = query
            else:
                # Regular search with the original query
                reformulated_query = query
            
            # Get API key using rotation mechanism
            api_key = self._get_next_api_key()
            if not api_key:
                return "Sorry, no API keys available for search.", None
                
            if not self.search_engine_id:
                return "Search engine ID not configured.", None
                
            # Build the search service
            import googleapiclient.discovery
            service = googleapiclient.discovery.build(
                "customsearch", "v1", developerKey=api_key
            )
            
            # Execute search
            search_results = service.cse().list(
                q=reformulated_query,
                cx=self.search_engine_id,
                num=10 if detailed else 5
            ).execute()
            
            # Format results as text
            formatted_text = self._format_search_results(search_results, query, detailed)
            
            # Extract image data if available
            image_results = self._extract_image_data(search_results)
            
            # Return both text results and image data
            return formatted_text, image_results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            # Return error message and empty image results on failure
            return f"Sorry, I encountered an error while searching: {str(e)}", None

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
        
        # Direct username mention detection (e.g., "cari username johndoe" without platform)
        direct_username_match = re.search(r'(?:cari|search|find|temukan|lihat|show)\s+(?:username|user|profile|akun|id)\s+([a-zA-Z0-9_\.]+)', query_lower)
        if direct_username_match:
            username = direct_username_match.group(1)
            # This is a generic username search without specific platform
            result['intent'] = 'profile_search'
            result['entities'] = {
                'platform': 'general',
                'username': username
            }
            result['reformulated_query'] = f"{username} profile social media account"
            return result
        
        # Cek profile search patterns
        for platform, pattern in self.profile_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                username = None
                
                # Extract username based on the pattern match groups
                if platform == 'generic':
                    # For generic pattern, we have platform in group(1) and username in group(2)
                    platform_name = match.group(1)
                    username = match.group(2)
                    
                    # Map common platform variations to our supported platforms
                    platform_mapping = {
                        'ig': 'instagram',
                        'insta': 'instagram',
                        'fb': 'facebook',
                        'tweet': 'twitter',
                        'twt': 'twitter',
                        'gh': 'github',
                        'git': 'github',
                        'yt': 'youtube',
                        'pin': 'pinterest'
                    }
                    
                    # Try to map to a known platform
                    platform = platform_mapping.get(platform_name.lower(), platform_name.lower())
                else:
                    # For specific platform patterns
                    username = match.group(1)
                
                # Hapus @ jika ada di depan username
                if username and username.startswith('@'):
                    username = username[1:]
                
                result['intent'] = 'profile_search'
                result['entities'] = {
                    'platform': platform,
                    'username': username
                }
                
                # Reformulate query based on platform
                if platform in self.platform_urls:
                    # Langsung target URL profil
                    result['reformulated_query'] = f"{platform} {username} profile account"
                    result['direct_url'] = self.platform_urls[platform].format(username=username)
                else:
                    # For unknown platforms, do a general search
                    result['reformulated_query'] = f"{platform} {username} profile account social media"
                
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
        # No need to escape, since we'll use plain text mode in the handler
        response_text = f"Results for '{query}':\n\n"
        
        if "items" not in result:
            return f"No results found for '{query}'."
                    
        for item in result["items"]:
            # Get values directly without escaping
            title = item.get("title", "No title")
            snippet = item.get("snippet", "No description")
            link = item.get("link", "#")
            
            # Clean up the snippet (remove ellipses without escaping)
            snippet = snippet.replace('...', '').strip()
            
            response_text += f"📌 {title}\n"
            response_text += f"💡 {snippet}\n"
            response_text += f"🔗 {link}\n\n"

            # Add additional info if detailed
            if detailed and "pagemap" in item:
                if "metatags" in item["pagemap"]:
                    meta = item["pagemap"]["metatags"][0]
                    if "og:description" in meta:
                        extra_details = meta["og:description"]
                        response_text += f"📝 Detail:\n{extra_details}\n\n"
        
        return response_text

    def _escape_markdown(self, text):
        """
        Legacy method - kept for compatibility.
        We're now using plain text mode instead of MarkdownV2.
        """
        if not isinstance(text, str):
            text = str(text)
        
        return text