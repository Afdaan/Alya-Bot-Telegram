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
from utils.commands import is_roast_command, get_random_brutal_roast, ROAST_PREFIXES
from utils.language_handler import get_language, get_response

# Import tambahan
import time
from utils.context_manager import context_manager

import random
import json
from core.personas import persona_manager

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

async def _send_markdown_message(update: Update, text: str, reply_markup=None) -> None:
    """
    Safely send a message with MarkdownV2 format and handle large messages.
    
    Args:
        update: Telegram update object
        text: Text to send, already prepped with markdown
        reply_markup: Optional reply markup
    """
    # Format text for markdown - sanitize first
    formatted_text = text
    
    # Split message if too long
    parts = split_long_message(formatted_text)
    
    try:
        for i, part in enumerate(parts):
            # Only add reply markup to the last part
            current_markup = reply_markup if i == len(parts) - 1 else None
            
            # First try with MarkdownV2
            try:
                await update.message.reply_text(
                    part, 
                    parse_mode='MarkdownV2',
                    reply_markup=current_markup
                )
            except Exception as e:
                logger.warning(f"Failed to send with MarkdownV2: {e}")
                # If that fails, try without markdown
                await update.message.reply_text(
                    part.replace("\\", ""), # Remove escapes
                    reply_markup=current_markup
                )
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        # If all attempts fail, send plain text apology
        await update.message.reply_text(
            "Maaf, terjadi kesalahan saat mengirim pesan. Silakan coba lagi."
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Handle incoming messages with more natural responses.
    
    Args:
        update: Telegram Update object
        context: CallbackContext for state management
    """
    try:
        # Input validation
        if not update.message or not update.message.text:
            logger.debug("Received invalid message without text content")
            return

        message_text = update.message.text
        chat_type = update.message.chat.type
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Extract mentioned username for proper handling
        telegram_mention = None
        mentioned_username = None
        
        # Detect @username mentions in the message
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":  # This is a @username mention
                    telegram_mention = message_text[entity.offset:entity.offset + entity.length]
                    mentioned_username = telegram_mention[1:]  # Remove the @ symbol
                    logger.info(f"Detected mention: {telegram_mention}, username: {mentioned_username}")
                    break

        # Handle group messages - require prefix for groups
        if chat_type in ['group', 'supergroup']:
            if not message_text.startswith(CHAT_PREFIX):
                return
            message_text = message_text.replace(CHAT_PREFIX, "", 1).strip()

        # Early return for empty messages
        if not message_text:
            return
            
        # Get current language setting
        language = get_language(context)
            
        # Start typing indicator in background task that keeps refreshing
        typing_task = asyncio.create_task(send_typing_action(context, chat_id, 30))  # Up to 30 seconds
        
        try:
            # Select appropriate persona
            persona = select_persona(update.message, language)
            
            # Get user context
            user_id = user.id
            prev_context = context_manager.get_context(user_id, chat_id)
            prev_history = context_manager.get_chat_history(user_id, chat_id, 5)
            
            # Build enhanced prompt with relevant context
            enhanced_message = message_text
            
            # Add context from previous messages for better continuity
            if prev_history and len(prev_history) > 0:
                last_msg = prev_history[-1]['content'] if len(prev_history) > 0 else ''
                if last_msg:
                    enhanced_message = f"(Previous context: {last_msg[:100]}{'...' if len(last_msg) > 100 else ''})\n\nCurrent message: {message_text}"
            
            # Generate response with timeout protection
            response = await asyncio.wait_for(
                generate_chat_response(
                    enhanced_message,
                    user.id,
                    context=context,
                    persona_context=persona
                ),
                timeout=60.0
            )
            
            # Format response with proper Markdown
            safe_response = format_markdown_response(
                response,
                username=user.first_name,           
                telegram_username=user.username,    
                mentioned_username=mentioned_username,
                mentioned_text=telegram_mention    
            )
            
            # Add debug info if enabled
            if context.bot_data.get('debug_mode', False):
                debug_info = create_debug_info(user, update, chat_type, message_text, safe_response, telegram_mention)
                safe_response = debug_info

            # Cancel typing indicator before sending
            typing_task.cancel()
            
            # Send the response with proper formatting
            await send_formatted_response(update, safe_response)
            
            # Save conversation history
            context_manager.add_chat_message(user_id, chat_id, update.message.message_id, 'user', message_text)
            
            # Extract and save important information
            extracted_info = extract_important_facts(message_text, response)
            if extracted_info:
                for info_type, info_value in extracted_info.items():
                    try:
                        validated_user_id = int(user_id) if isinstance(user_id, (int, str)) else 0
                        validated_chat_id = int(chat_id) if isinstance(chat_id, (int, str)) else 0
                        
                        context_data = {
                            'command': 'personal_info',
                            'timestamp': int(time.time()),
                            'info_type': str(info_type),
                            'value': str(info_value),
                        }
                        
                        context_manager.save_context(validated_user_id, validated_chat_id, f"personal_{info_type}", context_data)
                        logger.debug(f"Personal info '{info_type}' saved for user {user_id}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid user_id or chat_id for personal info: {e}")
            
            # Save assistant's response to history
            context_manager.add_chat_message(user_id, chat_id, 0, 'assistant', response)

        except asyncio.TimeoutError:
            logger.warning(f"Response generation timed out for user {user.id}")
            typing_task.cancel()
            
            timeout_msg = get_response("timeout", context)
            await update.message.reply_text(
                timeout_msg,
                parse_mode='MarkdownV2'
            )
            return

    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
        
        error_msg = get_response("error", context)
        
        await update.message.reply_text(
            error_msg,
            parse_mode='MarkdownV2'
        )

def create_debug_info(user, update, chat_type, message_text, safe_response, telegram_mention=None) -> str:
    """
    Create detailed debug information block.
    
    Args:
        user: User data
        update: Update object
        chat_type: Type of chat
        message_text: Original message text
        safe_response: Formatted response
        telegram_mention: Optional mention
        
    Returns:
        Debug information formatted string
    """
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
    
    return debug_info

async def handle_text_message(update: Update, context: CallbackContext) -> None:
    """
    Handle incoming messages and detect if they're roast commands or regular messages.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    if not update.message or not update.message.text:
        return

    # Check if message starts with roast prefix - STRICT PREFIX CHECK
    message_text = update.message.text.strip()
    words = message_text.split()
    
    # Process as roast ONLY if the FIRST word is a roast prefix
    if words and words[0].lower() in ROAST_PREFIXES:
        await handle_roast(update, context)
        return
        
    # Otherwise, process as regular message
    await handle_message(update, context)

async def handle_roast(update: Update, context: CallbackContext) -> None:
    """
    Handle roast command with natural-sounding brutal responses.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    message = update.message
    
    # Parse the roast command
    is_roast, target, is_github, keywords, user_info = is_roast_command(message)
    
    # If no target specified, use sender's name or get target from reply
    if not target:
        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user.first_name
        else:
            target = update.effective_user.first_name
    
    # Generate a natural sounding brutal roast
    brutal_roast = get_random_brutal_roast(target, is_github)
    
    try:
        # Send the roast with markdown
        await message.reply_text(
            brutal_roast,
            parse_mode='Markdown'  # Use standard Markdown for simpler formatting
        )
    except Exception as e:
        # Fallback: send without formatting if markdown fails
        logger.warning(f"Failed to send roast with markdown: {e}")
        await message.reply_text(brutal_roast.replace('*', ''))
    
    # Mark roast with additional metadata to prevent it being used in future context
    try:
        context_manager.add_message_to_history(
            user_id=update.effective_user.id, 
            role='assistant',
            content=brutal_roast,
            chat_id=update.effective_chat.id,
            message_id=None,
            importance=0.1,   # Very low importance 
            metadata={"type": "roast", "do_not_reference": True, "ignore_in_memory": True}
        )
        
        # Tambah flag untuk clear memory state setelah roast
        context_data = {
            'last_interaction': 'roast',
            'timestamp': int(time.time()),
            'should_reset_memory_state': True
        }
        context_manager.save_context(
            update.effective_user.id,
            update.effective_chat.id,
            'memory_state',
            context_data
        )
    except Exception as e:
        logger.error(f"Failed to save roast context: {e}")

# Improved formatted response sender
async def send_formatted_response(update, response_text):
    """
    Send formatted response, splitting if necessary.
    
    Args:
        update: Telegram Update object
        response_text: The formatted response text
    """
    # Determine if content might be lyrics (has many short lines)
    lines = response_text.split('\n')
    is_likely_lyrics = (len(lines) > 8 and 
                        sum(len(line) < 50 for line in lines) / len(lines) > 0.7)
    
    # Use smaller chunks for lyrics to preserve formatting
    max_chunk_size = 2000 if is_likely_lyrics else 4000
    
    if len(response_text) > max_chunk_size:
        parts = split_long_message(response_text, max_chunk_size)
        for i, part in enumerate(parts):
            await update.message.reply_text(
                part,
                reply_to_message_id=update.message.message_id if i == 0 else None,
                parse_mode='MarkdownV2'
            )
            # Slightly longer delay between message parts to prevent rate limiting
            await asyncio.sleep(0.75)
    else:
        await update.message.reply_text(
            response_text,
            reply_to_message_id=update.message.message_id,
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

def get_roleplay_action(persona_type: str, message_content: str, response_content: str) -> str:
    """
    Get appropriate roleplay action based on persona and message context.
    
    Args:
        persona_type: Type of persona (waifu, toxic, smart)
        message_content: User message content
        response_content: Bot response content
        
    Returns:
        Formatted roleplay action string
    """
    # Skip for roasting mode
    if "NAJIS" in response_content or "ANJIR" in response_content:
        return ""
        
    # Get persona data
    persona_data = persona_manager.personas.get(persona_type, {})
    actions = persona_data.get('roleplay_actions', {})
    
    if not actions:
        # Fallback actions if not found in persona
        default_actions = {
            "neutral": ["*menatap*", "*mengangguk*", "*memiringkan kepala*"],
            "thinking": ["*berpikir*", "*menatap ke atas*"]
        }
        actions = default_actions
    
    # Determine action type based on message and response
    action_type = detect_action_type(message_content, response_content)
    
    # Get actions for the determined type, or fallback to neutral
    action_list = actions.get(action_type, actions.get('neutral', ['*tersenyum*']))
    
    # Pick random action
    action = random.choice(action_list)
    
    return action

def detect_action_type(message: str, response: str) -> str:
    """
    Detect appropriate action type based on message content and response.
    
    Args:
        message: User message text
        response: Bot response text
        
    Returns:
        Action type string
    """
    message_lower = message.lower()
    response_lower = response.lower()
    
    # Simple sentiment detection
    if any(word in message_lower for word in ["sedih", "menangis", "kecewa", "galau", "sad"]):
        return "sad"
    elif any(word in message_lower for word in ["marah", "kesal", "geram", "sebal", "angry"]):
        return "angry"
    elif any(word in message_lower for word in ["bagaimana", "gimana", "bingung", "confused", "??"]):
        return "thinking"
    elif "?" in message:
        return "thinking"
        
    # Check response sentiment for determining action
    if any(word in response_lower for word in ["maaf", "sedih", "kecewa"]):
        return "sad"
    elif any(word in response_lower for word in ["senang", "bahagia", "sukses"]):
        return "happy"
    elif any(word in response_lower for word in ["menurut", "analisis", "perhitungan"]):
        return "thinking"
    elif any(word in response_lower for word in ["benar", "tepat", "correct"]):
        return "happy"
    elif any(word in response_lower for word in ["sebal", "kesal", "marah"]):
        return "angry"
    elif "?" in response:
        return "confused"
    
    # Special case for toxic persona
    if "toxic" in response_lower:
        return "judgmental"
    elif "smart" in response_lower:
        return "analyzing"
            
    # Default to neutral
    return "neutral"

# Helper to check if the response is a roast
def is_roast_response(response: str) -> bool:
    """Check if response is a roast based on content patterns."""
    roast_markers = ["ANJIR", "NAJIS", "GOBLOK", "TOLOL", "BEGO", "KONTOL", "MEMEK", "BANGSAT", "MUKA LO"]
    return any(marker in response for marker in roast_markers)

def get_current_persona_type(message) -> str:
    """Get current persona type based on message content."""
    # Check for roasting command
    is_roast, _, _, _, _ = is_roast_command(message)
    
    if is_roast:
        return "toxic"
    
    # Detect if info/advanced questions
    message_text = message.text.lower()
    info_keywords = [
        'jadwal', 'siapa', 'apa', 'dimana', 'kapan', 'bagaimana', 
        'mengapa', 'cara', 'berapa', 'info', 'cari', 'carikan', 
        'detail', '-d', '--detail'
    ]
    is_info_query = any(keyword in message_text for keyword in info_keywords)
    is_advanced = (
        'detail' in message_text or
        '-d' in message_text or
        '--detail' in message_text or
        len(message_text.split()) > 12  # consider advanced if question is long
    )
    
    if is_info_query and is_advanced:
        return "smart"
    
    # Default persona
    return "waifu"