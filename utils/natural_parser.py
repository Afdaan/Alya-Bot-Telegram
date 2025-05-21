"""
Natural Language Parsing Utilities for Alya Bot.

This module provides utilities for parsing natural language input 
to detect intents, extract named entities, and classify messages.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any

from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Add the missing function that's being imported
def extract_command_parts(message_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract command and arguments from a message text.
    
    Args:
        message_text: Full message text with potential command
        
    Returns:
        Tuple of (command, arguments)
    """
    if not message_text:
        return None, None
        
    # Remove leading/trailing whitespace
    message_text = message_text.strip()
    
    # Check for slash commands
    if message_text.startswith('/'):
        parts = message_text.split(maxsplit=1)
        command = parts[0][1:]  # Remove the slash
        arguments = parts[1] if len(parts) > 1 else ""
        return command, arguments
    
    # Check for special prefixed commands like !ai, !search
    special_prefixes = ['!ai', '!search', '!sauce', '!trace', '!roast']
    for prefix in special_prefixes:
        if message_text.lower().startswith(prefix):
            parts = message_text.split(maxsplit=1)
            command = parts[0][1:]  # Remove the !
            arguments = parts[1] if len(parts) > 1 else ""
            return command, arguments
            
    # No command found
    return None, message_text

# Function to check message intent (may already exist, keeping for reference)
def check_message_intent(message: str) -> str:
    """
    Check the intent of a message.
    
    Args:
        message: Message text to analyze
        
    Returns:
        Intent classification string
    """
    # ... existing code ...
    # If this function doesn't exist, implement a simple version:
    intent_types = {
        "question": ["apa", "siapa", "kapan", "dimana", "mengapa", "bagaimana", "?"],
        "request": ["tolong", "bantu", "bisa", "minta", "mohon"],
        "greeting": ["hai", "halo", "hi", "hello", "ohayo", "konnichiwa"],
        "farewell": ["bye", "selamat tinggal", "sampai jumpa", "dadah"],
        "search": ["cari", "search", "find", "temukan"],
        "informative": ["jelaskan", "ceritakan", "explain", "tell me about"]
    }
    
    message_lower = message.lower()
    
    # Check for each intent type
    for intent, keywords in intent_types.items():
        if any(keyword in message_lower for keyword in keywords):
            return intent
    
    # Default to conversational if no specific intent detected
    return "conversational"

def detect_intent(message: str) -> Optional[str]:
    """
    Detect the intent of a message using advanced heuristics.
    
    Args:
        message: Message text to analyze
        
    Returns:
        Intent classification or None if uncertain
    """
    # ... existing code if any ...
    # Otherwise implement a basic version:
    return check_message_intent(message)

# Intent categories
INTENT_GREETING = "greeting"
INTENT_QUESTION = "question"
INTENT_COMMAND = "command"
INTENT_OPINION = "opinion"
INTENT_ROLEPLAY = "roleplay"
INTENT_PERSONAL = "personal"
INTENT_INFORMATIVE = "informative"

