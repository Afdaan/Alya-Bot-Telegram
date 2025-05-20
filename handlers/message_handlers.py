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
from telegram.constants import ParseMode, ChatAction

from config.settings import (
    CHAT_PREFIX, 
    DEFAULT_LANGUAGE, 
    SUPPORTED_LANGUAGES,
    DEVELOPER_IDS,
    GROUP_CHAT_REQUIRES_PREFIX,
    ADDITIONAL_PREFIXES
)
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.rate_limiter import limiter, rate_limited
from utils.language_handler import get_language, get_response
from utils.context_manager import context_manager
from utils.commands import command_detector
from core.models import generate_chat_response
from core.personas import persona_manager, get_persona_context

# Setup logger
logger = logging.getLogger(__name__)

# Semua kemungkinan prefiks untuk chat - akan digunakan untuk deteksi
ALL_VALID_PREFIXES = [CHAT_PREFIX.lower()] + [prefix.lower() for prefix in ADDITIONAL_PREFIXES]

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
    message_text = message.text.strip()
    user = update.effective_user
    chat_type = message.chat.type
    chat_id = message.chat_id
    
    # Log incoming message untuk debugging - gunakan only di development
    # PERBAIKAN: Akses debug_mode dengan cara yang benar
    debug_mode = context.bot_data.get('debug_mode', False)
    if debug_mode:
        logger.debug(f"Received message from {user.id} in {chat_type}: '{message_text[:30]}...'")
    
    # Deteksi prefix dan extract dari grup vs private chat
    is_private_chat = chat_type == "private"
    has_bot_prefix = False
    original_message = message_text
    
    # PERBAIKAN PENTING: Hanya proses pesan di grup jika ada prefix yang valid 
    if not is_private_chat:
        # Cek apakah menggunakan salah satu prefix yang valid
        lower_text = message_text.lower()
        
        for prefix in ALL_VALID_PREFIXES:
            if lower_text.startswith(prefix):
                has_bot_prefix = True
                # Hapus prefix dari message text
                message_text = message_text[len(prefix):].strip()
                break
                
        # Tambahkan cek mention ke bot - ini juga valid untuk trigger respon
        if not has_bot_prefix and context.bot and context.bot.username:
            bot_mention = f"@{context.bot.username}"
            if bot_mention in message_text:
                has_bot_prefix = True
                # Hapus mention dari teks
                message_text = message_text.replace(bot_mention, "").strip()
        
        # PERBAIKAN UTAMA: Jika di grup dan tidak ada prefix yang valid, JANGAN RESPON
        if GROUP_CHAT_REQUIRES_PREFIX and not has_bot_prefix:
            # Log detail untuk debug saja
            if debug_mode:
                logger.debug(f"Ignoring message in group without valid prefix: '{original_message[:30]}...'")
            return
    
    # PERBAIKAN: Jika message kosong setelah menghapus prefix, beri panduan
    if not message_text and (is_private_chat or has_bot_prefix):
        guide_text = ("Hai! Aku Alya, ada yang bisa aku bantu? "
                    "Kamu bisa bertanya atau mengobrol denganku~ ✨")
        await message.reply_text(guide_text)
        return
    
    # Deteksi apakah ini adalah command (seperti /start, /help) yang disalahgunakan
    # sebagai normal message, jika iya abaikan
    if message_text.startswith('/'):
        # Ini command, jangan proses sebagai chat normal
        return
    
    # Check message length - terlalu pendek gak guna diproses
    if len(message_text) < 2:
        # Kalau di private chat atau ada prefix valid, kasih panduan
        if is_private_chat or has_bot_prefix:
            await message.reply_text("Hmm? Alya tidak mengerti pesan yang terlalu pendek... 🤔")
        return
    
    # Mulai proses chat asli
    await process_chat_message(update, context, message_text)

async def process_chat_message(update: Update, context: CallbackContext, processed_text: str) -> None:
    """
    Process chat message and generate AI response.
    
    Args:
        update: Telegram update object
        context: Callback context
        processed_text: Text message after prefix removal
    """
    message = update.message
    user = update.effective_user
    chat_id = message.chat.id

    # Send typing indicator
    await message.chat.send_action(ChatAction.TYPING)
    
    # Setup async task untuk typing indicator yang terus diperbarui
    typing_task = asyncio.create_task(
        send_continued_typing(context.bot, chat_id)
    )
    
    try:
        # Get language setting - FIX: menggunakan bot_data, bukan context.get
        # DEFAULT_LANGUAGE sebagai fallback jika tidak ada language di bot_data
        language = DEFAULT_LANGUAGE
        if hasattr(context, 'bot_data') and isinstance(context.bot_data, dict):
            language = context.bot_data.get('language', DEFAULT_LANGUAGE)
        
        # Get persona based on user settings - FIX: ambil persona dari context.user_data
        persona_type = "tsundere"  # Default fallback
        if hasattr(context, 'user_data') and isinstance(context.user_data, dict):
            persona_type = context.user_data.get("persona", "tsundere")
        persona_context = get_persona_context(persona_type)
        
        # Get relevant context for this conversation
        user_context = context_manager.recall_relevant_context(
            user.id, 
            processed_text,
            chat_id=chat_id
        )
        
        # Generate response with appropriate context
        response_text = await generate_chat_response(
            processed_text, 
            user.id, 
            context=context,
            persona_context=persona_context
        )
        
        # Cancel typing indicator
        typing_task.cancel()
        
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
                        chat_id=chat_id,
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
        # Cancel typing indicator
        typing_task.cancel()
        
        # FIX: Pastikan language sudah terdefinisi sebelum digunakan di get_response
        lang = DEFAULT_LANGUAGE
        if hasattr(context, 'bot_data') and isinstance(context.bot_data, dict):
            lang = context.bot_data.get('language', DEFAULT_LANGUAGE)
            
        # API timeout response - Dengan language yang sudah terdefinisi
        timeout_message = get_response("timeout", lang)
        if not timeout_message:
            timeout_message = "Hmm, Alya membutuhkan waktu terlalu lama... Bisa coba lagi nanti? 🥺"
        
        await message.reply_text(timeout_message, parse_mode='MarkdownV2')
        
    except Exception as e:
        # Cancel typing indicator
        typing_task.cancel()
        
        # FIX: Pastikan variable language sudah didefinisikan dengan fallback yang aman
        lang = DEFAULT_LANGUAGE
        if hasattr(context, 'bot_data') and isinstance(context.bot_data, dict):
            lang = context.bot_data.get('language', DEFAULT_LANGUAGE)
        
        # General error message with safe formatting
        logger.error(f"Error generating response: {e}")
        # Perbaikan akses get_response dengan language yang sudah terdefinisi
        error_message = get_response("error", lang)
        if not error_message:
            error_message = "Gomen, terjadi kesalahan saat memproses pesan... 🙏"
        
        await message.reply_text(error_message)

async def send_continued_typing(bot, chat_id: int, max_duration: int = 30) -> None:
    """
    Send continued typing indicator every 4 seconds.
    Typing indicator normally expires after 5 seconds.
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send typing indicator to
        max_duration: Maximum duration in seconds
    """
    end_time = time.time() + max_duration
    try:
        while time.time() < end_time:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)  # Refresh before expiration
    except asyncio.CancelledError:
        # Task was cancelled, no problem
        pass
    except Exception as e:
        logger.error(f"Error in continuous typing: {e}")