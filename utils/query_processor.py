"""
Query Processing Utilities for Alya Bot.

This module provides query processing, intent detection, and search query
optimization for better search results and understanding user intentions.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from utils.natural_parser import check_message_intent

logger = logging.getLogger(__name__)

class QueryProcessor:
    """
    Process user queries for enhanced search results and understanding.
    
    This class handles query preprocessing, optimization, and categorization
    to improve search quality and user experience.
    """
    
    def __init__(self):
        """Initialize the query processor with intent and entity patterns."""
        # Query categories with relevant keywords
        self.query_categories = {
            'travel': ['perjalanan', 'rute', 'jalan', 'ke', 'dari', 'menuju', 'tiket', 'transport'],
            'schedule': ['jadwal', 'waktu', 'jam', 'schedule', 'acara', 'event', 'hari'],
            'price': ['harga', 'biaya', 'tarif', 'cost', 'mahal', 'murah', 'beli', 'bayar'],
            'weather': ['cuaca', 'suhu', 'weather', 'temperature', 'hujan', 'panas', 'dingin'],
            'news': ['berita', 'kabar', 'news', 'update', 'terbaru', 'trending', 'viral'],
            'product': ['beli', 'jual', 'produk', 'barang', 'shop', 'belanja', 'toko'],
            'location': ['tempat', 'lokasi', 'spot', 'area', 'di mana', 'alamat', 'maps'],
            'definition': ['apa itu', 'siapa itu', 'maksud dari', 'definisi', 'arti', 'pengertian'],
            'howto': ['cara', 'bagaimana', 'tutorial', 'how to', 'petunjuk', 'panduan', 'langkah']
        }
        
        # Load stopwords for query optimization
        self.stopwords = self._load_stopwords()
        
        # Region/city names for locality detection
        self.regions = [
            'jakarta', 'bandung', 'surabaya', 'medan', 'semarang', 'yogyakarta', 'jogja', 
            'bali', 'makassar', 'palembang', 'padang', 'aceh', 'lampung', 'papua', 'malang',
            'bogor', 'bekasi', 'tangerang', 'depok', 'solo', 'banten', 'lombok', 'batam'
        ]
        
    def _load_stopwords(self) -> Set[str]:
        """
        Load stopwords for query cleaning.
        
        Returns:
            Set of stopword strings
        """
        return {
            # Indonesian stopwords
            'yang', 'dan', 'di', 'ke', 'dari', 'dengan', 'untuk', 'pada', 'ini', 'itu',
            'atau', 'juga', 'ada', 'akan', 'bisa', 'dalam', 'oleh', 'secara', 'jika',
            'agar', 'tentang', 'seperti', 'adalah', 'sebagai', 'saya', 'kamu', 'dia',
            # English stopwords
            'the', 'and', 'to', 'of', 'in', 'for', 'on', 'with', 'by', 'at', 'from',
            'about', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has',
            'a', 'an', 'i', 'you', 'he', 'she', 'they', 'we', 'it'
        }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process query for enhanced search.
        
        Args:
            query: User's search query
            
        Returns:
            Dictionary with processed query information
        """
        if not query or not query.strip():
            return {
                "original": "",
                "processed": "",
                "category": "unknown",
                "entities": {},
                "locality": None
            }
        
        # Clean and normalize query
        cleaned_query = self.clean_query(query)
        
        # Get intent information to assist categorization
        intent_info = check_message_intent(query)
        
        # Categorize query
        category = self.categorize_query(cleaned_query, intent_info)
        
        # Extract key entities
        entities = self.extract_entities(query)
        
        # Optimize query for search
        optimized_query = self.optimize_query(cleaned_query, category)
        
        # Detect locality for region-specific searches
        locality = self.detect_locality(query)
        
        return {
            "original": query,
            "processed": optimized_query,
            "category": category,
            "entities": entities,
            "locality": locality,
            "keywords": intent_info.get("keywords", [])
        }
    
    def clean_query(self, query: str) -> str:
        """
        Clean query by removing noise and normalizing text.
        
        Args:
            query: Original query
            
        Returns:
            Cleaned query string
        """
        if not query:
            return ""
            
        # Convert to lowercase
        query = query.lower().strip()
        
        # Remove excess whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Remove unnecessary prefixes
        prefixes_to_remove = ['tolong', 'mau', 'cari', 'carikan', 'search', 'find', 'please']
        
        for prefix in prefixes_to_remove:
            if query.startswith(prefix + " "):
                query = query.replace(prefix, '', 1).strip()
                
        # Remove unnecessary punctuation at start/end
        query = query.strip('.,;:?!-"\'')
                
        return query
    
    def categorize_query(self, query: str, intent_info: Dict[str, Any] = None) -> str:
        """
        Categorize query based on content and intent.
        
        Args:
            query: User's query
            intent_info: Optional intent analysis results
            
        Returns:
            Query category string
        """
        query_lower = query.lower()
        
        # Count matches for each category
        category_matches = {}
        
        for category, keywords in self.query_categories.items():
            category_matches[category] = 0
            
            for keyword in keywords:
                if keyword in query_lower:
                    category_matches[category] += 1
                    
                    # Give more weight to keywords at the start of the query
                    if query_lower.startswith(keyword):
                        category_matches[category] += 0.5
        
        # Use intent to influence categorization
        if intent_info:
            # Informative intent maps well to definition/howto
            if intent_info.get('intent') == 'informative':
                category_matches['definition'] = category_matches.get('definition', 0) + 0.5
                category_matches['howto'] = category_matches.get('howto', 0) + 0.5
                
            # Questions often seek definitions
            if intent_info.get('contains_question', False):
                category_matches['definition'] = category_matches.get('definition', 0) + 0.5
        
        # Determine primary category (with most matches)
        if category_matches:
            # Find category with most matches
            max_matches = max(category_matches.values())
            
            if max_matches > 0:
                # Get all categories with max matches
                max_categories = [
                    category for category, matches 
                    in category_matches.items() 
                    if matches == max_matches
                ]
                
                if max_categories:
                    return max_categories[0]
        
        # Default to general search if no category matches
        return "general"
    
    def optimize_query(self, query: str, category: str) -> str:
        """
        Optimize query for better search results based on category.
        
        Args:
            query: Cleaned user query
            category: Detected query category
            
        Returns:
            Optimized query for search engine
        """
        words = query.split()
        
        # Remove stopwords if query is long enough
        if len(words) > 3:
            words = [word for word in words if word not in self.stopwords]
            query = ' '.join(words)
        
        # Add category-specific optimizations
        if category == 'travel':
            if 'rute' in query and 'ke' in query:
                query = re.sub(r'rute\s+ke', 'rute menuju', query)
                
        elif category == 'schedule':
            if 'jadwal' in query:
                # Add time qualifier if not present
                time_qualifiers = ['hari ini', 'besok', 'minggu ini', 'bulan ini']
                has_time = any(qualifier in query for qualifier in time_qualifiers)
                
                if not has_time:
                    query += ' terbaru'
                    
        elif category == 'news':
            # Add recency for news queries
            if 'berita' in query and not any(word in query for word in ['terbaru', 'hari ini', 'update']):
                query += ' terbaru'
                
        elif category == 'howto':
            # Add tutorial qualifier for how-to queries
            if 'cara' in query and not any(word in query for word in ['tutorial', 'langkah', 'metode']):
                query += ' tutorial'
                
        return query
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities from query for structured understanding.
        
        Args:
            query: User's query
            
        Returns:
            Dictionary of entity types and values
        """
        entities = {
            'locations': [],
            'dates': [],
            'products': [],
            'organizations': []
        }
        
        # Extract locations
        location_patterns = [
            r'di\s+([A-Za-z\s]+)(?:\s|$|\.|,)',
            r'ke\s+([A-Za-z\s]+)(?:\s|$|\.|,)',
            r'dari\s+([A-Za-z\s]+)(?:\s|$|\.|,)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match.strip() and len(match.strip()) > 2:
                    entities['locations'].append(match.strip())
        
        # Extract dates
        date_patterns = [
            r'(?:tanggal|tgl)\s+(\d{1,2}(?:\s+)?\w+(?:\s+)?\d{2,4})',
            r'(\d{1,2}\s+(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)(?:\s+\d{2,4})?)',
            r'((?:senin|selasa|rabu|kamis|jumat|sabtu|minggu)(?:\s+(?:depan|ini|kemarin))?)'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities['dates'].extend([m.strip() for m in matches if m.strip()])
            
        # Extract products
        product_patterns = [
            r'(?:beli|jual|cari|produk)\s+([A-Za-z0-9\s]+)(?:\s|$|\.|,)',
            r'(?:harga|review)\s+([A-Za-z0-9\s]+)(?:\s|$|\.|,)'
        ]
        
        for pattern in product_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match.strip() and len(match.strip()) > 2:
                    entities['products'].append(match.strip())
        
        # Extract organizations
        org_patterns = [
            r'(?:perusahaan|company|PT|CV)\s+([A-Za-z\s]+)(?:\s|$|\.|,)',
            r'(?:oleh|dari|with)\s+([A-Z][A-Za-z\s]+)(?:\s|$|\.|,)'
        ]
        
        for pattern in org_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match.strip() and len(match.strip()) > 2:
                    entities['organizations'].append(match.strip())
        
        # Remove duplicates and clean up
        for entity_type in entities:
            if entities[entity_type]:
                # Remove duplicates while preserving order
                seen = set()
                entities[entity_type] = [
                    x for x in entities[entity_type] 
                    if not (x in seen or seen.add(x))
                ]
        
        return entities
    
    def detect_locality(self, query: str) -> Optional[str]:
        """
        Detect if query has a locality focus (region-specific).
        
        Args:
            query: User's query
            
        Returns:
            Detected locality or None
        """
        query_lower = query.lower()
        
        # Direct region mentions
        for region in self.regions:
            if region in query_lower:
                return region
        
        # Check for location prepositions followed by potential regions
        location_matches = re.findall(r'(?:di|ke|dari)\s+([a-z]+)', query_lower)
        for match in location_matches:
            if match in self.regions:
                return match
                
        return None

# Create singleton instance
query_processor = QueryProcessor()

def process_query(query: str) -> Dict[str, Any]:
    """
    Process search query for better results (convenience function).
    
    Args:
        query: Search query
        
    Returns:
        Processed query information
    """
    return query_processor.process_query(query)
