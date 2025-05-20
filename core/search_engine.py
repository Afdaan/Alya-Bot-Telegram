"""
Search Engine module for Alya Telegram Bot.

This module provides web search capabilities using Google Custom Search API,
including query optimization, structured data extraction, and response formatting.
"""

import os
import logging
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
        
        # Define platform-specific patterns once and reuse them
        self._init_search_patterns()
        
        # Initialize service with memory cache
        self._init_search_service()
        
    def _init_search_patterns(self):
        """Initialize search patterns for different types of searches."""
        # Common pattern parts to avoid duplication
        profile_prefix = r'(?:profile|profil|akun|user|username|cari|search|lihat|show|find|temukan)'
        username_suffix = r'(?:dengan username|dengan nama|username|nama|user|akun|untuk|dari|of|for|called|named|yang bernama|dengan id|id)?'
        
        # Enhanced intent patterns with more natural language variations for profile searches
        self.profile_patterns = {
            'github': f"{profile_prefix}\\s+(?:github|gh|git)\\s+{username_suffix}\\s*[\"']?(@?\\w+)[\"']?",
            'instagram': f"{profile_prefix}|stalking\\s+(?:instagram|ig|insta|instagramnya|ignya)\\s+{username_suffix}|punya\\s*[\"']?(@?\\w+)[\"']?",
            'twitter': f"{profile_prefix}\\s+(?:twitter|x|tweet|tw|twt|tweets)\\s+{username_suffix}\\s*[\"']?(@?\\w+)[\"']?",
            'facebook': f"{profile_prefix}\\s+(?:facebook|fb|meta|facebooknya|fbnya)\\s+{username_suffix}\\s*[\"']?(@?\\w+)[\"']?",
            'tiktok': f"{profile_prefix}\\s+(?:tiktok|tt|tik tok|tiktoknya|ttnya)\\s+{username_suffix}\\s*[\"']?(@?\\w+)[\"']?",
            'linkedin': f"{profile_prefix}\\s+(?:linkedin|linked in|li|linkedinnya)\\s+{username_suffix}\\s*[\"']?([\\w\\.-]+)[\"']?",
            'youtube': f"(?:channel|{profile_prefix})\\s+(?:youtube|yt|youtubenya|ytnya)\\s+{username_suffix}|channel\\s*[\"']?([\\w\\s\\.-]+)[\"']?",
            'reddit': f"{profile_prefix}\\s+(?:reddit|rddt|redd|subreddit|r/)\\s+{username_suffix}|u/|user\\s*[\"']?([\\w\\.-]+)[\"']?",
            'pinterest': f"{profile_prefix}\\s+(?:pinterest|pin|pins)\\s+{username_suffix}\\s*[\"']?([\\w\\.-]+)[\"']?",
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
        
    def _init_search_service(self):
        """Initialize search service with memory cache."""
        try:
            # Use memory cache instead of file cache
            self.service = build(
                "customsearch", 
                "v1", 
                developerKey=self._get_next_api_key(),
                cache_discovery=False  # Disable file caching
            )
        except Exception as e:
            logger.error(f"Failed to initialize search service: {str(e)}")
            self.service = None

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
        
        if not api_keys:
            logger.warning("No Google Search API keys found in environment variables")
        else:        
            logger.info(f"Loaded {len(api_keys)} Google Search API keys")
        
        return api_keys

    def _get_next_api_key(self):
        """Get the next available API key using round-robin selection."""
        if not self.api_keys:
            logger.error("No API keys available")
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
            
            # Extract the reformulated query 
            reformulated_query = intent_data.get('reformulated_query', query)
            
            # Check if this is a profile search
            if intent_data['intent'] == 'profile_search' and 'entities' in intent_data:
                platform = intent_data['entities'].get('platform')
                username = intent_data['entities'].get('username')
                
                if platform and username:
                    # Generate profile-specific response
                    formatted_text = f"Profile search for {username} on {platform}:\n\n"
                    
                    # If we have a direct URL template for this platform, provide it
                    if platform in self.platform_urls:
                        profile_url = self.platform_urls[platform].format(username=username)
                        formatted_text += f"Direct link: {profile_url}\n\n"
            else:
                formatted_text = ""  # Will be populated with search results
            
            # Check if our service is properly initialized
            if not self.service:
                # Try to reinitialize
                self._init_search_service()
                if not self.service:
                    return "Search service unavailable. Please try again later.", None
            
            # Get API key using rotation mechanism
            api_key = self._get_next_api_key()
            if not api_key:
                return "Sorry, no API keys available for search.", None
                
            if not self.search_engine_id:
                return "Search engine ID not configured.", None
            
            # Execute search using our pre-initialized service
            search_results = self.service.cse().list(
                q=reformulated_query,
                cx=self.search_engine_id,
                num=10 if detailed else 5
            ).execute()
            
            # Format results as text
            if not formatted_text:  # Only generate formatted text for non-profile searches
                formatted_text = self._format_search_results(search_results, query, detailed)
            else:
                # For profile searches, append the standard search results
                formatted_text += self._format_search_results(search_results, query, detailed)
            
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
                                    thumbnails = item['pagemap']['cse_thumbnail']
                                    if thumbnails and len(thumbnails) > 0 and 'src' in thumbnails[0]:
                                        image_data['thumbnail'] = thumbnails[0]['src']
                                            
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
        
        # Use a more efficient approach for filtering words
        cleaned_words = []
        for word in query_lower.split():
            if word not in fillers:
                cleaned_words.append(word)
        
        query_lower = " ".join(cleaned_words)
        
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
        
        # Check profile search patterns
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
                
                # Remove @ if present at the beginning of username
                if username and username.startswith('@'):
                    username = username[1:]
                
                result['intent'] = 'profile_search'
                result['entities'] = {
                    'platform': platform,
                    'username': username
                }
                
                # Reformulate query based on platform
                if platform in self.platform_urls:
                    # Direct target profile URL
                    result['reformulated_query'] = f"{platform} {username} profile account"
                    result['direct_url'] = self.platform_urls[platform].format(username=username)
                else:
                    # For unknown platforms, do a general search
                    result['reformulated_query'] = f"{platform} {username} profile account social media"
                
                return result
        
        # Check search intent patterns
        for intent_name, pattern in self.search_intents.items():
            match = re.search(pattern, query_lower)
            if match:
                # Extract entity (topic/subject of search)
                subject = match.group(1).strip()
                
                result['intent'] = intent_name
                result['entities'] = {'subject': subject}
                
                # Reformulate query based on intent
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

    async def format_search_results(results: List[Dict[str, any]], query: str, detailed: bool = False) -> str:
        """
        Format search results into a readable text.
        
        Args:
            results: List of search result dictionaries
            query: Original search query
            detailed: Whether to include detailed information
            
        Returns:
            Formatted search results text
        """
        if not results:
            return "Tidak ada hasil yang ditemukan untuk pencarian ini."
        
        # Start with search query
        output = [f"Results for '{query}':", ""]
        
        # Add snippets
        for result in results:
            title = result.get('title', 'No title')
            source = result.get('source', 'Unknown source')
            snippet = result.get('snippet', '')
            url = result.get('link', '')
            
            # Format title differently based on source
            if "wikipedia" in source.lower():
                output.append(f"📚 {title}")
            elif "github" in source.lower():
                output.append(f"💻 {title}")
            elif "news" in source.lower() or "berita" in source.lower():
                output.append(f"📰 {title}")
            else:
                output.append(f"🌐 {title}")
                
            # Add source info if available
            if source and source != title and not source.startswith('http'):
                output.append(f"   {source}")
                
            # Add detailed snippet if requested
            if detailed and snippet:
                # Clean up snippet
                snippet = snippet.replace("\n", " ").strip()
                if len(snippet) > 150:
                    snippet = snippet[:150] + "..."
                output.append(f"   {snippet}")
                
            # Add URL only in detailed mode (to avoid clutter)
            if detailed and url:
                output.append(f"   {url}")
                
            # Add separator between results
            output.append("")
        
        # Add footer with info about image results if available
        if any('image_url' in result or 'thumbnail' in result for result in results):
            output.append("📷 Hasil gambar akan ditampilkan secara terpisah.")
        
        return "\n".join(output)

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
        
        # Track URLs for button creation
        response_urls = []
                    
        for item in result["items"]:
            # Get values directly without escaping
            title = item.get("title", "No title")
            snippet = item.get("snippet", "No description")
            link = item.get("link", "#")
            
            # Clean up the snippet (remove ellipses without escaping)
            snippet = snippet.replace('...', '').strip()
            
            response_text += f"📌 {title}\n"
            response_text += f"💡 {snippet}\n"
            
            # Store URLs for buttons instead of showing raw links
            if link and link != "#":
                # Add reference number
                link_num = len(response_urls) + 1
                response_text += f"🔗 Link #{link_num}\n\n"
                
                # PERBAIKAN: Sanitasi title untuk URL, hapus karakter yang bisa menyebabkan error
                safe_title = ''.join(c for c in title[:15] if c.isalnum() or c.isspace())
                
                # PERBAIKAN: Pastikan URL selalu diawali dengan protokol
                if not link.startswith(('http://', 'https://')):
                    link = 'https://' + link
                    
                response_urls.append((safe_title, link))
            else:
                response_text += "\n"  # Still add spacing

            # Add additional info if detailed
            if detailed and "pagemap" in item:
                if "metatags" in item["pagemap"]:
                    meta = item["pagemap"]["metatags"][0]
                    if "og:description" in meta:
                        extra_details = meta["og:description"]
                        response_text += f"📝 Detail:\n{extra_details}\n\n"
        
        # Add special marker to indicate we have URLs for buttons
        if response_urls:
            # PERBAIKAN: Format URL dengan lebih aman untuk menghindari error parsing
            url_parts = []
            for title, url in response_urls:
                # Gunakan pipe character sebagai delimiter yang aman
                url_parts.append(f"{title}|{url}")
                
            response_text += f"__URLS__{','.join(url_parts)}"
        
        return response_text