class NaturalLanguageParser:
    """
    Parser for detecting intent and extracting information from natural text.
    
    This class provides tools for understanding user messages beyond
    simple command pattern matching.
    """
    
    def __init__(self):
        """Initialize the natural language parser with pattern dictionaries."""
        # Intent patterns by category
        self.intent_patterns = {
            INTENT_GREETING: [
                r'\b(?:hai|halo|hello|hi|hey|ohayou|konichiwa|ohayo|hei)\b',
                r'^(?:selamat\s+(?:pagi|siang|sore|malam))$',
                r'^(?:good\s+(?:morning|afternoon|evening|night))$'
            ],
            INTENT_QUESTION: [
                r'\?$',
                r'\b(?:apa|siapa|kapan|dimana|bagaimana|kenapa|mengapa)\b.+',
                r'\b(?:what|who|when|where|how|why)\b.+',
                r'\b(?:bisakah|dapatkah|maukah)\b.+',
                r'\b(?:can|could|would|should)\b.+'
            ],
            INTENT_COMMAND: [
                r'^[!/].+',
                r'(?:tolong|please|coba)\s+(?:carikan|search|find|cari)\s+.+',
                r'(?:carikan|find|search|cari)\s+(?:untuk|for|about)\s+.+',
                r'^(?:tolong|please)\s+\w+(?:kan|in)\b',
                r'.*\b(?:lakukan|do|execute|run)\b.*'
            ],
            INTENT_OPINION: [
                r'\b(?:menurutmu|pendapatmu|bagaimana pendapat|what do you think|your opinion|your thoughts)\b',
                r'\b(?:apakah kamu setuju|do you agree|setuju|agree)\b',
                r'(?:lebih\s+(?:baik|bagus)|better)\b'
            ],
            INTENT_ROLEPLAY: [
                r'\*[^*]+\*',
                r'\b(?:roleplay|pretend|act as|act like|seolah-olah)\b'
            ],
            INTENT_PERSONAL: [
                r'\b(?:kamu|you)\b.*\b(?:suka|like|enjoy|love)\b',
                r'\b(?:siapa|who)(?:\s+are)?\s+(?:kamu|you|namamu|your name)\b',
                r'\b(?:umur|age|old)(?:\s+are)?\s+(?:kamu|you|mu)\b',
                r'\b(?:tentang|about)(?:\s+diri)?\s+(?:kamu|you|mu)\b'
            ],
            INTENT_INFORMATIVE: [
                r'\b(?:apa itu|what is|define|explain|jelaskan)\b\s+\w+',
                r'\b(?:bagaimana cara|how to|how do|cara)\b\s+\w+',
                r'\b(?:berapa|how much|how many)\b\s+\w+'
            ]
        }
        
        # Language indicators
        self.language_indicators = {
            'id': set(['apa', 'siapa', 'kapan', 'dimana', 'bagaimana', 'kenapa', 'kamu', 'saya', 
                      'tidak', 'ya', 'tolong', 'bisa', 'akan', 'sudah', 'belum']),
            'en': set(['what', 'who', 'when', 'where', 'how', 'why', 'you', 'i', 
                      'not', 'yes', 'please', 'can', 'will', 'have', 'has'])
        }
        
    async def detect_intent(self, text: str) -> str:
        """
        Detect primary intent from text message.
        
        Args:
            text: User message text
            
        Returns:
            Intent category string
        """
        if not text:
            return INTENT_ROLEPLAY  # Default intent
        
        # Clean text for pattern matching
        clean_text = text.strip().lower()
        
        # Count matches for each intent type
        intent_scores = {intent: 0 for intent in self.intent_patterns}
        
        for intent, patterns in self.intent_patterns.items():
            # Check each pattern
            for pattern in patterns:
                if re.search(pattern, clean_text, re.IGNORECASE):
                    intent_scores[intent] += 1
        
        # Special case for questions, reduce score if it's likely a command
        if intent_scores[INTENT_QUESTION] > 0 and text.startswith(('/')) or '!' in text[:2]:
            intent_scores[INTENT_QUESTION] = 0
        
        # Get intent with highest score
        max_score = max(intent_scores.values())
        
        if max_score == 0:
            # No clear intent detected
            return INTENT_ROLEPLAY  # Default to roleplay
        
        # Find all intents with max score
        top_intents = [intent for intent, score in intent_scores.items() if score == max_score]
        
        if len(top_intents) == 1:
            return top_intents[0]
        
        # Multiple max intents, use priority
        priority_order = [
            INTENT_COMMAND,
            INTENT_QUESTION,
            INTENT_GREETING,
            INTENT_OPINION,
            INTENT_INFORMATIVE,
            INTENT_PERSONAL,
            INTENT_ROLEPLAY
        ]
        
        for intent in priority_order:
            if intent in top_intents:
                return intent
        
        return INTENT_ROLEPLAY  # Default fallback
        
    def detect_language(self, text: str) -> str:
        """
        Detect primary language of text.
        
        Args:
            text: User message text
            
        Returns:
            Language code ('id', 'en', or 'unknown')
        """
        # Default to the system's default language if text is empty
        if not text:
            return DEFAULT_LANGUAGE
        
        # Clean and tokenize text
        clean_text = text.lower()
        words = re.findall(r'\b[a-z]+\b', clean_text)
        
        if not words:
            return DEFAULT_LANGUAGE
        
        # Count matches for each language
        id_count = sum(1 for word in words if word in self.language_indicators['id'])
        en_count = sum(1 for word in words if word in self.language_indicators['en'])
        
        if id_count > en_count:
            return 'id'
        elif en_count > id_count:
            return 'en'
        else:
            return DEFAULT_LANGUAGE
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        Extract important keywords from text.
        
        Args:
            text: User message text
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        if not text:
            return []
        
        # Clean text and split into words
        clean_text = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', clean_text)
        
        # Remove common stopwords
        stopwords = {
            'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'pada', 'dengan', 'ada', 
            'the', 'and', 'to', 'in', 'of', 'for', 'on', 'is', 'are', 'was'
        }
        
        filtered_words = [word for word in words if word not in stopwords]
        
        # Count word frequency
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return top keywords
        keywords = [word for word, _ in sorted_words[:max_keywords]]
        return keywords
    
    def check_message_intent(self, text: str) -> Dict[str, Any]:
        """
        Check message for intent and metadata.
        
        Args:
            text: User message text
            
        Returns:
            Dictionary with intent analysis
        """
        intent = asyncio.run(self.detect_intent(text))
        language = self.detect_language(text)
        
        return {
            'intent': intent,
            'language': language,
            'contains_question': '?' in text,
            'is_command': text.startswith(('/', '!')),
            'keywords': self.extract_keywords(text)
        }

