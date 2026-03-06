"""
Voice message handler for Alya Bot.
Handles voice message input and generates voice responses using the Alya voice model.
"""
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
from core.nlp import NLPEngine
from database.database_manager import DatabaseManager
from utils.voice_processor import VoiceProcessor
from utils.language_translator import translate_response_for_voice
from config.settings import VOICE_ENABLED, DEFAULT_LANGUAGE, ADMIN_IDS

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
            is_admin = user.id in ADMIN_IDS
            
            if not is_admin and (not db_user or not db_user.voice_enabled):
                await update.message.reply_html(
                    "🔒 <b>Voice Access Required</b>\n\nContact an admin to request access!"
                )
                return

            await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
            
            # 2. Download and Transcribe
            voice_file = await update.message.voice.get_file()
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                await voice_file.download_to_drive(tmp.name)
                transcription = await self.voice_processor.transcribe_audio(tmp.name, db_user_dict.get('language_code', DEFAULT_LANGUAGE))
                os.unlink(tmp.name)
            
            if not transcription:
                await update.message.reply_text("❌ I couldn't understand that. Try again!")
                return
            
            text, detected_lang = transcription
            lang_flag = {"en": "🇺🇸", "id": "🇮🇩", "ja": "🎌"}.get(detected_lang, "🌐")
            await update.message.reply_html(f"🎤 <i>({lang_flag} {detected_lang.upper()}): {text}</i>")
            
            # 3. AI Processing
            msg_context = self.nlp_engine.get_message_context(text, user.id) if self.nlp_engine else {}
            rel_level = db_user_dict.get('relationship_level', 0)
            
            prompt = self.persona_manager.get_chat_prompt(
                user.first_name, text, "", rel_level, is_admin, db_user_dict.get('language_code', DEFAULT_LANGUAGE)
            )
            
            response = await self.gemini_client.generate_response(
                user.id, user.first_name, text, prompt, rel_level, is_admin, db_user_dict.get('language_code', DEFAULT_LANGUAGE)
            )
            
            if not response:
                await update.message.reply_text("❌ Failed to generate response.")
                return

            # 4. Responses (Text + Voice)
            from utils.formatters import format_persona_response
            ui_text = format_persona_response(response, use_html=True) + "\u200C"
            await update.message.reply_html(ui_text)
            
            await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.RECORD_VOICE)
            voice_lang = self.db_manager.get_user_voice_language(user.id) if self.db_manager else "en"
            
            voice_text = response
            if voice_lang != db_user_dict.get('language_code'):
                translated = await translate_response_for_voice(response, db_user_dict.get('language_code'), voice_lang)
                voice_text = translated or response
            
            voice_path = await self.voice_processor.text_to_speech(voice_text, voice_lang)
            if voice_path and os.path.exists(voice_path):
                caption = f"🎙️ Alya's voice ({voice_lang.upper()})"
                with open(voice_path, 'rb') as vf:
                    await update.message.reply_voice(vf, caption=caption)
                os.unlink(voice_path)

            # 5. Metadata Update
            if self.memory_manager:
                self.memory_manager.save_user_message(user.id, text)
                self.memory_manager.save_bot_response(user.id, response)
            
            if db_user:
                self.db_manager.increment_interaction_count(user.id)
                if msg_context:
                    delta = self._calculate_affection_delta(user.id, msg_context)
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
