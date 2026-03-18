"""
Voice message handler for Alya Bot.
Handles voice message input and generates voice responses using the Alya voice model.
"""
import asyncio
import logging
import os
import tempfile
from typing import Optional
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.constants import ChatAction

from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.memory import MemoryManager
from core.mood_manager import MoodManager
from core.nlp import NLPEngine, ContextManager
from database.database_manager import DatabaseManager, db_manager, get_user_lang
from utils.voice_processor import VoiceProcessor
from utils.voice_helpers import send_voice_reply
from utils.telegram_helpers import ChatActionSender, start_loading_animation
from config.settings import VOICE_ENABLED, DEFAULT_LANGUAGE, ADMIN_IDS, AFFECTION_POINTS

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handler for voice message functionality with Alya."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        persona_manager: PersonaManager,
        memory_manager: MemoryManager,
        db_manager: DatabaseManager,
        nlp_engine: Optional[NLPEngine] = None,
        voice_processor: Optional[VoiceProcessor] = None
    ):
        """
        Initialize voice handler.
        
        Args:
            gemini_client: Gemini AI client for processing
            persona_manager: Persona management
            memory_manager: Memory management
            db_manager: Database manager
            nlp_engine: NLP engine for emotion/intent detection
            voice_processor: Shared voice processor
        """
        self.gemini_client = gemini_client
        self.persona_manager = persona_manager
        self.memory_manager = memory_manager
        self.db_manager = db_manager
        self.context_manager = ContextManager(self.db_manager) if self.db_manager else None
        self.nlp_engine = nlp_engine
        
        # Use shared voice processor
        if voice_processor:
            self.voice_processor = voice_processor
            logger.info("✅ Using shared VoiceProcessor")
        else:
            try:
                self.voice_processor = VoiceProcessor()
                logger.info("✅ Voice processor initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize voice processor: {e}")
                self.voice_processor = None
    
    def get_handlers(self):
        """Return list of voice message handlers."""
        if not VOICE_ENABLED or not self.voice_processor:
            logger.warning("Voice feature is disabled or voice processor not available")
            return []
        
        return [
            MessageHandler(
                filters.VOICE & ~filters.COMMAND,
                self.handle_voice_message
            )
        ]
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming voice messages with transcription and AI response."""
        if not self.voice_processor:
            await update.message.reply_text("❌ Voice feature is currently unavailable.")
            return
        
        user = update.effective_user
        chat = update.effective_chat
        
        try:
            # 1. Access Check
            db_user_dict = self._create_or_update_user(user)
            db_user = self.db_manager.get_user_object(user.id) if self.db_manager else None
            is_admin = user.id in ADMIN_IDS or (self.db_manager.is_admin(user.id) if self.db_manager else False)
            
            if not is_admin and (not db_user or not db_user.voice_enabled):
                await update.message.reply_html(
                    "🔒 <b>Voice Access Required</b>\n\nContact an admin to request access!"
                )
                return
            
            async with ChatActionSender(context, chat.id, ChatAction.TYPING):
                # 1. Download and Transcribe
                voice = update.message.voice
                file = await context.bot.get_file(voice.file_id)
                
                with tempfile.TemporaryDirectory() as tmp_dir:
                    ogg_path = os.path.join(tmp_dir, f"voice_{voice.file_id}.ogg")
                    await file.download_to_drive(ogg_path)
                    
                    transcription_data = await self.voice_processor.transcribe_audio(ogg_path, lang=db_user_dict.get('language_code', DEFAULT_LANGUAGE))
                    if not transcription_data:
                        await update.message.reply_html("❌ Gagal mengenali suara kamu...")
                        return
                    
                    user_text, detected_lang = transcription_data
                    logger.info(f"🎙️ Voice transcribed (lang={detected_lang}): {user_text}")
                
                lang_flag = {"en": "🇺🇸", "id": "🇮🇩", "jp": "🎌"}.get(detected_lang, "🌐")
                await update.message.reply_html(f"🎤 <i>({lang_flag} {detected_lang.upper()}): {user_text}</i>")

                phrase = "Alya is thinking" if db_user_dict.get('language_code', DEFAULT_LANGUAGE) == 'en' else "Alya lagi mikir"
                loading_msg = await update.message.reply_text(f"<blockquote><b>💭 {phrase}...</b></blockquote>", parse_mode="HTML")

                from utils.telegram_helpers import start_loading_animation
                loading_task = start_loading_animation(loading_msg, phrase)

                # 2. Memory & Relationship Updates
                self.db_manager.save_message(user.id, "user", user_text)
                if self.memory_manager:
                    self.memory_manager.save_user_message(user.id, user_text)
                
                message_context = {}
                if self.nlp_engine:
                    message_context = self.nlp_engine.get_message_context(user_text, user.id)
                    mood_manager = MoodManager()
                    
                    current_mood = self.db_manager.get_user_mood(user.id)
                    rel_info = self.db_manager.get_user_relationship_info(user.id)

                # 3. Generate AI Response
                rel_level = db_user_dict.get('relationship_level', 0)
                
                # Build context string
                history_text = ""
                if self.context_manager:
                    history = self.context_manager.get_context_window(user.id)
                    if history:
                        # Clean format: [Role] Content
                        history_text = "\n".join([f"[{msg['role'].capitalize()}] {msg['content']}" for msg in history])
                
                try:
                    response = await self.gemini_client.generate_response(
                        user_id=user.id,
                        username=user.first_name or "user",
                        message=user_text,
                        context=self.persona_manager.get_chat_prompt(
                            username=user.first_name,
                            message=user_text,
                            context=history_text,
                            relationship_level=rel_level,
                            is_admin=is_admin,
                            lang=db_user_dict.get('language_code', DEFAULT_LANGUAGE)
                        ),
                        relationship_level=rel_level,
                        is_admin=is_admin,
                        lang=db_user_dict.get('language_code', DEFAULT_LANGUAGE)
                    )
                finally:
                    loading_task.cancel()
                    try:
                        await loading_task
                    except asyncio.CancelledError:
                        pass
                
                if not response:
                    error_msg = "❌ Gagal mendapatkan respon dari Alya..."
                    try:
                        await loading_msg.edit_text(error_msg, parse_mode="HTML")
                    except Exception:
                        await update.message.reply_html(error_msg)
                    return

            ui_text = format_persona_response(response, use_html=True) + "\u200C"
            try:
                await loading_msg.edit_text(ui_text, parse_mode="HTML")
            except Exception:
                await update.message.reply_html(ui_text)

            source_lang = db_user_dict.get('language_code', DEFAULT_LANGUAGE)
            await send_voice_reply(
                update=update,
                context=context,
                text=response,
                voice_processor=self.voice_processor,
                db_manager=self.db_manager,
                source_lang=source_lang
            )

            # 5. Metadata Update
            if self.memory_manager:
                self.memory_manager.save_bot_response(user.id, response)
            
            if db_user:
                self.db_manager.increment_interaction_count(user.id)
                if message_context:
                    delta = self._calculate_affection_delta(user.id, message_context)
                    if delta: self.db_manager.update_affection(user.id, delta)

        except Exception as e:
            logger.error(f"❌ Voice processing error: {e}")
            await update.message.reply_text("❌ Error processing voice message.")
    
    def _create_or_update_user(self, user):
        """Create or update user in database."""
        try:
            return self.db_manager.get_or_create_user(
                user_id=user.id,
                username=user.username or user.first_name,
                first_name=user.first_name,
                last_name=user.last_name
            )
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return None
    
    def _prepare_conversation_context(
        self,
        user,
        query: str,
        lang: str,
        message_context: dict,
        relationship_level: int
    ):
        """Prepare conversation context for Gemini (simplified for voice)."""
        # Get chat prompt using PersonaManager with Alya persona
        persona_prompt = self.persona_manager.get_chat_prompt(
            username=user.first_name or "user",
            message=query,
            context="",  # Voice messages don't have history context
            relationship_level=relationship_level,
            is_admin=user.id in ADMIN_IDS,
            lang=lang,
            extra_sections=None  # Use default persona (waifu/Alya)
        )
        
        return {
            "system_prompt": persona_prompt,
            "message_context": message_context,
            "relationship_level": relationship_level,
            "language": lang
        }
    
    def _calculate_affection_delta(self, user_id: int, message_context: dict) -> int:
        """Calculate affection points change based on message context."""
        from config.settings import AFFECTION_POINTS
        
        delta = 0
        emotion = message_context.get("emotion", "neutral")
        intent = message_context.get("intent", "conversation")
        
        # Emotion-based affection
        emotion_mapping = {
            "joy": "positive_emotion",
            "gratitude": "gratitude",
            "love": "affection",
            "sadness": "mild_positive_emotion",  # Showing vulnerability
            "anger": "anger",
            "fear": "mild_positive_emotion"
        }
        
        if emotion in emotion_mapping:
            delta += AFFECTION_POINTS.get(emotion_mapping[emotion], 0)
        
        # Intent-based affection
        if intent in AFFECTION_POINTS:
            delta += AFFECTION_POINTS[intent]
        
        # Base conversation affection
        delta += AFFECTION_POINTS.get("conversation", 1)
        
        return delta
