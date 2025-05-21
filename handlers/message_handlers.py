"""
Message Handlers for Alya Telegram Bot.

This module handles regular chat messages, mentions, and non-command interactions
with natural language understanding instead of regex patterns.
"""

import logging
import asyncio
import re
import random
from typing import List, Dict, Any, Optional, Tuple

from telegram import Update, Message, User
from telegram.constants import ParseMode, ChatAction
from telegram.ext import CallbackContext, Application, MessageHandler, filters

from config.settings import (
    CHAT_PREFIX, 
    DEFAULT_LANGUAGE,
    GROUP_CHAT_REQUIRES_PREFIX,
    ADDITIONAL_PREFIXES,
    DEVELOPER_IDS
)
from core.models import generate_chat_response
from core.personas import get_persona_context, persona_manager
from core.emotion_system import update_emotion, enhance_response
from core.mood_manager import mood_manager, MoodType
from utils.formatters import format_markdown_response
from utils.rate_limiter import limiter
from utils.context_manager import context_manager
from utils.language_handler import detect_language

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Main message handler that routes to appropriate sub-handlers.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.effective_user or not update.message or not update.message.text:
        return
        
    message = update.message
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    # Filter out non-private chats without prefixes/mentions if required
    if GROUP_CHAT_REQUIRES_PREFIX and update.effective_chat and not update.effective_chat.type == "private":
        # Check for prefixes
        has_prefix = any(message.text.lower().startswith(prefix.lower()) for prefix in ADDITIONAL_PREFIXES)
        # Check for mentions (including edited messages)
        mentions_bot = message.entities and any(
            entity.type == "mention" and message.text[entity.offset:entity.offset + entity.length].lower() == "@alyabot"
            for entity in message.entities
        )
        
        if not has_prefix and not mentions_bot:
            # Ignore messages without prefix or mention in groups
            return
    
    # Process the message
    await process_chat_message(update, context)

async def process_chat_message(update: Update, context: CallbackContext, query: Optional[str] = None) -> None:
    """Process incoming chat message and generate Alya's response."""
    try:
        user = update.effective_user
        message_text = query if query else update.message.text

        # Get conversation context
        conversation_context = context_manager.recall_relevant_context(user.id, message_text)
        username = format_markdown_response(user.first_name)  # Escape the username

        # Generate AI response
        ai_response = await generate_chat_response(
            message=message_text,
            username=username,  # Pass the escaped username
            user_id=user.id,
            context_data=conversation_context
        )

        # Format response with MarkdownV2 safety
        safe_response = format_markdown_response(ai_response, username=username)

        await update.message.reply_text(
            safe_response,
            parse_mode=ParseMode.MARKDOWN_V2
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "Gomenasai\\! Ada error saat memproses pesan\\.\\.\\. 😔",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def add_message_to_history(user_id: int, chat_id: int, message: Message) -> None:
    """
    Add user message to chat history.
    
    Args:
        user_id: User ID
        chat_id: Chat ID
        message: Message object
    """
    try:
        # Get message content and metadata
        text = message.text or ""
        message_id = message.message_id
        
        # Store message in history
        context_manager.add_chat_message(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            role="user",
            content=text
        )
    except Exception as e:
        logger.error(f"Error adding message to history: {e}")

async def add_response_to_history(user_id: int, chat_id: int, message: Message) -> None:
    """
    Add bot response to chat history.
    
    Args:
        user_id: User ID
        chat_id: Chat ID
        message: Message object
    """
    try:
        # Get message content and metadata
        text = message.text or ""
        message_id = message.message_id
        
        # Strip markdown formatting for storage
        clean_text = re.sub(r'\\(.)', r'\1', text)  # Remove escape characters
        
        # Store message in history
        context_manager.add_chat_message(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            role="assistant",
            content=clean_text
        )
    except Exception as e:
        logger.error(f"Error adding response to history: {e}")

def register_message_handlers(app: Application) -> None:
    """
    Register message handlers with the application.
    
    Args:
        app: Telegram application instance
    """
    # Add handler for regular text messages
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("Message handlers registered successfully")