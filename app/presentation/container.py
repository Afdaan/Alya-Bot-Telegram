"""
Dependency injection container for the application.
"""
import logging
from typing import Dict, Any

from ..core.conversation import ConversationUseCase
from ..infrastructure import (
    SQLAlchemyUserRepository,
    SQLAlchemyMessageRepository,
    SQLAlchemyMemoryRepository,
    GeminiAIService,
    HuggingFaceSentimentService,
    YAMLPersonaService,
    RAGMemoryService
)
from .handlers import TelegramHandlers

logger = logging.getLogger(__name__)


class DIContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services."""
        logger.info("Initializing services...")
        
        # Repositories
        self._services['user_repository'] = SQLAlchemyUserRepository()
        self._services['message_repository'] = SQLAlchemyMessageRepository()
        self._services['memory_repository'] = SQLAlchemyMemoryRepository()
        
        # External services
        self._services['ai_service'] = GeminiAIService()
        self._services['sentiment_service'] = HuggingFaceSentimentService()
        self._services['persona_service'] = YAMLPersonaService()
        
        # Memory service
        self._services['memory_service'] = RAGMemoryService(
            message_repo=self._services['message_repository'],
            memory_repo=self._services['memory_repository']
        )
        
        # Use cases
        self._services['conversation_use_case'] = ConversationUseCase(
            user_repo=self._services['user_repository'],
            message_repo=self._services['message_repository'],
            ai_service=self._services['ai_service'],
            sentiment_service=self._services['sentiment_service'],
            persona_service=self._services['persona_service'],
            memory_service=self._services['memory_service']
        )
        
        # Handlers
        self._services['telegram_handlers'] = TelegramHandlers(
            conversation_use_case=self._services['conversation_use_case']
        )
        
        logger.info("All services initialized successfully")
    
    def get(self, service_name: str) -> Any:
        """Get service by name."""
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' not found")
        return self._services[service_name]
    
    def get_telegram_handlers(self) -> TelegramHandlers:
        """Get Telegram handlers."""
        return self.get('telegram_handlers')
