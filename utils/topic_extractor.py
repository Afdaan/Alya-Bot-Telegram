"""
Topic Extraction Utilities for Alya Bot.

This module provides functionality to extract conversation topics and key entities
from messages to build better contextual awareness for the bot.
"""

import logging
import re
import string
from typing import List, Dict, Set, Any, Optional, Tuple, Union
from collections import Counter

logger = logging.getLogger(__name__)

# Common Indonesian and English stopwords
STOPWORDS = {
    # Indonesian stopwords
    'ada', 'adalah', 'adanya', 'adapun', 'agak', 'agaknya', 'agar', 'akan', 'akankah', 
    'akhir', 'akhiri', 'akhirnya', 'aku', 'akulah', 'amat', 'amatlah', 'anda', 'andalah', 
    'antar', 'antara', 'antaranya', 'apa', 'apaan', 'apabila', 'apakah', 'apalagi', 'apatah', 
    'artinya', 'asal', 'asalkan', 'atas', 'atau', 'ataukah', 'ataupun', 'awal', 'awalnya', 
    'bagai', 'bagaikan', 'bagaimana', 'bagaimanakah', 'bagaimanapun', 'bagi', 'bagian', 
    'bahkan', 'bahwa', 'bahwasanya', 'baik', 'bakal', 'bakalan', 'balik', 'banyak', 
    'bapak', 'baru', 'bawah', 'beberapa', 'begini', 'beginian', 'beginikah', 'beginilah', 
    'begitu', 'begitukah', 'begitulah', 'begitupun', 'bekerja', 'belakang', 'belakangan', 
    'belum', 'belumlah', 'benar', 'benarkah', 'benarlah', 'berada', 'berakhir', 'berakhirlah', 
    'berakhirnya', 'berapa', 'berapakah', 'berapalah', 'berapapun', 'berarti', 'berawal', 
    'berbagai', 'berdatangan', 'beri', 'berikan', 'berikut', 'berikutnya', 'berjumlah', 
    'berkali-kali', 'berkata', 'berkehendak', 'berkeinginan', 'berkenaan', 'berlainan', 
    'berlalu', 'berlangsung', 'berlebihan', 'bermacam', 'bermacam-macam', 'bermaksud', 
    'bermula', 'bersama', 'bersama-sama', 'bersiap', 'bersiap-siap', 'bertanya', 
    'bertanya-tanya', 'berturut', 'berturut-turut', 'bertutur', 'berujar', 'berupa', 
    'besar', 'betul', 'betulkah', 'biasa', 'biasanya', 'bila', 'bilakah', 'bisa', 'bisakah', 
    'boleh', 'bolehkah', 'bolehlah', 'buat', 'bukan', 'bukankah', 'bukanlah', 'bukannya', 
    'bulan', 'bung', 'cara', 'caranya', 'cukup', 'cukupkah', 'cukuplah', 'cuma', 'dahulu', 
    'dalam', 'dan', 'dapat', 'dari', 'daripada', 'datang', 'dekat', 'demi', 'demikian', 
    'demikianlah', 'dengan', 'depan', 'di', 'dia', 'diakhiri', 'diakhirinya', 'dialah', 
    'diantara', 'diantaranya', 'diberi', 'diberikan', 'diberikannya', 'dibuat', 'dibuatnya', 
    'didapat', 'didatangkan', 'digunakan', 'diibaratkan', 'diibaratkannya', 'diingat', 
    'diingatkan', 'diinginkan', 'dijawab', 'dijelaskan', 'dijelaskannya', 'dikarenakan', 
    'dikatakan', 'dikatakannya', 'dikerjakan', 'diketahui', 'diketahuinya', 'dikira', 
    'dilakukan', 'dilalui', 'dilihat', 'dimaksud', 'dimaksudkan', 'dimaksudkannya', 
    'dimaksudnya', 'diminta', 'dimintai', 'dimisalkan', 'dimulai', 'dimulailah', 
    'dimulainya', 'dimungkinkan', 'dini', 'dipastikan', 'diperbuat', 'diperbuatnya', 
    'dipergunakan', 'diperkirakan', 'diperlihatkan', 'diperlukan', 'diperlukannya', 
    'dipersoalkan', 'dipertanyakan', 'dipunyai', 'diri', 'dirinya', 'disampaikan', 
    'disebut', 'disebutkan', 'disebutkannya', 'disini', 'disinilah', 'ditambahkan', 
    'ditandaskan', 'ditanya', 'ditanyai', 'ditanyakan', 'ditegaskan', 'ditujukan', 
    'ditunjuk', 'ditunjuki', 'ditunjukkan', 'ditunjukkannya', 'ditunjuknya', 'dituturkan', 
    'dituturkannya', 'diucapkan', 'diucapkannya', 'diungkapkan', 'dong', 'dua', 'dulu', 
    'empat', 'enggak', 'enggaknya', 'entah', 'entahlah', 'guna', 'gunakan', 'hal', 'hampir', 
    'hanya', 'hanyalah', 'hari', 'harus', 'haruslah', 'harusnya', 'hendak', 'hendaklah', 
    'hendaknya', 'hingga', 'ia', 'ialah', 'ibarat', 'ibaratkan', 'ibaratnya', 'ibu', 'ikut', 
    'ingat', 'ingat-ingat', 'ingin', 'inginkah', 'inginkan', 'ini', 'inikah', 'inilah', 
    'itu', 'itukah', 'itulah', 'jadi', 'jadilah', 'jadinya', 'jangan', 'jangankan', 
    'janganlah', 'jauh', 'jawab', 'jawaban', 'jawabnya', 'jelas', 'jelaskan', 'jelaslah', 
    'jelasnya', 'jika', 'jikalau', 'juga', 'jumlah', 'jumlahnya', 'justru', 'kala', 
    'kalau', 'kalaulah', 'kalaupun', 'kalian', 'kami', 'kamilah', 'kamu', 'kamulah', 'kan', 
    'kapan', 'kapankah', 'kapanpun', 'karena', 'karenanya', 'kasus', 'kata', 'katakan', 
    'katakanlah', 'katanya', 'ke', 'keadaan', 'kebetulan', 'kecil', 'kedua', 'keduanya', 
    'keinginan', 'kelamaan', 'kelihatan', 'kelihatannya', 'kelima', 'keluar', 'kembali', 
    'kemudian', 'kemungkinan', 'kemungkinannya', 'kenapa', 'kepada', 'kepadanya', 'kesamaan', 
    'keseluruhan', 'keseluruhannya', 'keterlaluan', 'ketika', 'khususnya', 'kini', 'kinilah',
    
    # English stopwords
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", 
    "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 
    'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 
    'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 
    'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 
    'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 
    'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 
    'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 
    'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 
    'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 
    'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 
    's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 
    'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', 
    "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 
    'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 
    'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', 
    "won't", 'wouldn', "wouldn't"
}

