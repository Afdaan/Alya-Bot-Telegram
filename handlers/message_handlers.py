"""
Message Handler module for Alya Telegram Bot.

This module processes incoming messages, handles persona selection,
typing indicators, and response formatting/delivery.
"""

import logging
import asyncio
import re  # Tambahkan import re yang hilang
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

# Import tambahan
import time
from utils.context_manager import context_manager

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
        
        # Get previous context jika ada
        user_id = user.id
        chat_id = update.effective_chat.id
        prev_context = context_manager.get_context(user_id, chat_id)
        prev_history = context_manager.get_chat_history(user_id, chat_id, 10)  # Increase from 5 to 10 messages
        
        # Enhance prompt dengan context bila ada
        enhanced_message = message_text
        
        if prev_context or prev_history:
            context_info = []
            
            # Extract personal information from history
            personal_info = extract_personal_info(prev_history)
            if personal_info:
                context_info.append("Important personal information about the user:")
                for key, value in personal_info.items():
                    context_info.append(f"User's {key}: {value}")
            
            # Check commands contexts - keep existing code
            if prev_context:
                # Check recent sauce command context
                if 'sauce' in prev_context and int(time.time()) - prev_context['sauce'].get('timestamp', 0) < 3600:
                    context_info.append("User recently used !sauce command to find the source of an anime image.")
                
                # Check recent trace command context
                if 'trace' in prev_context and int(time.time()) - prev_context['trace'].get('timestamp', 0) < 3600:
                    media_type = prev_context['trace'].get('media_type', 'content')
                    context_info.append(f"User recently used !trace command to analyze {media_type}.")
                    if prev_context['trace'].get('response_summary'):
                        context_info.append(f"Your analysis summary: {prev_context['trace']['response_summary']}")
                
                # Check recent search command context
                if 'search' in prev_context and int(time.time()) - prev_context['search'].get('timestamp', 0) < 3600:
                    context_info.append(f"User recently searched for: '{prev_context['search'].get('query', '')}'")
                
            # Improve chat history formatting with clear separation
            if prev_history:
                context_info.append("\nRecent conversation history:")
                for entry in prev_history:
                    role = "User" if entry['role'] == 'user' else "You (Alya)"
                    # Include full content for better context
                    context_info.append(f"{role}: {entry['content']}")
                
            # Build enhanced prompt with more directive for memory
            if context_info:
                context_string = "\n".join(context_info)
                enhanced_message = (
                    f"[CONTEXT - IMPORTANT MEMORY INFORMATION]\n{context_string}\n[/CONTEXT]\n\n"
                    f"Remember all information above, especially personal details. "
                    f"The user expects you to remember these details.\n\n"
                    f"User's current message: {message_text}"
                )
        
        # Generate response dengan enhanced prompt
        try:
            response = await asyncio.wait_for(
                generate_chat_response(
                    enhanced_message,  # Use context-enhanced message
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
        
        # Save current message & response ke history
        context_manager.add_chat_message(user_id, chat_id, update.message.message_id, 'user', message_text)
        
        # Extract and save important personal info before saving response
        extracted_info = extract_important_facts(message_text, response)
        if extracted_info:
            for info_type, info_value in extracted_info.items():
                context_data = {
                    'command': 'personal_info',
                    'timestamp': int(time.time()),
                    'info_type': info_type,
                    'value': info_value,
                }
                context_manager.save_context(user_id, chat_id, f"personal_{info_type}", context_data)
        
        context_manager.add_chat_message(user_id, chat_id, 0, 'assistant', response)

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

def extract_personal_info(chat_history):
    """Extract personal information from chat history"""
    personal_info = {}
    
    # Define patterns to identify personal info
    patterns = {
        'birthday': [
            r'ulang\s*tahun[ku|saya|gw]\s*(?:adalah|itu|pada)?\s*tanggal\s*(\d{1,2}\s*[a-zA-Z]+)',
            r'tanggal\s*ulang\s*tahun[ku|saya|gw]\s*(?:adalah)?\s*(\d{1,2}\s*[a-zA-Z]+)',
            r'[I|i|saya|gw|aku] born on (\d{1,2}\s*[a-zA-Z]+)',
            r'[my|My|saya|gw] birthday is (\d{1,2}\s*[a-zA-Z]+)',
        ],
        'name': [
            r'[N|n]ama\s*[saya|gw|ku|aku]\s*(?:adalah)?\s*([A-Za-z]+)',
            r'[P|p]anggil\s*[aku|saya|gw]\s*([A-Za-z]+)',
            r'[M|m]y\s*name\s*is\s*([A-Za-z]+)',
            r'[C|c]all\s*me\s*([A-Za-z]+)',
        ],
        'hobby': [
            r'[H|h]obi\s*[saya|gw|ku|aku]\s*(?:adalah)?\s*([A-Za-z\s]+)',
            r'[S|s]uka\s*([A-Za-z\s]+)',
            r'[M|m]y\s*hobby\s*is\s*([A-Za-z\s]+)',
        ]
    }
    
    # Check each message for personal info
    for entry in chat_history:
        if entry['role'] == 'user':
            content = entry['content']
            
            # Apply patterns to extract information
            for info_type, regex_patterns in patterns.items():
                for pattern in regex_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches and matches[0]:
                        personal_info[info_type] = matches[0]
                        break
    
    return personal_info

def extract_important_facts(user_message, bot_response):
    """Extract important facts from message exchange"""
    extracted_info = {}
    
    # Check for birthday information
    birthday_patterns = [
        r'ulang\s*tahun[ku|saya|gw]\s*(?:adalah|itu|pada)?\s*tanggal\s*(\d{1,2}\s*[a-zA-Z]+)',
        r'tanggal\s*ulang\s*tahun[ku|saya|gw]\s*(?:adalah)?\s*(\d{1,2}\s*[a-zA-Z]+)',
        r'[I|i|saya|gw|aku] born on (\d{1,2}\s*[a-zA-Z]+)',
        r'[my|My|saya|gw] birthday is (\d{1,2}\s*[a-zA-Z]+)',
    ]
    
    for pattern in birthday_patterns:
        matches = re.findall(pattern, user_message, re.IGNORECASE)
        if matches:
            extracted_info['birthday'] = matches[0]
            break
    
    # Check for other critical personal info
    # ... similar patterns for name, age, location, etc.
    
    return extracted_info