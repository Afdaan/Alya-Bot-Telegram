"""
Memory context manager for Alya Bot with simple RAG functionality.
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from database.database_manager import db_manager, DatabaseManager
from config.settings import (
    MAX_MEMORY_ITEMS, RAG_MAX_RESULTS, SLIDING_WINDOW_SIZE
)

logger = logging.getLogger(__name__)

class MemoryManager:
    """Memory manager for conversation context and RAG functionality."""
    
    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the memory manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.message_counters: Dict[int, int] = {}  # Track messages per user
    
    def get_conversation_context(self, user_id: int) -> List[Dict[str, Any]]:
        """Get recent conversation history for context.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of conversation messages in Gemini format
        """
        try:
            # Get raw history from database
            raw_history = self.db.get_conversation_history(user_id, limit=MAX_MEMORY_ITEMS)
            
            # Format for Gemini API
            formatted_history = []
            for item in raw_history:
                formatted_history.append({
                    "role": item["role"],
                    "parts": [item["content"]]
                })
                
            return formatted_history
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract potential keywords from a query.
        
        This is a simple implementation. In production, you would use
        proper NLP techniques like TF-IDF or embeddings.
        
        Args:
            query: Query text
            
        Returns:
            List of extracted keywords
        """
        # Remove common stop words and punctuation
        stop_words = {'di', 'ke', 'dari', 'yang', 'dan', 'atau', 'dengan', 'untuk',
                     'pada', 'adalah', 'ini', 'itu', 'juga', 'saya', 'kamu', 'apa'}
        
        # Clean the text
        query = query.lower()
        query = re.sub(r'[^\w\s]', ' ', query)  # Remove punctuation
        
        # Extract words
        words = query.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def _simple_text_similarity(self, query: str, text: str) -> float:
        """Calculate simple text similarity based on keyword overlap.
        
        This is a very basic implementation. In production, you would use
        proper embeddings and vector similarity.
        
        Args:
            query: Query text
            text: Text to compare against
            
        Returns:
            Similarity score (0-1)
        """
        query_keywords = self._extract_keywords(query)
        text_lower = text.lower()
        
        if not query_keywords:
            return 0.0
            
        # Count how many keywords appear in the text
        matches = sum(1 for keyword in query_keywords if keyword in text_lower)
        
        # Calculate similarity score (0-1)
        similarity = matches / len(query_keywords) if query_keywords else 0
        
        return similarity
    
    def retrieve_relevant_memories(self, user_id: int, query: str) -> List[str]:
        """Retrieve relevant memories using simple RAG approach.
        
        Args:
            user_id: Telegram user ID
            query: User query
            
        Returns:
            List of relevant memory texts
        """
        try:
            # Get all stored texts
            rag_texts = self.db.get_rag_texts(user_id)
            
            # Calculate similarity for each text
            scored_texts = []
            for item in rag_texts:
                text = item["text"]
                score = self._simple_text_similarity(query, text)
                scored_texts.append((text, score))
            
            # Sort by similarity score (descending)
            scored_texts.sort(key=lambda x: x[1], reverse=True)
            
            # Return top results
            return [text for text, score in scored_texts[:RAG_MAX_RESULTS] if score > 0.1]
            
        except Exception as e:
            logger.error(f"Error retrieving relevant memories: {e}")
            return []
    
    def save_user_message(self, user_id: int, message: str) -> bool:
        """Save a user message to conversation history and RAG storage.
        
        Args:
            user_id: Telegram user ID
            message: Message content
            
        Returns:
            Success status
        """
        self._increment_message_counter(user_id)
        return self.db.save_message(user_id, 'user', message)
    
    def save_bot_response(self, user_id: int, response: str) -> bool:
        """Save a bot response to conversation history.
        
        Args:
            user_id: Telegram user ID
            response: Response content
            
        Returns:
            Success status
        """
        self._increment_message_counter(user_id)
        return self.db.save_message(user_id, 'assistant', response)
    
    def _increment_message_counter(self, user_id: int) -> None:
        """Increment message counter and check if sliding window should be applied.
        
        Args:
            user_id: Telegram user ID
        """
        # Initialize counter if not exists
        if user_id not in self.message_counters:
            self.message_counters[user_id] = 0
            
        # Increment counter
        self.message_counters[user_id] += 1
        
        # Check if we need to apply sliding window
        if self.message_counters[user_id] >= SLIDING_WINDOW_SIZE:
            self._apply_sliding_window(user_id)
            self.message_counters[user_id] = 0
    
    def _apply_sliding_window(self, user_id: int) -> None:
        """Apply sliding window to keep conversation from growing too large.
        
        When the conversation reaches SLIDING_WINDOW_SIZE messages, we keep
        only the most recent MAX_MEMORY_ITEMS messages and discard older ones.
        
        Args:
            user_id: Telegram user ID
        """
        try:
            logger.info(f"Applying sliding window for user {user_id}")
            
            # This implementation deletes all but the most recent messages
            # A more sophisticated approach would maintain summary or embeddings
            self.db.apply_sliding_window(user_id, MAX_MEMORY_ITEMS)
        except Exception as e:
            logger.error(f"Error applying sliding window: {e}")
    
    def reset_memory(self, user_id: int) -> bool:
        """Reset memory for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Success status
        """
        # Reset message counter
        if user_id in self.message_counters:
            self.message_counters[user_id] = 0
            
        return self.db.reset_conversation(user_id)
    
    def create_context_prompt(self, user_id: int, query: str, lang: str = 'id') -> str:
        """Create a context-aware prompt with relevant memories.
        
        Args:
            user_id: Telegram user ID
            query: User query
            lang: Language for context prompt ('id' or 'en')
            
        Returns:
            Enhanced prompt with context
        """
        # Get relevant memories
        memories = self.retrieve_relevant_memories(user_id, query)
        
        if not memories:
            return query
            
        # Create a context-enhanced prompt with language support
        if lang == 'en':
            context_prompt = "Based on previous information:\n\n"
            question_prefix = "\nQuestion: "
        else:  # Indonesian (default)
            context_prompt = "Berdasarkan informasi sebelumnya:\n\n"
            question_prefix = "\nPertanyaan: "
        
        # Add memories as context
        for i, memory in enumerate(memories[:3]):  # Limit to top 3 for conciseness
            context_prompt += f"- {memory}\n"
            
        context_prompt += f"{question_prefix}{query}"
        
        return context_prompt
