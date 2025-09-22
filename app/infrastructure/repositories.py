"""
Repository implementations using SQLAlchemy.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from ..domain.entities import User, Message, ConversationContext, RelationshipLevel, EmotionType
from ..domain.repositories import UserRepository, MessageRepository, MemoryRepository
from .database import UserModel, MessageModel, ConversationContextModel, create_session_factory

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""
    
    def __init__(self):
        self.session_factory = create_session_factory()
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.session_factory() as session:
            user_model = session.query(UserModel).filter(UserModel.id == user_id).first()
            if user_model:
                return self._to_entity(user_model)
            return None
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        with self.session_factory() as session:
            user_model = self._to_model(user)
            session.add(user_model)
            session.commit()
            session.refresh(user_model)
            return self._to_entity(user_model)
    
    async def update(self, user: User) -> User:
        """Update existing user."""
        with self.session_factory() as session:
            user_model = session.query(UserModel).filter(UserModel.id == user.id).first()
            if user_model:
                # Update fields
                user_model.username = user.username
                user_model.first_name = user.first_name
                user_model.last_name = user.last_name
                user_model.language_code = user.language_code
                user_model.relationship_level = user.relationship_level.value
                user_model.affection_points = user.affection_points
                user_model.interaction_count = user.interaction_count
                user_model.is_admin = user.is_admin
                user_model.is_active = user.is_active
                user_model.last_interaction = user.last_interaction
                user_model.preferences = user.preferences
                
                session.commit()
                session.refresh(user_model)
                return self._to_entity(user_model)
            return user
    
    async def get_or_create(self, user_id: int, **kwargs) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_id(user_id)
        if not user:
            user = User(id=user_id, **kwargs)
            user = await self.create(user)
        return user
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert model to entity."""
        return User(
            id=model.id,
            username=model.username,
            first_name=model.first_name,
            last_name=model.last_name,
            language_code=model.language_code,
            relationship_level=RelationshipLevel(model.relationship_level),
            affection_points=model.affection_points,
            interaction_count=model.interaction_count,
            is_admin=model.is_admin,
            is_active=model.is_active,
            created_at=model.created_at,
            last_interaction=model.last_interaction,
            preferences=model.preferences or {}
        )
    
    def _to_model(self, entity: User) -> UserModel:
        """Convert entity to model."""
        return UserModel(
            id=entity.id,
            username=entity.username,
            first_name=entity.first_name,
            last_name=entity.last_name,
            language_code=entity.language_code,
            relationship_level=entity.relationship_level.value,
            affection_points=entity.affection_points,
            interaction_count=entity.interaction_count,
            is_admin=entity.is_admin,
            is_active=entity.is_active,
            created_at=entity.created_at,
            last_interaction=entity.last_interaction,
            preferences=entity.preferences
        )


class SQLAlchemyMessageRepository(MessageRepository):
    """SQLAlchemy implementation of MessageRepository."""
    
    def __init__(self):
        self.session_factory = create_session_factory()
    
    async def save(self, message: Message) -> Message:
        """Save a message."""
        with self.session_factory() as session:
            message_model = self._to_model(message)
            session.add(message_model)
            session.commit()
            session.refresh(message_model)
            return self._to_entity(message_model)
    
    async def get_recent_messages(self, user_id: int, limit: int = 10) -> List[Message]:
        """Get recent messages for a user."""
        with self.session_factory() as session:
            messages = (
                session.query(MessageModel)
                .filter(MessageModel.user_id == user_id)
                .order_by(desc(MessageModel.created_at))
                .limit(limit)
                .all()
            )
            return [self._to_entity(msg) for msg in messages]
    
    async def get_conversation_history(self, user_id: int, hours: int = 24) -> List[Message]:
        """Get conversation history within time period."""
        with self.session_factory() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            messages = (
                session.query(MessageModel)
                .filter(
                    and_(
                        MessageModel.user_id == user_id,
                        MessageModel.created_at >= cutoff_time
                    )
                )
                .order_by(MessageModel.created_at)
                .all()
            )
            return [self._to_entity(msg) for msg in messages]
    
    def _to_entity(self, model: MessageModel) -> Message:
        """Convert model to entity."""
        emotion = None
        if model.emotion:
            try:
                emotion = EmotionType(model.emotion)
            except ValueError:
                pass
        
        return Message(
            id=model.id,
            user_id=model.user_id,
            content=model.content,
            role=model.role,
            emotion=emotion,
            sentiment_score=model.sentiment_score,
            created_at=model.created_at,
            metadata=model.metadata or {}
        )
    
    def _to_model(self, entity: Message) -> MessageModel:
        """Convert entity to model."""
        return MessageModel(
            id=entity.id,
            user_id=entity.user_id,
            content=entity.content,
            role=entity.role,
            emotion=entity.emotion.value if entity.emotion else None,
            sentiment_score=entity.sentiment_score,
            created_at=entity.created_at,
            metadata=entity.metadata
        )


class SQLAlchemyMemoryRepository(MemoryRepository):
    """SQLAlchemy implementation of MemoryRepository."""
    
    def __init__(self):
        self.session_factory = create_session_factory()
    
    async def store_context(self, user_id: int, content: str, metadata: Dict[str, Any]) -> None:
        """Store conversation context."""
        with self.session_factory() as session:
            context = ConversationContextModel(
                user_id=user_id,
                content=content,
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            session.add(context)
            session.commit()
    
    async def search_similar(self, user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar contexts."""
        # This is a simple text-based search
        # In production, you would use vector similarity search
        with self.session_factory() as session:
            contexts = (
                session.query(ConversationContextModel)
                .filter(ConversationContextModel.user_id == user_id)
                .order_by(desc(ConversationContextModel.updated_at))
                .limit(limit * 2)  # Get more to filter
                .all()
            )
            
            # Simple text matching (replace with vector search in production)
            results = []
            query_lower = query.lower()
            for context in contexts:
                if any(word in context.content.lower() for word in query_lower.split()):
                    results.append({
                        "content": context.content,
                        "similarity": 0.8,  # Placeholder
                        "metadata": context.metadata
                    })
                    if len(results) >= limit:
                        break
            
            return results
    
    async def get_conversation_context(self, user_id: int) -> Optional[ConversationContext]:
        """Get current conversation context."""
        with self.session_factory() as session:
            context_model = (
                session.query(ConversationContextModel)
                .filter(ConversationContextModel.user_id == user_id)
                .order_by(desc(ConversationContextModel.updated_at))
                .first()
            )
            
            if context_model:
                return ConversationContext(
                    user_id=user_id,
                    topics=context_model.topics or [],
                    summary=context_model.summary
                )
            return None
