"""
Fact Extractor for Alya Telegram Bot.

This module extracts personal facts from user messages for persistent memory.
"""

import re
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)

class FactExtractor:
    """Extract personal facts from message content."""
    
    def __init__(self):
        """Initialize fact extractor with patterns."""
        self.patterns = {
            'birthday': [
                r'ulang\s*tahun[ku|saya|gw]\s*(?:adalah|itu|pada)?\s*tanggal\s*(\d{1,2}\s*[a-zA-Z]+)',
                r'tanggal\s*ulang\s*tahun[ku|saya|gw]\s*(?:adalah)?\s*(\d{1,2}\s*[a-zA-Z]+)',
                r'[I|i|saya|gw|aku] born on (\d{1,2}\s*[a-zA-Z]+)',
                r'[my|My|saya|gw] birthday is (\d{1,2}\s*[a-zA-Z]+)',
            ],
            'name': [
                r'[N|n]ama\s*[saya|gw|ku|aku]\s*(?:adalah)?\s*([A-Za-z]+)',
                r'[P|p]anggil\s*[aku|saya|gw]\s*([A-Za-z]+)',
                r'[M|m]y\s*name\s*is\s*([A-Za-z]+)',
                r'[C|c]all\s*me\s*([A-Za-z]+)',
            ],
            'hobby': [
                r'[H|h]obi\s*[saya|gw|ku|aku]\s*(?:adalah)?\s*([A-Za-z\s]+)',
                r'[S|s]uka\s*([A-Za-z\s]+)',
                r'[M|m]y\s*hobby\s*is\s*([A-Za-z\s]+)',
            ],
            'location': [
                r'[T|t]inggal\s*di\s*([A-Za-z\s]+)',
                r'[A|a]lamat\s*[saya|gw|ku|aku]\s*(?:adalah)?\s*([A-Za-z\s]+)',
                r'[I|i]\s*live\s*in\s*([A-Za-z\s]+)',
            ]
        }
    
    def extract_facts(self, text: str) -> Dict[str, str]:
        """
        Extract personal facts from text.
        
        Args:
            text: Message text to analyze
            
        Returns:
            Dictionary of extracted facts (fact_type -> value)
        """
        facts = {}
        
        for fact_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches and matches[0]:
                    # Clean up and normalize the match
                    value = self._normalize_value(fact_type, matches[0])
                    facts[fact_type] = value.strip()
                    break
        
        return facts
    
    def _normalize_value(self, fact_type: str, value: str) -> str:
        """Normalize extracted values based on fact type."""
        if fact_type == 'birthday':
            # Try to standardize birthday format
            value = value.lower()
            # Convert Indonesian month names if needed
            id_months = {
                'januari': 'january', 
                'februari': 'february',
                'maret': 'march',
                'april': 'april',
                'mei': 'may',
                'juni': 'june',
                'juli': 'july',
                'agustus': 'august',
                'september': 'september',
                'oktober': 'october',
                'november': 'november',
                'desember': 'december'
            }
            
            for id_month, en_month in id_months.items():
                if id_month in value:
                    value = value.replace(id_month, en_month)
        
        return value

# Singleton instance
fact_extractor = FactExtractor()
