"""
Helper utilities for handling voice-related bot responses.
Reduces duplication between VoiceHandler and ConversationHandler.
"""
import logging
import asyncio
from typing import Any, Optional

from telegram import Update
from telegram.ext import ContextTypes

from utils.tts_queue import dispatch_tts
from utils.language_translator import translate_response_for_voice
from utils.telegram_helpers import start_loading_animation
from config.settings import DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

async def send_voice_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    voice_processor: Any,
    db_manager: Any,
    source_lang: Optional[str] = None
) -> None:
    """
    Translates text dialogue, shows a recording animation, and dispatches a TTS job.
    
    Args:
        update: The Telegram update.
        context: The Telegram context.
        text: The raw AI response text to convert to voice.
        voice_processor: The VoiceProcessor instance.
        db_manager: The database manager to get user language settings.
        source_lang: The language the text is currently in.
    """
    if not voice_processor:
        logger.warning("Attempted to send voice reply but voice_processor is not available")
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if source_lang is None:
        source_lang = DEFAULT_LANGUAGE

    try:
        # 1. Get user's preferred voice language
        voice_lang = db_manager.get_user_voice_language(user.id) if db_manager else "en"
        
        # 2. Extract dialogue and translate for TTS
        tts_text = await translate_response_for_voice(text, source_lang, voice_lang)
        
        # 3. Create loading/recording message
        tts_phrase = "Alya is recording a voice note" if source_lang == 'en' else "Alya lagi ngerekam voice note"
        tts_loading_msg = await update.message.reply_html(
            f"<blockquote><b>🎙️ {tts_phrase}.</b></blockquote>"
        )

        # 4. Start animation
        tts_loading_task = start_loading_animation(
            tts_loading_msg, 
            tts_phrase, 
            frames=["🎙️", "🎶", "✨"], 
            interval=2.5
        )

        try:
            # 5. Dispatch job to TTS microservice (fire and forget)
            await dispatch_tts(
                bot=context.bot,
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id,
                voice_processor=voice_processor,
                response_text=tts_text,
                voice_lang=voice_lang,
                user_lang=source_lang,
                loading_message_id=tts_loading_msg.message_id
            )
        finally:
            pass
            
    except Exception as e:
        logger.error(f"Error in send_voice_reply: {e}", exc_info=True)
