import os
import aiohttp
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus
import re
import json
import asyncio

logger = logging.getLogger(__name__)
load_dotenv()

class SearchEngine:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    async def search(self, query: str, detailed: bool = False) -> str:
        try:
            if not query or not isinstance(query, str):
                logger.error(f"Invalid query: {query}")
                return "Maaf, tidak dapat memproses query pencarian."

            # Clean and optimize the query
            cleaned_query = self._optimize_query(query)
            
            if not self.api_key or not self.search_engine_id:
                logger.error("Missing API key or search engine ID")
                return "Maaf, fitur pencarian sedang tidak tersedia."
            
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': cleaned_query,
                'num': 5 if detailed else 3,
                'gl': 'id',  # Set geography to Indonesia
                'lr': 'lang_id',  # Prefer Indonesian results
            }
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=15)  # 15 seconds timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.get(self.base_url, params=params) as response:
                        if response.status != 200:
                            logger.error(f"Search API error: {response.status}")
                            return "Maaf, terjadi error saat mencari informasi 😢"
                            
                        result = await response.json()
                        
                        if 'items' not in result:
                            return f"Maaf, tidak menemukan hasil yang relevan untuk '{query}' 😔"

                        # Extract structured data when possible
                        structured_data = self._extract_structured_data(result)
                        if structured_data:
                            return structured_data

                        # Format results
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
                
                except asyncio.TimeoutError:
                    logger.error("Search timeout")
                    return "Maaf, pencarian membutuhkan waktu terlalu lama. Silakan coba lagi nanti."

        except Exception as e:
            logger.error(f"Search error: {e}")
            return "Maaf, terjadi error saat mencari informasi 😢"

    def _optimize_query(self, query: str) -> str:
        """Optimize the search query for better results."""
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
        """Extract structured data like schedules or timetables when available."""
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
