"""
Message Handlers for Alya Telegram Bot.

This module provides handlers for processing text messages and generating
AI responses with proper context handling.
"""

import logging
import random
import asyncio
import time
from typing import Dict, Any, Optional, List, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from config.settings import (
    CHAT_PREFIX, 
    DEFAULT_LANGUAGE, 
    SUPPORTED_LANGUAGES,
    DEVELOPER_IDS
)
from utils.formatters import format_markdown_response
from utils.rate_limiter import limiter, rate_limited
from utils.language_handler import get_language  # Kita udah fix function ini
from utils.context_manager import context_manager
from utils.commands import command_detector
from core.models import generate_chat_response
from core.personas import persona_manager, get_persona_context

# Setup logger
logger = logging.getLogger(__name__)

# Command patterns untuk chat
CHAT_COMMAND_PATTERN = r"^!ai\s+"

@rate_limited(limiter)
async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Handle incoming text messages with context-aware AI responses.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.message or not update.message.text:
        return

    message = update.message
    message_text = message.text
    user = update.effective_user
    
    # Setup user info
    user_info = {
        'user_id': user.id,
        'username': user.username or "Unknown",
        'first_name': user.first_name or "User",
        'chat_id': message.chat_id,
        'is_group': message.chat.type != "private"
    }
    
    # Check if message is for AI in group chat (!ai prefix)
    is_private = message.chat.type == "private"
    should_process = is_private or message_text.lower().startswith(CHAT_PREFIX.lower())
    
    if not should_process:
        # Potential passive monitoring for mentions (@bot_username)
        if (context.bot.username and 
            f"@{context.bot.username}" in message_text):
            # Bot was mentioned, log but don't necessarily respond
            logger.info(f"Bot mentioned in group {message.chat_id} by {user.id}")
        return

    # Remove AI prefix for group chats
    if not is_private and message_text.lower().startswith(CHAT_PREFIX.lower()):
        message_text = message_text[len(CHAT_PREFIX):].strip()
        if not message_text:  # Empty after removing prefix
            await message.reply_text("Kamu ingin bicara apa? ✨")
            return

    # Check if it's a recognized command
    command_type = command_detector.detect_command_type(message_text)
    if command_type:
        # This is actually a command masquerading as a message
        # Log and ignore - will be handled by command handlers
        logger.debug(f"Detected {command_type} command pattern, ignoring in message handler")
        return
    
    # Check message length
    if len(message_text) < 2:  # Too short to process
        await message.reply_text("Hmm? Alya tidak mengerti pesan yang terlalu pendek... 🤔")
        return

    # Send typing indicator
    await message.chat.send_action('typing')
    
    try:
        # Get language setting - FIX: Pass context object directly
        language = context.bot_data.get("language", DEFAULT_LANGUAGE)
        
        # Get persona based on user settings
        persona_type = context.user_data.get("persona", "tsundere")
        persona_context = get_persona_context(persona_type)
        
        # Get relevant context for this conversation
        user_context = context_manager.recall_relevant_context(
            user.id, 
            message_text,
            chat_id=message.chat_id
        )
        
        # Check roasting mode settings
        is_roasting = False
        memory_state = user_context.get('memory_state', {})
        if memory_state.get('is_roasting'):
            is_roasting = True
            
        # Generate response with appropriate context
        response_text = await generate_chat_response(
            message_text, 
            user.id, 
            context=context,
            persona_context=persona_context
        )
        
        # Update memory state after roast mode
        if is_roasting:
            # Reset roast mode after one message 
            # (no longer using it = reset the flag)
            memory_state['is_roasting'] = False
            memory_state['should_reset_memory_state'] = True
            memory_state['timestamp'] = time.time()
            context_manager.save_context(user.id, message.chat_id, 'memory_state', memory_state)
        
        # Format the message for proper display
        formatted_response = format_markdown_response(
            response_text,
            username=user.first_name
        )
        
        # Split if too long (telegram limit)
        if len(formatted_response) > 4000:
            segments = []
            current_segment = ""
            
            # Split by paragraphs
            paragraphs = formatted_response.split("\n\n")
            for p in paragraphs:
                if len(current_segment) + len(p) + 2 > 4000:
                    segments.append(current_segment)
                    current_segment = p
                else:
                    current_segment += "\n\n" + p if current_segment else p
                    
            if current_segment:
                segments.append(current_segment)
                
            # Send segments
            for i, segment in enumerate(segments):
                if i == 0:  # First message as reply
                    await message.reply_text(
                        segment, 
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:  # Following messages just sent to same chat
                    await context.bot.send_message(
                        chat_id=message.chat_id,
                        text=segment,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
        else:
            # Send single message response
            await message.reply_text(
                formatted_response,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
    except asyncio.TimeoutError:
        # API timeout response
        timeout_message = "Hmm, Alya membutuhkan waktu terlalu lama... Bisa coba lagi nanti? 🥺"
        await message.reply_text(timeout_message)
        
    except Exception as e:
        # General error message with safe formatting
        logger.error(f"Error generating response: {e}")
        error_message = "Gomen, terjadi kesalahan saat memproses pesan... 🙏"
        await message.reply_text(error_message)

# ... existing code ...