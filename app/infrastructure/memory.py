"""
Memory service implementation with RAG support.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import numpy as np
from sentence_transformers import SentenceTransformer

from ..domain.entities import Message, ConversationContext
from ..domain.services import MemoryService
from ..domain.repositories import MessageRepository, MemoryRepository
from config.settings import settings

logger = logging.getLogger(__name__)


class RAGMemoryService(MemoryService):
    """RAG-based memory service implementation."""
    
    def __init__(
        self, 
        message_repo: MessageRepository,
        memory_repo: MemoryRepository
    ):
        self.message_repo = message_repo
        self.memory_repo = memory_repo
        self.embedding_model = None
        self._load_embedding_model()
    
    def _load_embedding_model(self):
        """Load sentence transformer model for embeddings."""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None
    
    async def update_context(self, user_id: int, message: Message) -> None:
        """Update conversation context."""
        try:
            # Store the message content with embedding
            if self.embedding_model and message.content:
                embedding = self.embedding_model.encode(message.content).tolist()
                await self.memory_repo.store_context(
                    user_id=user_id,
                    content=message.content,
                    metadata={
                        "role": message.role,
                        "emotion": message.emotion.value if message.emotion else None,
                        "sentiment_score": message.sentiment_score,
                        "embedding": embedding,
                        "timestamp": message.created_at.isoformat() if message.created_at else None
                    }
                )
            
        except Exception as e:
            logger.error(f"Error updating context: {e}")
    
    async def get_relevant_context(self, user_id: int, query: str) -> str:
        """Get relevant conversation context using RAG."""
        try:
            # Get recent messages for immediate context
            recent_messages = await self.message_repo.get_recent_messages(
                user_id, 
                limit=settings.sliding_window_size
            )
            
            # Build immediate context
            context_parts = []
            
            # Add recent conversation
            if recent_messages:
                context_parts.append("**Percakapan Terakhir:**")
                for msg in reversed(recent_messages[-5:]):  # Last 5 messages
                    role = "User" if msg.role == "user" else "Alya"
                    context_parts.append(f"{role}: {msg.content}")
            
            # Search for similar past conversations
            if self.embedding_model:
                similar_contexts = await self.memory_repo.search_similar(
                    user_id, 
                    query, 
                    limit=settings.rag_max_results
                )
                
                if similar_contexts:
                    context_parts.append("\n**Konteks Relevan dari Percakapan Sebelumnya:**")
                    for ctx in similar_contexts:
                        context_parts.append(f"- {ctx['content']}")
            
            return "\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return ""
    
    async def apply_sliding_window(self, user_id: int) -> None:
        """Apply sliding window to memory."""
        try:
            # Get conversation history
            messages = await self.message_repo.get_conversation_history(
                user_id, 
                hours=24
            )
            
            # If we have too many messages, summarize older ones
            if len(messages) > settings.max_memory_messages:
                # Keep recent messages, summarize older ones
                recent_messages = messages[-settings.sliding_window_size:]
                older_messages = messages[:-settings.sliding_window_size]
                
                # Create summary of older messages
                if older_messages:
                    summary = self._create_summary(older_messages)
                    await self.memory_repo.store_context(
                        user_id=user_id,
                        content=f"Summary: {summary}",
                        metadata={
                            "type": "summary",
                            "message_count": len(older_messages),
                            "timestamp": datetime.now().isoformat()
                        }
                    )
            
        except Exception as e:
            logger.error(f"Error applying sliding window: {e}")
    
    def _create_summary(self, messages: List[Message]) -> str:
        """Create a summary of conversation messages."""
        # Simple extractive summary
        # In production, you might want to use a summarization model
        
        user_messages = [msg.content for msg in messages if msg.role == "user"]
        assistant_messages = [msg.content for msg in messages if msg.role == "assistant"]
        
        summary_parts = []
        
        if user_messages:
            # Get key topics from user messages
            topics = self._extract_key_topics(user_messages)
            if topics:
                summary_parts.append(f"User talked about: {', '.join(topics)}")
        
        if assistant_messages:
            # Get sample responses
            if len(assistant_messages) > 2:
                summary_parts.append(f"Alya responded {len(assistant_messages)} times with various emotions")
        
        return ". ".join(summary_parts) if summary_parts else "General conversation"
    
    def _extract_key_topics(self, messages: List[str]) -> List[str]:
        """Extract key topics from messages."""
        # Simple keyword extraction
        # In production, you might want to use NLP techniques
        
        common_words = set(['aku', 'kamu', 'saya', 'anda', 'dia', 'mereka', 'yang', 'dan', 'atau', 'tapi'])
        
        all_words = []
        for message in messages:
            words = message.lower().split()
            words = [w for w in words if len(w) > 3 and w not in common_words]
            all_words.extend(words)
        
        # Count frequency
        word_count = {}
        for word in all_words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # Get top topics
        topics = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
        return [topic[0] for topic in topics if topic[1] > 1]