class TopicExtractor:
    """
    Extract and analyze topics from conversation text.
    
    This class provides functionality to identify important topics,
    entities, and themes from conversation messages.
    """
    
    def __init__(self, stopwords: Set[str] = STOPWORDS, min_word_length: int = 3):
        """
        Initialize topic extractor.
        
        Args:
            stopwords: Set of stopwords to ignore
            min_word_length: Minimum length for valid words
        """
        self.stopwords = stopwords
        self.min_word_length = min_word_length
        
        # Common greeting and closing words to ignore
        self.greeting_words = {
            'hello', 'hi', 'hey', 'halo', 'hai', 'pagi', 'siang', 'sore', 'malam',
            'bye', 'goodbye', 'selamat', 'sampai', 'jumpa', 'good', 'morning',
            'afternoon', 'evening', 'night'
        }
    
    def extract_topics(self, text: str, max_topics: int = 5) -> List[str]:
        """
        Extract important topics from text.
        
        Args:
            text: Text to analyze
            max_topics: Maximum number of topics to extract
            
        Returns:
            List of extracted topics
        """
        if not text or len(text) < 10:
            return []
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remove punctuation and replace with spaces
        for punc in string.punctuation:
            text = text.replace(punc, ' ')
            
        # Split into words
        words = text.split()
        
        # Filter words
        filtered_words = [
            word for word in words
            if (word not in self.stopwords and
                word not in self.greeting_words and
                len(word) >= self.min_word_length)
        ]
        
        # Count word frequencies
        word_freq = Counter(filtered_words)
        
        # Get most common words as topics
        topics = [word for word, _ in word_freq.most_common(max_topics)]
        
        return topics
    
    def extract_named_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract potential named entities from text.
        
        This is a simple rule-based approach. For better results,
        consider integrating a proper NER library.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of entity types to entity lists
        """
        entities = {
            'persons': [],
            'places': [],
            'organizations': [],
            'misc': []
        }
        
        # Simple pattern for capitalized phrases (potential named entities)
        cap_phrases = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        
        # Remove duplicates while preserving order
        unique_phrases = []
        seen = set()
        for phrase in cap_phrases:
            if phrase.lower() not in seen and len(phrase) > 1:
                unique_phrases.append(phrase)
                seen.add(phrase.lower())
        
        # Simple classification based on keywords
        place_indicators = {'di', 'ke', 'dari', 'in', 'at', 'to', 'from'}
        org_indicators = {'PT', 'CV', 'Ltd', 'Inc', 'Corp'}
        
        for phrase in unique_phrases:
            # Check for place indicators
            context = self._get_entity_context(text, phrase)
            
            if any(indicator in context for indicator in place_indicators):
                entities['places'].append(phrase)
            elif any(indicator in phrase.split() for indicator in org_indicators):
                entities['organizations'].append(phrase)
            else:
                # Default to person if it looks like a name
                if len(phrase.split()) <= 3:  # Most names have 1-3 words
                    entities['persons'].append(phrase)
                else:
                    entities['misc'].append(phrase)
        
        return entities
    
    def _get_entity_context(self, text: str, entity: str) -> Set[str]:
        """
        Get context words around an entity.
        
        Args:
            text: Full text
            entity: Entity to find context for
            
        Returns:
            Set of context words
        """
        # Find entity in text
        entity_pos = text.find(entity)
        if entity_pos == -1:
            return set()
            
        # Get 3 words before and after entity
        start_pos = max(0, text.rfind(' ', 0, entity_pos - 15) if entity_pos > 15 else 0)
        end_pos = min(len(text), text.find(' ', entity_pos + len(entity) + 15) if entity_pos + len(entity) + 15 < len(text) else len(text))
        
        context = text[start_pos:end_pos].lower()
        return set(context.split())
    
    def get_message_topics(self, message: str) -> Dict[str, Any]:
        """
        Analyze message and extract topics and entities.
        
        Args:
            message: Message text
            
        Returns:
            Dictionary with extracted topics and entities
        """
        if not message or len(message) < 10:
            return {"topics": [], "entities": {}}
            
        try:
            topics = self.extract_topics(message)
            entities = self.extract_named_entities(message)
            
            return {
                "topics": topics,
                "entities": entities
            }
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return {"topics": [], "entities": {}}
    
    def categorize_message(self, message: str) -> Optional[str]:
        """
        Categorize message into a general category.
        
        Args:
            message: Message text
            
        Returns:
            Category name or None if not categorizable
        """
        if not message:
            return None
            
        # Convert to lowercase for matching
        message_lower = message.lower()
        
        # Define category indicators
        categories = {
            'question': ['?', 'apa', 'siapa', 'kapan', 'dimana', 'bagaimana', 'kenapa', 
                         'what', 'who', 'when', 'where', 'how', 'why'],
            'greeting': ['hai', 'halo', 'hello', 'hi', 'morning', 'pagi', 'siang', 
                         'sore', 'malam'],
            'opinion': ['menurut', 'pendapat', 'pikir', 'think', 'opinion', 'feel'],
            'request': ['tolong', 'bantu', 'help', 'please', 'bisa', 'can', 'could'],
            'statement': ['adalah', 'itu', 'ini', 'that', 'this', 'is', 'are']
        }
        
        # Check for category indicators
        category_scores = {category: 0 for category in categories}
        
        for category, indicators in categories.items():
            for indicator in indicators:
                if indicator in message_lower:
                    category_scores[category] += 1
        
        # Special case for questions
        if '?' in message:
            category_scores['question'] += 2
            
        # Get highest scoring category
        max_score = max(category_scores.values())
        if max_score > 0:
            # Get all categories with max score
            max_categories = [c for c, s in category_scores.items() if s == max_score]
            return max_categories[0]  # Return first category if multiple have same score
            
        return None

# Create singleton instance
topic_extractor = TopicExtractor()

def extract_topics(text: str, max_topics: int = 5) -> List[str]:
    """
    Extract topics from text (convenience function).
    
    Args:
        text: Text to analyze
        max_topics: Maximum number of topics to extract
        
    Returns:
        List of extracted topics
    """
    return topic_extractor.extract_topics(text, max_topics)

def get_message_topics(message: str) -> Dict[str, Any]:
    """
    Get topics and entities from message (convenience function).
    
    Args:
        message: Message text
        
    Returns:
        Dictionary with topics and entities
    """
    return topic_extractor.get_message_topics(message)
