"""
Message Handlers for Alya Telegram Bot.

This module handles all text messages sent to the bot,
with proper differentiation between private and group chats.
"""

import logging
from typing import Dict, Any, Optional

from telegram import Update, Chat
from telegram.ext import CallbackContext

from core.models import generate_response, generate_chat_response, fix_roleplay_format  
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.context_manager import context_manager
from utils.rate_limiter import limiter
from utils.commands import command_detector
from core.personas import get_persona_context, persona_manager
from config.settings import (
    CHAT_PREFIX,
    ADDITIONAL_PREFIXES,
    GROUP_CHAT_REQUIRES_PREFIX
)

logger = logging.getLogger(__name__)

# All valid prefixes for better detection
ALL_VALID_PREFIXES = [CHAT_PREFIX.lower()] + [prefix.lower() for prefix in ADDITIONAL_PREFIXES]

async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Main message handler that routes messages to appropriate handlers.
    
    Args:
        update: Update object containing the message
        context: Context object for storing data
    """
    # Skip command messages
    if update.message and update.message.text and update.message.text.startswith('/'):
        return
    
    # Validate update has message with text
    if not update.message or not update.message.text:
        return
        
    message_text = update.message.text
    chat_type = update.effective_chat.type
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Process different chat types
    if chat_type == Chat.PRIVATE:
        # Private chat - handle all messages
        await process_chat_message(update, context, message_text)
    else:
        # Group chat - only respond to specific prefixes or mentions
        # This is now primarily handled by core/bot.py with dedicated handlers
        # This is just a fallback for direct mentions
        
        # Check for mention
        if context.bot and context.bot.username:
            bot_mention = f"@{context.bot.username}"
            if bot_mention.lower() in message_text.lower():
                # Remove mention from text
                processed_text = message_text.replace(bot_mention, "", 1).strip()
                await process_chat_message(update, context, processed_text)

async def process_chat_message(
    update: Update, 
    context: CallbackContext, 
    message_text: str,
    is_group: bool = False
) -> None:
    """
    Process chat message and generate AI response.
    
    Args:
        update: Telegram update object
        context: Callback context
        message_text: Clean message text to process
        is_group: Whether this is a group chat message
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Skip empty messages
    if not message_text or len(message_text.strip()) < 2:
        if not is_group:
            await update.message.reply_text(
                "Hmm? Alya tidak mengerti pesan yang terlalu pendek... 🤔"
            )
        return
    
    # Check rate limit for regular chat
    allowed, wait_time = await limiter.acquire_with_feedback(user.id)
    if not allowed:
        logger.info(f"Rate limit hit for user {user.id}, wait time: {wait_time:.1f}s")
        return
    
    # Send typing indicator
    await update.message.chat.send_chat_action("typing")
    
    # Get user's current persona
    user_persona = persona_manager.get_current_persona(user.id)
    
    # Get persona context for enhanced responses
    persona_context = get_persona_context(user_persona)
    
    try:
        # Generate AI response with persona context
        response = await generate_chat_response(
            message=message_text,
            user_id=user.id,
            context=context,
            persona_context=persona_context
        )
        
        # Format and send response
        formatted_response = format_markdown_response(response, username=user.first_name)
        await update.message.reply_text(formatted_response, parse_mode='MarkdownV2')
        
        # Store message in context
        context_manager.add_message_to_history(
            user_id=user.id,
            role="user",
            content=message_text,
            chat_id=chat_id
        )
        
        context_manager.add_message_to_history(
            user_id=user.id,
            role="assistant",
            content=response,
            chat_id=chat_id,
            message_id=update.message.message_id
        )
        
    except Exception as e:
        # Determine context-appropriate error message
        context_type = "grup" if is_group else "pesan"
        logger.error(f"Error generating response ({context_type}): {e}")
        await update.message.reply_text(
            f"Gomennasai\\! Ada error saat memproses {context_type}\\. Error: {escape_markdown_v2(str(e)[:50])}",
            parse_mode='MarkdownV2'
        )