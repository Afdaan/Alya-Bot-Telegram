"""
Repository interfaces for data access.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .entities import User, Message, ConversationContext


class UserRepository(ABC):
    """Interface for user data access."""
    
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user."""
        pass
    
    @abstractmethod
    async def get_or_create(self, user_id: int, **kwargs) -> User:
        """Get existing user or create new one."""
        pass


class MessageRepository(ABC):
    """Interface for message data access."""
    
    @abstractmethod
    async def save(self, message: Message) -> Message:
        """Save a message."""
        pass
    
    @abstractmethod
    async def get_recent_messages(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for a user."""
        pass
    
    @abstractmethod
    async def get_conversation_history(
        self, 
        user_id: int, 
        hours: int = 24
    ) -> List[Message]:
        """Get conversation history within time period."""
        pass


class MemoryRepository(ABC):
    """Interface for RAG memory system."""
    
    @abstractmethod
    async def store_context(
        self, 
        user_id: int, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """Store conversation context."""
        pass
    
    @abstractmethod
    async def search_similar(
        self, 
        user_id: int, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar contexts."""
        pass
    
    @abstractmethod
    async def get_conversation_context(
        self, 
        user_id: int
    ) -> Optional[ConversationContext]:
        """Get current conversation context."""
        pass
