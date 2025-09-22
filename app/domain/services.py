"""
Service interfaces for business logic.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .entities import User, Message, AIResponse, EmotionType, PersonaConfig


class AIService(ABC):
    """Interface for AI model interactions."""
    
    @abstractmethod
    async def generate_response(
        self, 
        message: str, 
        context: str, 
        persona: PersonaConfig,
        user: User
    ) -> AIResponse:
        """Generate AI response."""
        pass


class SentimentService(ABC):
    """Interface for sentiment analysis."""
    
    @abstractmethod
    async def analyze_emotion(self, text: str) -> EmotionType:
        """Analyze emotion from text."""
        pass
    
    @abstractmethod
    async def get_sentiment_score(self, text: str) -> float:
        """Get sentiment score (-1 to 1)."""
        pass


class PersonaService(ABC):
    """Interface for persona management."""
    
    @abstractmethod
    async def load_persona(self, name: str) -> PersonaConfig:
        """Load persona configuration."""
        pass
    
    @abstractmethod
    async def get_response_template(
        self, 
        persona: PersonaConfig, 
        emotion: EmotionType,
        language: str = "id"
    ) -> str:
        """Get response template for emotion."""
        pass


class MemoryService(ABC):
    """Interface for conversation memory."""
    
    @abstractmethod
    async def update_context(
        self, 
        user_id: int, 
        message: Message
    ) -> None:
        """Update conversation context."""
        pass
    
    @abstractmethod
    async def get_relevant_context(
        self, 
        user_id: int, 
        query: str
    ) -> str:
        """Get relevant conversation context."""
        pass
    
    @abstractmethod
    async def apply_sliding_window(self, user_id: int) -> None:
        """Apply sliding window to memory."""
        pass
