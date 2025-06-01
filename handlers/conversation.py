"""
Conversation for Alya Bot.
"""
import logging
import random
from typing import Dict, List, Optional, Any
import asyncio

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from config.settings import COMMAND_PREFIX, FEATURES, ADMIN_IDS
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.memory import MemoryManager
from core.database import DatabaseManager
from core.nlp import NLPEngine
from utils.formatters import format_response, format_error_response
from utils.roast import RoastHandler

logger = logging.getLogger(__name__)

class ConversationHandler:
    """Handler for conversation functionality with Alya."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        persona_manager: PersonaManager, 
        memory_manager: MemoryManager,
        nlp_engine: Optional[NLPEngine] = None
    ) -> None:
        self.gemini = gemini_client
        self.persona = persona_manager
        self.memory = memory_manager
        self.nlp = nlp_engine or NLPEngine()
        self.db = DatabaseManager()
        self.roast_handler = RoastHandler(gemini_client, persona_manager)
    
    def get_handlers(self) -> List:
        handlers = [
            MessageHandler(
                filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
                self.chat_command
            ),
            MessageHandler(
                (
                    filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND &
                    (
                        filters.Regex(f"^{COMMAND_PREFIX}") |
                        filters.REPLY
                    )
                ),
                self.chat_command
            ),
        ]
        handlers.extend(self.roast_handler.get_handlers())
        return handlers
    
    def _create_or_update_user(self, user) -> bool:
        is_admin = user.id in ADMIN_IDS or self.db.is_admin(user.id)
        self.db.get_or_create_user(
            user.id, 
            username=user.username or "", 
            first_name=user.first_name or "", 
            last_name=user.last_name or "",
            is_admin=is_admin
        )
        return is_admin
    
    def _get_relationship_level(self, user_id: int) -> int:
        user_info = self.db.get_user_relationship_info(user_id)
        return user_info.get("relationship", {}).get("level", 0) if user_info else 0
    
    async def _send_error_response(self, update: Update, username: str) -> None:
        error_message = self.persona.get_error_message(username=username or "user")
        formatted_error = format_error_response(error_message)
        await update.message.reply_html(formatted_error)
            
    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message_text = update.message.text

        reply_context = ""
        is_reply_to_alya = False
        replied_message_is_conversation = False
        if update.message.reply_to_message:
            replied = update.message.reply_to_message
            if replied.from_user and replied.from_user.is_bot:
                if replied.from_user.id == context.bot.id:
                    reply_context = replied.text or ""
                    if replied.text and replied.text.endswith("\u200C"):
                        replied_message_is_conversation = True
                    is_reply_to_alya = True

        if update.message.chat.type in ["group", "supergroup"]:
            if is_reply_to_alya:
                if update.message.reply_to_message and not replied_message_is_conversation:
                    return
                query = message_text.strip()
            else:
                if message_text.startswith(COMMAND_PREFIX):
                    query = message_text.replace(COMMAND_PREFIX, "", 1).strip()
                else:
                    return
        else:
            query = message_text.strip()

        bot_username = (await context.bot.get_me()).username if hasattr(context.bot, "get_me") else None
        if query.startswith("/"):
            if bot_username:
                if query.split()[0].lower().startswith(f"/") and f"@{bot_username.lower()}" in query.split()[0].lower():
                    return
            else:
                return
            return

        if reply_context:
            query = f"{reply_context}\n\n{query}"
        
        if not query:
            help_message = self.persona.get_help_message(
                username=user.first_name or "user",
                prefix=COMMAND_PREFIX
            )
            formatted_help = format_response(help_message, "neutral")
            await update.message.reply_html(formatted_help)
            return
        
        chat = update.effective_chat
        try:
            if hasattr(update.message, "message_thread_id") and update.message.message_thread_id:
                await context.bot.send_chat_action(
                    chat_id=chat.id,
                    action=ChatAction.TYPING,
                    message_thread_id=update.message.message_thread_id
                )
            else:
                await context.bot.send_chat_action(
                    chat_id=chat.id,
                    action=ChatAction.TYPING
                )
        except Exception as e:
            logger.warning(f"Failed to send typing action: {e}")
        
        try:
            self._create_or_update_user(user)
            self.db.save_message(user.id, "user", query)
            self.memory.save_user_message(user.id, query)
            user_context = await self._prepare_conversation_context(user, query)
            response = await self.gemini.generate_content(
                user_input=user_context["enhanced_query"],
                system_prompt=user_context["system_prompt"],
                history=user_context["history"]
            )
            if response:
                await self._process_and_send_response(update, user, response, user_context["message_context"])
            else:
                await self._send_error_response(update, user.first_name)
        except Exception as e:
            logger.error(f"Error in chat command: {e}", exc_info=True)
            await self._send_error_response(update, user.first_name)
    
    async def _prepare_conversation_context(self, user, query: str) -> Dict[str, Any]:
        user_task = asyncio.create_task(self._get_user_info(user))
        self.memory.save_user_message(user.id, query)
        relationship_level = self._get_relationship_level(user.id)
        message_context = {}
        if FEATURES.get("emotion_detection", False) and self.nlp:
            message_context = self.nlp.get_message_context(query, user.id)
        history = self._call_method_safely(self.memory.get_conversation_context, user.id)
        enhanced_query = self._call_method_safely(self.memory.create_context_prompt, user.id, query)
        system_prompt = self.persona.get_system_prompt()
        relationship_context = self._get_relationship_context(user, relationship_level, user.id in ADMIN_IDS)
        if relationship_context:
            system_prompt += f"\n\n{relationship_context}"
        await user_task
        if message_context:
            logger.debug(f"Message context: {message_context}")
        return {
            "history": history,
            "enhanced_query": enhanced_query,
            "system_prompt": system_prompt,
            "message_context": message_context,
            "relationship_level": relationship_level
        }
    
    def _call_method_safely(self, method, *args, **kwargs):
        if asyncio.iscoroutinefunction(method):
            return asyncio.create_task(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)
        
    async def _process_and_send_response(
        self, 
        update: Update, 
        user, 
        response: str, 
        message_context: Dict[str, Any]
    ) -> None:
        # Store messages in DB first
        self.db.save_message(user.id, "assistant", response)
        self.memory.save_bot_response(user.id, response)
        
        # Update user relationship based on detected context
        if message_context:
            self._update_affection_from_context(user.id, message_context)
            
        # Get emotion context for formatting
        emotion = message_context.get("emotion", "neutral") if message_context else "neutral"
        intensity = message_context.get("intensity", 0.5) if message_context else 0.5
        
        # Get a relationship-appropriate mood
        relationship_level = self._get_relationship_level(user.id)
        
        # Get suggested mood for response based on context analysis
        suggested_mood = self.nlp.suggest_mood_for_response(message_context, relationship_level) if self.nlp else "neutral"
        
        # Determine response length treatment using contextual analysis
        # Rather than hardcoding keywords, use the message context for natural handling
        long_response = len(response) > 500
        
        # Use the full NLP context to make a deeper, more human-like decision
        should_keep_full_response = False
        
        # Use the complete message context to determine when full responses are appropriate
        if message_context:
            # Messages with emotional depth or personal topics often deserve longer responses
            topics = message_context.get("semantic_topics", [])
            intent = message_context.get("intent", "")
            emotion_value = message_context.get("emotion", "")
            intensity_value = message_context.get("intensity", 0.5)
            
            # Consider emotional intensity for personal topics - humans give more detailed responses
            # to personally meaningful or emotional conversations
            if intensity_value > 0.7:  # Strong emotional messages deserve fuller responses
                should_keep_full_response = True
            
            # Keep full responses for meaningful conversation topics regardless of length
            meaningful_topics = ["personal", "relationship", "departure", "serious_discussion"]
            if any(topic in meaningful_topics for topic in topics):
                should_keep_full_response = True
                
            # Special intents that deserve detailed responses regardless of length
            important_intents = ["personal_sharing", "emotional_support", "departure", 
                                "deep_question", "apology", "vulnerability"]
            if intent in important_intents:
                should_keep_full_response = True
                
            # High emotional stakes conversations (fear, sadness, deeply personal)
            if emotion_value in ["sadness", "fear"] and intensity_value > 0.4:
                should_keep_full_response = True
                
            # High relationship impact messages always get full responses
            relationship_signals = message_context.get("relationship_signals", {})
            if relationship_signals.get("intimacy", 0) > 0.7 or relationship_signals.get("romantic_interest", 0) > 0.7:
                should_keep_full_response = True
        
        # Apply response format based on context - this is what humans do
        if long_response and not should_keep_full_response:
            # Only truncate when appropriate based on context
            response = response.split("\n\n")[0] 
            suggested_mood = "tsundere_cold"  # Briefer mode for mundane topics
        
        # Format and send the response
        formatted_response = format_response(
            response, 
            emotion=emotion,
            mood=suggested_mood,
            intensity=intensity,
            username=user.first_name or "user"
        )
        
        # Add invisible marker to identify chat messages
        formatted_response = f"{formatted_response}\u200C"
        await update.message.reply_html(formatted_response)
    
    async def _get_user_info(self, user) -> Dict[str, Any]:
        is_admin = user.id in ADMIN_IDS or (self.db and self.db.is_admin(user.id))
        if self.db:
            self._create_or_update_user(user)
            relationship_level = self._get_relationship_level(user.id)
        else:
            relationship_level = 0
        return {
            'is_admin': is_admin,
            'relationship_level': relationship_level
        }

    def _get_relationship_context(self, user: Any, relationship_level: int, is_admin: bool) -> str:
        first_name = getattr(user, 'first_name', None) or "user"
        if is_admin:
            return (
                f"PENTING: {first_name} adalah admin bot dan orang yang sangat special untuk Alya. "
                f"Hubungan Alya dengan {first_name} sangat dekat, seperti pacar, "
                f"tapi Alya tetap tsundere. Alya sangat senang bisa mengobrol dengannya dan "
                f"sangat perhatian padanya. Gunakan sesekali honorifik -sama dan tunjukkan "
                f"bahwa Alya sangat menyayangi {first_name}."
            )
        relationship_contexts = {
            0: (
                f"Hubungan Alya dengan {first_name}: STRANGER. "
                f"Alya masih bersikap formal, agak dingin dan tsundere. "
                f"Masih menggunakan formal speech pattern."
            ),
            1: (
                f"Hubungan Alya dengan {first_name}: ACQUAINTANCE. "
                f"Alya mulai sedikit terbuka, tapi masih tsundere. "
                f"Sesekali menunjukkan sisi caring tapi cepat defensive jika dipuji."
            ),
            2: (
                f"Hubungan Alya dengan {first_name}: FRIEND. "
                f"Alya cukup dekat dan nyaman, sisi tsundere berkurang, "
                f"lebih banyak menunjukkan sisi dere dan lebih expresif. "
                f"Alya lebih banyak berbagi cerita pribadi."
            ),
            3: (
                f"Hubungan Alya dengan {first_name}: CLOSE FRIEND. "
                f"Alya sangat nyaman dan terbuka, masih tsundere tapi sangat caring. "
                f"Kadang menggunakan nama langsung tanpa honorifik. "
                f"Alya sangat perhatian dan menganggap {first_name} sebagai "
                f"orang yang sangat penting dalam hidupnya."
            )
        }
        return relationship_contexts.get(relationship_level, "")
    
    def _update_affection_from_context(self, user_id: int, message_context: Dict[str, Any]) -> None:
        if not message_context:
            return
        relationship_signals = message_context.get("relationship_signals", {})
        affection_delta = 0
        affection_delta += relationship_signals.get("friendliness", 0) * 10
        affection_delta += relationship_signals.get("romantic_interest", 0) * 20
        affection_delta -= relationship_signals.get("conflict", 0) * 15
        intent = message_context.get("intent", "")
        if intent == "gratitude":
            affection_delta += 5
        elif intent == "apology":
            affection_delta += 3
        elif intent == "affection":
            affection_delta += 10
        if abs(affection_delta) >= 1:
            affection_delta = round(affection_delta)
            self.db.update_affection(user_id, affection_delta)