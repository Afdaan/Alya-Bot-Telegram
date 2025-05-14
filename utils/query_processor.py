"""
Query Processing for Alya Telegram Bot.

Module ini mengoptimasi query pencarian untuk mendapatkan hasil yang lebih natural
dan spesifik, dengan mendeteksi intent dan mengubah query sesuai kebutuhan.
"""

import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Processor untuk query pencarian dengan natural language understanding."""
    
    def __init__(self):
        """Initialize query processor with intent patterns."""
        # Intent patterns untuk mendeteksi tipe pencarian
        self.intent_patterns = {
            'travel': r'(cara|rute|jalur|jalan)\s+(ke|menuju|dari|to)\s+([a-zA-Z0-9\s]+)',
            'schedule': r'(jadwal|jam|waktu|schedule)\s+([a-zA-Z0-9\s]+)',
            'price': r'(harga|biaya|tarif|price|cost)\s+([a-zA-Z0-9\s]+)',
            'weather': r'(cuaca|weather|suhu)\s+(di|in|at)?\s*([a-zA-Z0-9\s]+)',
            'news': r'(berita|kabar|news)\s+(tentang|mengenai|terbaru|about)?\s*([a-zA-Z0-9\s]+)',
            'howto': r'(cara|tutorial|how to|bagaimana)\s+(membuat|menggunakan|melakukan|make|use|do)\s+([a-zA-Z0-9\s]+)',
            'meaning': r'(apa|arti|maksud|pengertian|definisi)\s+(dari|itu|dari|of)?\s*([a-zA-Z0-9\s]+)',
            # Add more specific patterns for search quality
            'product_search': r'(beli|jual|cari|shop|toko)\s+(online)?\s*([a-zA-Z0-9\s]+)',
            'job_search': r'(lowongan|kerja|karir|job|vacancy)\s+(di|untuk|at|in)?\s*([a-zA-Z0-9\s]+)',
            'local_search': r'(tempat|lokasi|spot|area)\s+(di|dekat|sekitar|near|at|in)?\s*([a-zA-Z0-9\s]+)',
            'review_search': r'(review|ulasan|rating|pendapat)\s+(tentang|untuk|about|of)?\s*([a-zA-Z0-9\s]+)'
        }
        
        # Query templates berdasarkan intent
        self.query_templates = {
            'travel': "{entity} rute perjalanan maps direction",
            'schedule': "{entity} jadwal resmi timetable",
            'price': "{entity} harga terbaru price comparison marketplace",
            'weather': "prakiraan cuaca {entity} hari ini weather forecast",
            'news': "{entity} berita terbaru update news",
            'howto': "cara {verb} {entity} tutorial langkah step-by-step guide",
            'meaning': "definisi pengertian arti {entity} adalah meaning definition",
            'product_search': "{entity} jual beli online marketplace toko shop",
            'job_search': "{entity} lowongan pekerjaan karir job vacancy",
            'local_search': "{entity} lokasi tempat area site location",
            'review_search': "{entity} review ulasan rating pendapat opinion"
        }
        
    def process(self, query: str) -> Tuple[str, Dict]:
        """
        Process query to identify intent and optimize for search.
        
        Args:
            query: Original user query
            
        Returns:
            Tuple of (optimized query, metadata dict)
        """
        query_lower = query.lower()
        metadata = {'intent': 'general', 'entities': {}}
        
        # Detect query intent
        for intent, pattern in self.intent_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                metadata['intent'] = intent
                
                # Extract entities based on intent
                if intent == 'travel':
                    destination = match.group(3).strip()
                    metadata['entities']['destination'] = destination
                    return self.query_templates[intent].format(entity=destination), metadata
                
                elif intent == 'schedule':
                    item = match.group(2).strip()
                    metadata['entities']['item'] = item
                    return self.query_templates[intent].format(entity=item), metadata
                
                elif intent == 'price':
                    item = match.group(2).strip()
                    metadata['entities']['item'] = item
                    return self.query_templates[intent].format(entity=item), metadata
                    
                elif intent == 'weather':
                    location = match.group(3).strip() if len(match.groups()) >= 3 else ""
                    metadata['entities']['location'] = location
                    return self.query_templates[intent].format(entity=location), metadata
                
                elif intent == 'news':
                    topic = match.group(3).strip() if len(match.groups()) >= 3 else ""
                    metadata['entities']['topic'] = topic
                    return self.query_templates[intent].format(entity=topic), metadata
                
                elif intent == 'howto':
                    verb = match.group(2).strip()
                    entity = match.group(3).strip() if len(match.groups()) >= 3 else ""
                    metadata['entities']['verb'] = verb
                    metadata['entities']['entity'] = entity
                    return self.query_templates[intent].format(verb=verb, entity=entity), metadata
                
                elif intent == 'meaning':
                    term = match.group(3).strip() if len(match.groups()) >= 3 else ""
                    metadata['entities']['term'] = term
                    return self.query_templates[intent].format(entity=term), metadata
                
                elif intent == 'product_search':
                    product = match.group(3).strip()
                    metadata['entities']['product'] = product
                    return self.query_templates[intent].format(entity=product), metadata
                
                elif intent == 'job_search':
                    job = match.group(3).strip()
                    metadata['entities']['job'] = job
                    return self.query_templates[intent].format(entity=job), metadata
                
                elif intent == 'local_search':
                    location = match.group(3).strip()
                    metadata['entities']['location'] = location
                    return self.query_templates[intent].format(entity=location), metadata
                
                elif intent == 'review_search':
                    item = match.group(3).strip()
                    metadata['entities']['item'] = item
                    return self.query_templates[intent].format(entity=item), metadata
        
        # Remove filler words for general queries
        fillers = [
            "tolong", "coba", "bantu", "bisa", "minta", "alya", "dong", "ya", "kak",
            "mbak", "mas", "bro", "sis", "sayang", "beb", "deh", "sih", "ai", "carikan",
            "search", "cari", "carikan", "mencari", "apakah", "gimana"
        ]
        
        for filler in fillers:
            if f" {filler} " in f" {query_lower} ":
                query_lower = query_lower.replace(f" {filler} ", " ")
                
        # Detect question type queries
        if query_lower.startswith(('siapa', 'apa', 'kenapa', 'mengapa', 'bagaimana', 'dimana', 'kapan')):
            metadata['intent'] = 'question'
        
        # Detect image search intent
        if any(word in query_lower for word in ['gambar', 'foto', 'image', 'picture', 'pic']):
            metadata['intent'] = 'image_search'
            # Extract what the user is looking for images of
            img_match = re.search(r'(gambar|foto|image|picture|pic)\s+(dari|tentang|of|about)?\s*([a-zA-Z0-9\s]+)', query_lower)
            if img_match:
                subject = img_match.group(3).strip()
                metadata['entities']['subject'] = subject
                return f"{subject} images pictures high quality", metadata
        
        # Also check for common misspellings and variations
        query_cleaned = self._normalize_search_terms(query_lower)
        
        # If no specific intent detected, return cleaned query
        return query_cleaned, metadata
        
    def _normalize_search_terms(self, query: str) -> str:
        """
        Normalize search terms for better results. Fix common misspellings and variations.
        
        Args:
            query: Query to normalize
            
        Returns:
            Normalized query
        """
        replacements = {
            'instagram': ['ig', 'insta', 'instagtam'],
            'facebook': ['fb', 'fasebook', 'fesbuk'],
            'twitter': ['tweeter', 'twiter', 'twt'],
            'github': ['git', 'gh'],
            'youtube': ['yt', 'ytube', 'yutube'],
            'tiktok': ['tt', 'tik-tok', 'tiktoc']
        }
        
        for correct, variations in replacements.items():
            for var in variations:
                # Only replace if it's a whole word
                query = re.sub(r'\b' + var + r'\b', correct, query)
                
        return query

# Create singleton instance
query_processor = QueryProcessor()

def process_query(query: str) -> Tuple[str, Dict]:
    """
    Process search query for optimized results.
    
    Args:
        query: Original search query
        
    Returns:
        Tuple of (optimized query, metadata dict)
    """
    return query_processor.process(query)
