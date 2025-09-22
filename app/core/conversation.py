"""
Core conversation use case implementation.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..domain.entities import User, Message, AIResponse, RelationshipLevel, EmotionType
from ..domain.repositories import UserRepository, MessageRepository
from ..domain.services import AIService, SentimentService, PersonaService, MemoryService

logger = logging.getLogger(__name__)


class ConversationUseCase:
    """Use case for handling conversations."""
    
    def __init__(
        self,
        user_repo: UserRepository,
        message_repo: MessageRepository,
        ai_service: AIService,
        sentiment_service: SentimentService,
        persona_service: PersonaService,
        memory_service: MemoryService
    ):
        self.user_repo = user_repo
        self.message_repo = message_repo
        self.ai_service = ai_service
        self.sentiment_service = sentiment_service
        self.persona_service = persona_service
        self.memory_service = memory_service
    
    async def process_message(
        self, 
        user_id: int, 
        text: str,
        telegram_user_data: Optional[Dict[str, Any]] = None
    ) -> AIResponse:
        """Process incoming message and generate response."""
        try:
            # Get or create user
            user = await self._get_or_create_user(user_id, telegram_user_data)
            
            # Analyze sentiment
            emotion = await self.sentiment_service.analyze_emotion(text)
            sentiment_score = await self.sentiment_service.get_sentiment_score(text)
            
            # Create user message
            user_message = Message(
                user_id=user_id,
                content=text,
                role="user",
                emotion=emotion,
                sentiment_score=sentiment_score,
                created_at=datetime.now()
            )
            
            # Save user message
            await self.message_repo.save(user_message)
            
            # Update conversation memory
            await self.memory_service.update_context(user_id, user_message)
            
            # Get relevant context
            context = await self.memory_service.get_relevant_context(user_id, text)
            
            # Load persona
            persona = await self.persona_service.load_persona("alya")
            
            # Generate AI response
            ai_response = await self.ai_service.generate_response(
                message=text,
                context=context,
                persona=persona,
                user=user
            )
            
            # Create assistant message
            assistant_message = Message(
                user_id=user_id,
                content=ai_response.content,
                role="assistant",
                emotion=ai_response.emotion,
                created_at=datetime.now(),
                metadata={"tokens_used": ai_response.tokens_used}
            )
            
            # Save assistant message
            await self.message_repo.save(assistant_message)
            
            # Update memory with response
            await self.memory_service.update_context(user_id, assistant_message)
            
            # Apply sliding window
            await self.memory_service.apply_sliding_window(user_id)
            
            # Update user interaction
            await self._update_user_interaction(user, emotion, sentiment_score)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    async def _get_or_create_user(
        self, 
        user_id: int, 
        telegram_data: Optional[Dict[str, Any]]
    ) -> User:
        """Get existing user or create new one."""
        user = await self.user_repo.get_by_id(user_id)
        
        if not user and telegram_data:
            user = User(
                id=user_id,
                username=telegram_data.get("username"),
                first_name=telegram_data.get("first_name"),
                last_name=telegram_data.get("last_name"),
                language_code=telegram_data.get("language_code", "id"),
                created_at=datetime.now(),
                last_interaction=datetime.now()
            )
            user = await self.user_repo.create(user)
        elif user:
            # Update last interaction
            user.last_interaction = datetime.now()
            user = await self.user_repo.update(user)
        
        return user
    
    async def _update_user_interaction(
        self, 
        user: User, 
        emotion: EmotionType, 
        sentiment_score: float
    ) -> None:
        """Update user interaction stats and relationship."""
        user.interaction_count += 1
        
        # Update affection based on sentiment
        if sentiment_score > 0.3:
            user.affection_points += 2
        elif sentiment_score > 0:
            user.affection_points += 1
        elif sentiment_score < -0.3:
            user.affection_points = max(0, user.affection_points - 1)
        
        # Update relationship level based on affection points
        if user.affection_points >= 100 and user.relationship_level.value < 4:
            user.relationship_level = user.relationship_level.__class__(
                user.relationship_level.value + 1
            )
        
        await self.user_repo.update(user)