# Singleton instance
natural_parser = NaturalLanguageParser()

# Convenience function
def check_message_intent(text: str) -> Dict[str, Any]:
    """
    Check message intent (convenience function).
    
    Args:
        text: User message text
        
    Returns:
        Dictionary with intent analysis
    """
    return natural_parser.check_message_intent(text)

async def detect_intent(text: str) -> str:
    """
    Detect intent from text (async convenience function).
    
    Args:
        text: User message text
        
    Returns:
        Intent category string
    """
    return await natural_parser.detect_intent(text)

# Add the missing function that's imported
def extract_personal_info(message: str) -> Dict[str, str]:
    """
    Extract personal information from a message.
    
    Args:
        message: Message text to analyze
        
    Returns:
        Dictionary of extracted personal info (type -> value)
    """
    info = {}
    
    # Don't process empty messages
    if not message or len(message.strip()) < 5:
        return info
        
    message_lower = message.lower()
    
    # Extract name patterns
    name_patterns = [
        r"(?:nama\s+(?:saya|aku|gw|gue|ku))[^\w]+([\w\s]+)",
        r"(?:my\s+name\s+is|i\s+am|i'm)[^\w]+([\w\s]+)",
        r"(?:panggil\s+(?:saya|aku|gw|gue|ku))[^\w]+([\w\s]+)",
        r"(?:call\s+me)[^\w]+([\w\s]+)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, message_lower)
        if match:
            potential_name = match.group(1).strip()
            # Basic validation - ignore short/common words
            if len(potential_name) >= 2 and potential_name not in ["dia", "kamu", "you", "me"]:
                info["name"] = potential_name.title()  # Capitalize name
                break
    
    # Extract age patterns
    age_patterns = [
        r"(?:umur\s+(?:saya|aku|gw|gue))[^\w]+(\d+)",
        r"(?:i\s+am|i'm)\s+(\d+)\s+(?:years|yo|year)",
        r"(?:saya|aku|gw|gue)\s+(\d+)\s+tahun"
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, message_lower)
        if match:
            age = match.group(1)
            # Basic validation - reasonable age range
            if 1 <= int(age) <= 120:
                info["age"] = age
                break
    
    # Extract location patterns
    location_patterns = [
        r"(?:(?:saya|aku|gw|gue)\s+(?:dari|tinggal\s+di))[^\w]+([\w\s]+)",
        r"(?:i\s+(?:live\s+in|am\s+from))[^\w]+([\w\s]+)",
        r"(?:rumah\s+(?:saya|aku|gw|gue))[^\w]+([\w\s]+)"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, message_lower)
        if match:
            location = match.group(1).strip()
            # Basic validation - ignore short/common words
            if len(location) >= 3:
                info["location"] = location
                break
    
    # Extract occupation/job patterns
    job_patterns = [
        r"(?:(?:kerja|pekerjaan)\s+(?:saya|aku|gw|gue))[^\w]+([\w\s]+)",
        r"(?:i\s+work\s+as|my\s+job\s+is)[^\w]+([\w\s]+)",
        r"(?:(?:saya|aku|gw|gue)\s+(?:adalah|sebagai))\s+([\w\s]+)"
    ]
    
    for pattern in job_patterns:
        match = re.search(pattern, message_lower)
        if match:
            job = match.group(1).strip()
            if len(job) >= 3:
                info["occupation"] = job
                break
    
    return info
