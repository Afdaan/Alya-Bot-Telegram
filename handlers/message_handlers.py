"""
Message Handler module for Alya Telegram Bot.

This module processes incoming messages, handles persona selection,
typing indicators, and response formatting/delivery.
"""

import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import CallbackContext
from datetime import datetime

from config.settings import CHAT_PREFIX
from core.models import generate_chat_response
from core.personas import get_persona_context
from utils.formatters import format_markdown_response, split_long_message
from utils.commands import is_roast_command
from utils.language_handler import get_language, get_response

logger = logging.getLogger(__name__)

# =========================
# Typing Indicator
# =========================

async def send_typing_action(context, chat_id, duration=3):
    """
    Send typing action periodically to keep it active for longer periods.
    
    Args:
        context: CallbackContext
        chat_id: Target chat ID
        duration: How long to maintain typing indicator (seconds)
    """
    end_time = asyncio.get_event_loop().time() + duration
    while asyncio.get_event_loop().time() < end_time:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(4.5)  # Typing action lasts ~5 seconds, refresh before it expires

# =========================
# Message Processing
# =========================

async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Handle incoming messages with persona selection and response generation.
    
    Args:
        update: Telegram Update object
        context: CallbackContext for state management
    """
    try:
        # Basic validation
        if not update.message or not update.message.text:
            return

        message_text = update.message.text
        chat_type = update.message.chat.type
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Extract mentioned username for proper handling - IMPROVED DETECTION
        telegram_mention = None
        mentioned_username = None
        
        # First detect if there are any @username mentions in the message
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":  # This is a @username mention
                    telegram_mention = message_text[entity.offset:entity.offset + entity.length]
                    # Extract username without @ for potential use in message
                    mentioned_username = telegram_mention[1:]  # Remove the @ symbol
                    logger.info(f"Detected mention: {telegram_mention}, username: {mentioned_username}")
                    break

        # Handle special commands
        
        # Handle search command with "!search" prefix
        if message_text.lower().startswith('!search'):
            args = message_text.split(' ')[1:]
            context.args = args
            from handlers.command_handlers import handle_search
            return await handle_search(update, context)

        # Check for group message prefix
        if chat_type in ['group', 'supergroup']:
            if not message_text.startswith(CHAT_PREFIX):
                return
            message_text = message_text.replace(CHAT_PREFIX, "", 1).strip()

        if not message_text:
            return
            
        # Get the current language setting from context
        language = get_language(context)
            
        # Start typing indicator in background task that keeps refreshing
        typing_task = asyncio.create_task(send_typing_action(context, chat_id, 30))  # Up to 30 seconds of typing
        
        # Select appropriate persona based on command type, passing language
        persona = select_persona(update.message, language)
        
        # Generate response with persona context and timeout handling
        try:
            response = await asyncio.wait_for(
                generate_chat_response(
                    message_text,
                    user.id,
                    context=context,
                    persona_context=persona
                ),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Response generation timed out for user {user.id}")
            # Cancel typing indicator before sending error
            typing_task.cancel()
            
            # Get localized timeout message
            timeout_msg = get_response("timeout", context)
            
            await update.message.reply_text(
                timeout_msg,
                parse_mode='MarkdownV2'
            )
            return

        # Format and send response
        safe_response = format_markdown_response(
            response,
            username=user.first_name,           # User yang mengirim pesan (untuk sapaan)
            telegram_username=None,             # Kita tidak perlu menampilkan link username pengirim
            mentioned_username=mentioned_username,
            mentioned_text=telegram_mention    # Mention text asli untuk diteruskan
        )

        # Add debug info if debug mode is on
        if context.bot_data.get('debug_mode', False):
            debug_info = (
                "*📊 Debug Info*\n"
                f"👤 User ID: `{user.id}`\n"
                f"📝 Username: `@{user.username or 'None'}`\n"
                f"💬 Chat ID: `{update.effective_chat.id}`\n"
                f"💭 Chat Type: `{chat_type}`\n"
                f"📨 Message ID: `{update.message.message_id}`\n"
                f"⏰ Time: `{update.message.date.strftime('%H:%M:%S')}`\n\n"
                f"*💌 Message:*\n"
                f"`{message_text}`\n\n"
                f"*🤖 Response:*\n"
            ) + safe_response
            
            if telegram_mention:
                debug_info += f"\n\n*🏷️ Mention:* {telegram_mention}"
            
            safe_response = debug_info

        # Cancel the typing task before sending response
        typing_task.cancel()
        
        # Send the response, split if too long
        await send_formatted_response(update, safe_response)

    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        
        # Use localized error message
        error_msg = get_response("error", context)
        
        await update.message.reply_text(
            error_msg,
            parse_mode='MarkdownV2'
        )

# =========================
# Helper Functions
# =========================

def select_persona(message, language="id"):
    """
    Select appropriate persona based on message content.
    
    Args:
        message: Telegram message object
        language: Current language setting
        
    Returns:
        Appropriate persona context string
    """
    # Check for roasting command
    is_roast, target, is_github, keywords, user_info = is_roast_command(message)
    
    if is_roast:
        return get_persona_context("toxic", language)
        
    # If user asks for detail/advanced, or question is long, use SMART_PERSONA
    message_text = message.text
    info_keywords = [
        'jadwal', 'siapa', 'apa', 'dimana', 'kapan', 'bagaimana', 
        'mengapa', 'cara', 'berapa', 'info', 'cari', 'carikan', 
        'detail', '-d', '--detail'
    ]
    is_info_query = any(keyword in message_text.lower() for keyword in info_keywords)
    is_advanced = (
        'detail' in message_text.lower() or
        '-d' in message_text.lower() or
        '--detail' in message_text.lower() or
        len(message_text.split()) > 12  # consider advanced if question is long
    )
    
    if is_info_query and is_advanced:
        return get_persona_context("smart", language) 
    
    # Default persona
    return get_persona_context("waifu", language)

async def send_formatted_response(update, response_text):
    """
    Send formatted response, splitting if necessary.
    
    Args:
        update: Telegram Update object
        response_text: The formatted response text
    """
    if len(response_text) > 4000:
        parts = split_long_message(response_text, 4000)
        for i, part in enumerate(parts):
            await update.message.reply_text(
                part,
                reply_to_message_id=update.message.message_id if i == 0 else None,
                parse_mode='MarkdownV2'
            )
            await asyncio.sleep(0.5)  # Delay to prevent flood
    else:
        await update.message.reply_text(
            response_text,
            reply_to_message_id=update.message.message_id,
            parse_mode='MarkdownV2'
        )