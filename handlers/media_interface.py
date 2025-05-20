"""
Media Interface for Alya Telegram Bot.

This module serves as an interface between different media handlers
to avoid circular imports while allowing proper code organization.
"""

import logging
import importlib
import asyncio
from typing import Optional, Dict, Any
from telegram import Message, User, Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# Use dynamic imports instead of static imports to avoid circular dependencies
async def process_document_image(update: Update, context: CallbackContext) -> None:
    """
    Process document and image messages (interface function).
    
    Args:
        update: Telegram update object
        context: CallbackContext object
    """
    # Dynamic import to avoid circular dependency
    document_handlers = importlib.import_module('handlers.document_handlers')
    await document_handlers.handle_document_image(update, context)

async def handle_media_trace(message: Message, user: User) -> None:
    """
    Handle document/image analysis (interface function).
    
    Args:
        message: Telegram message with image/document
        user: User who sent the message
    """
    # Dynamic import to avoid circular dependency
    document_handlers = importlib.import_module('handlers.document_handlers')
    await document_handlers.handle_trace_command(message, user)

async def handle_media_sauce(message: Message, user: User) -> None:
    """
    Handle image source search (interface function).
    
    Args:
        message: Telegram message with image
        user: User who sent the message
    """
    # Dynamic import to avoid circular dependency
    document_handlers = importlib.import_module('handlers.document_handlers')
    await document_handlers.handle_sauce_command(message, user)

async def store_media_context_data(
    message: Message, 
    user_id: int, 
    context_type: str, 
    additional_data: Optional[dict] = None
) -> None:
    """
    Store media related context (interface function).
    
    Args:
        message: Message containing media
        user_id: User ID
        context_type: Type of context
        additional_data: Additional context data
    """
    # Dynamic import to avoid circular dependency
    trace_handlers = importlib.import_module('handlers.trace_handlers')
    await trace_handlers.store_media_context(message, user_id, context_type, additional_data)
