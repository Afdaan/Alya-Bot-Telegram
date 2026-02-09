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
        nlp_engine: Optional[NLPEngine] = None
    ):
        """
        Initialize voice handler.
        
        Args:
            gemini_client: Gemini AI client for processing
            persona_manager: Persona management
            memory_manager: Memory management
            db_manager: Database manager
            nlp_engine: NLP engine for emotion/intent detection
        """
        self.gemini_client = gemini_client
        self.persona_manager = persona_manager
        self.memory_manager = memory_manager
        self.db_manager = db_manager
        self.nlp_engine = nlp_engine
        
        # Initialize voice processor
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
        """
        Handle incoming voice messages.
        
        Args:
            update: Telegram update object
            context: Telegram context
        """
        if not self.voice_processor:
            await update.message.reply_text(
                "❌ Voice feature is currently unavailable. Please try text messages."
            )
            return
        
        user = update.effective_user
        chat = update.effective_chat
        voice = update.message.voice
        
        logger.info(f"🎤 Voice message received from {user.username} ({user.id})")
        
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=chat.id,
            action=ChatAction.TYPING
        )
        
        try:
            # Get or create user in database (returns dict)
            db_user_dict = self._create_or_update_user(user)
            lang = db_user_dict.get('language_code', DEFAULT_LANGUAGE) if db_user_dict else DEFAULT_LANGUAGE
            
            # Get User object for voice_enabled check
            db_user = self.db_manager.get_user_object(user.id) if self.db_manager else None
            
            # Check if user has voice access (whitelist)
            is_admin = user.id in ADMIN_IDS
            
            if not is_admin and (not db_user or not db_user.voice_enabled):
                await update.message.reply_text(
                    "🔒 <b>Voice Feature Access Required</b>\n\n"
                    "Sorry, you don't have access to the voice feature yet. "
                    "Voice/TTS is currently limited to whitelisted users.\n\n"
                    "💡 <i>Contact an admin to request access!</i>",
                    parse_mode='HTML'
                )
                logger.info(f"⛔ Voice access denied for user {user.id} (not whitelisted)")
                return
            
            # Download voice file
            voice_file = await voice.get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_voice:
                temp_voice_path = temp_voice.name
                await voice_file.download_to_drive(temp_voice_path)
            
            logger.info(f"📥 Voice file downloaded: {temp_voice_path}")
            
            # Transcribe voice to text
            await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
            transcribed_text = await self.voice_processor.transcribe_audio(temp_voice_path, lang)
            
            if not transcribed_text:
                await update.message.reply_text(
                    "❌ Sorry, I couldn't understand the voice message. Please try again or use text."
                )
                return
            
            logger.info(f"📝 Transcribed text: {transcribed_text}")
            
            # Show transcription to user
            await update.message.reply_text(
                f"🎤 <i>You said: {transcribed_text}</i>",
                parse_mode='HTML'
            )
            
            # Process the transcribed text like a normal message
            await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
            
            # Get NLP analysis
            message_context = {}
            if self.nlp_engine:
                message_context = self.nlp_engine.get_message_context(
                    transcribed_text,
                    user_id=user.id
                )
            
            # Get user relationship info
            relationship_level = db_user_dict.get('relationship_level', 0) if db_user_dict else 0
            
            # Build conversation context
            conversation_context = self._prepare_conversation_context(
                user,
                transcribed_text,
                lang,
                message_context,
                relationship_level
            )
            
            # Generate response using Gemini
            response = await self.gemini_client.generate_response(
                user_id=user.id,
                username=user.first_name or "user",
                message=transcribed_text,
                context=conversation_context["system_prompt"],
                relationship_level=relationship_level,
                is_admin=user.id in ADMIN_IDS,
                lang=lang,
                retry_count=3,
                is_media_analysis=False,
                media_context=None
            )
            
            if not response:
                await update.message.reply_text(
                    "❌ Sorry, I couldn't generate a response. Please try again."
                )
                return
            
            # Clean response
            cleaned_response = self._clean_response(response)
            
            # Send text response first
            await update.message.reply_text(
                cleaned_response,
                parse_mode='HTML'
            )
            
            # Generate and send voice response
            await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.RECORD_VOICE)
            
            voice_response_path = await self.voice_processor.text_to_speech(
                cleaned_response,
                lang=lang
            )
            
            if voice_response_path and os.path.exists(voice_response_path):
                await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.UPLOAD_VOICE)
                
                with open(voice_response_path, 'rb') as voice_file:
                    await update.message.reply_voice(
                        voice=voice_file,
                        caption="🎙️ Alya's voice response"
                    )
                
                logger.info(f"🎙️ Voice response sent to {user.username}")
                
                # Clean up voice response file
                try:
                    os.unlink(voice_response_path)
                except Exception as e:
                    logger.warning(f"Failed to delete voice response file: {e}")
            
            # Save conversation to memory
            if self.memory_manager:
                self.memory_manager.save_user_message(
                    user_id=user.id,
                    message=transcribed_text
                )
                self.memory_manager.save_bot_response(
                    user_id=user.id,
                    response=cleaned_response
                )
            
            # Update user stats
            if db_user:
                self.db_manager.increment_interaction_count(user.id)
                
                # Calculate affection delta
                if message_context:
                    affection_delta = self._calculate_affection_delta(user.id, message_context)
                    if affection_delta != 0:
                        self.db_manager.update_affection(user.id, affection_delta)
            
        except Exception as e:
            logger.error(f"❌ Error processing voice message: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ An error occurred while processing your voice message. Please try again."
            )
        
        finally:
            # Clean up temporary voice file
            try:
                if 'temp_voice_path' in locals():
                    os.unlink(temp_voice_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary voice file: {e}")
    
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
    
    def _clean_response(self, response: str) -> str:
        """Clean response text for voice output."""
        # Remove markdown formatting
        response = response.replace('*', '').replace('_', '').replace('`', '')
        
        # Remove HTML tags
        response = response.replace('<b>', '').replace('</b>', '')
        response = response.replace('<i>', '').replace('</i>', '')
        response = response.replace('<code>', '').replace('</code>', '')
        
        # Limit length for voice
        max_length = 500
        if len(response) > max_length:
            response = response[:max_length] + "..."
        
        return response.strip()
    
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
