"""
Handler Registry for Alya Bot.

This module implements a registry pattern for organizing, prioritizing,
and managing Telegram handlers in a structured way.
"""

import logging
from typing import Callable, Dict, List, Any, Optional, Tuple
from enum import Enum
from telegram.ext import (
    Application,
    BaseHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

logger = logging.getLogger(__name__)

class HandlerPriority(Enum):
    """Priority levels for handlers."""
    HIGH = 0
    MEDIUM = 1
    LOW = 2
    
class HandlerType(Enum):
    """Types of handlers supported."""
    COMMAND = "command"
    MESSAGE = "message"
    CALLBACK = "callback"
    MEDIA = "media"
    ADMIN = "admin"
    OTHER = "other"

class HandlerRegistry:
    """Registry for organizing and managing bot handlers."""
    
    def __init__(self):
        """Initialize the handler registry."""
        self.handlers: Dict[HandlerType, Dict[str, Tuple[BaseHandler, HandlerPriority]]] = {
            handler_type: {} for handler_type in HandlerType
        }
        self.is_registered = False
    
    def register_command(
        self, 
        command: str, 
        handler_func: Callable, 
        priority: HandlerPriority = HandlerPriority.MEDIUM,
        admin_only: bool = False
    ) -> None:
        """
        Register a command handler.
        
        Args:
            command: Command name without the slash
            handler_func: Handler function
            priority: Handler priority
            admin_only: Whether this is an admin-only command
        """
        handler = CommandHandler(command, handler_func)
        handler_type = HandlerType.ADMIN if admin_only else HandlerType.COMMAND
        self.handlers[handler_type][command] = (handler, priority)
        logger.debug(f"Registered {'admin' if admin_only else 'command'} handler: /{command}")
    
    def register_message_handler(
        self,
        name: str,
        handler_func: Callable,
        filter_obj: filters.BaseFilter,
        priority: HandlerPriority = HandlerPriority.MEDIUM,
        block: bool = True
    ) -> None:
        """
        Register a message handler with custom filter.
        
        Args:
            name: Unique name for the handler
            handler_func: Handler function
            filter_obj: Filter object to apply
            priority: Handler priority
            block: Whether to block while processing updates
        """
        handler = MessageHandler(filter_obj, handler_func, block=block)
        self.handlers[HandlerType.MESSAGE][name] = (handler, priority)
        logger.debug(f"Registered message handler: {name}")
    
    def register_callback_handler(
        self,
        name: str,
        handler_func: Callable,
        pattern: Optional[str] = None,
        priority: HandlerPriority = HandlerPriority.MEDIUM
    ) -> None:
        """
        Register a callback query handler.
        
        Args:
            name: Unique name for the handler
            handler_func: Handler function
            pattern: Optional regex pattern for filtering callbacks
            priority: Handler priority
        """
        handler = CallbackQueryHandler(handler_func, pattern=pattern)
        self.handlers[HandlerType.CALLBACK][name] = (handler, priority)
        logger.debug(f"Registered callback handler: {name}")
    
    def register_media_handler(
        self,
        name: str,
        handler_func: Callable,
        filter_obj: filters.BaseFilter,
        priority: HandlerPriority = HandlerPriority.MEDIUM
    ) -> None:
        """
        Register a media handler.
        
        Args:
            name: Unique name for the handler
            handler_func: Handler function
            filter_obj: Filter object to apply
            priority: Handler priority
        """
        handler = MessageHandler(filter_obj, handler_func)
        self.handlers[HandlerType.MEDIA][name] = (handler, priority)
        logger.debug(f"Registered media handler: {name}")
    
    def setup_application(self, application: Application) -> None:
        """
        Set up all registered handlers in the application.
        
        Adds handlers to the application in order of priority.
        
        Args:
            application: The Telegram Application instance
        """
        if self.is_registered:
            logger.warning("Handlers already registered to application")
            return
            
        # Process handlers in order of priority and type importance
        handler_order = [
            HandlerType.COMMAND,
            HandlerType.CALLBACK,
            HandlerType.MESSAGE,
            HandlerType.MEDIA,
            HandlerType.ADMIN,
            HandlerType.OTHER
        ]
        
        for handler_type in handler_order:
            # Sort handlers by priority
            sorted_handlers = sorted(
                self.handlers[handler_type].items(),
                key=lambda item: item[1][1].value  # Sort by priority value
            )
            
            # Add handlers to application
            for name, (handler, _) in sorted_handlers:
                application.add_handler(handler)
                logger.debug(f"Added handler to application: {handler_type.value}/{name}")
        
        self.is_registered = True
        logger.info(f"Successfully registered {self._count_handlers()} handlers to application")
    
    def _count_handlers(self) -> int:
        """Count the total number of registered handlers."""
        return sum(len(handlers) for handlers in self.handlers.values())

# Create a singleton instance
handler_registry = HandlerRegistry()

# Convenience exports
command = handler_registry.register_command
message = handler_registry.register_message_handler
callback = handler_registry.register_callback_handler
media = handler_registry.register_media_handler
setup = handler_registry.setup_application
