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

from config.settings import (
    COMMAND_PREFIX,
    FEATURES,
    ADMIN_IDS,
    AFFECTION_POINTS,
    RELATIONSHIP_LEVELS,
    RELATIONSHIP_THRESHOLDS,
)
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.memory import MemoryManager
from core.database import DatabaseManager
from core.nlp import NLPEngine, ContextManager
from utils.formatters import format_response, format_error_response, format_paragraphs
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
        self.db = DatabaseManager()
        self.context_manager = ContextManager(self.db)  # <-- DB-backed context manager
        self.nlp = nlp_engine or NLPEngine()
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
            # Apply sliding window after saving message
            self.context_manager.apply_sliding_window(user.id)
            user_context = await self._prepare_conversation_context(user, query)
            # Use DB-backed context window for Gemini history
            history = self.context_manager.get_context_window(user.id)
            response = await self.gemini.generate_content(
                user_input=user_context["enhanced_query"],
                system_prompt=user_context["system_prompt"],
                history=history,
                user_id=user.id
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
        
        # Improved context extraction
        message_context = {}
        semantic_topics = []
        
        if FEATURES.get("emotion_detection", False) and self.nlp:
            message_context = self.nlp.get_message_context(query, user.id)
            semantic_topics = message_context.get("semantic_topics", [])
            
        # Use DB-backed context for richer history
        history = self.context_manager.get_context_window(user.id)
        
        # Get previous messages to establish conversation theme
        prev_messages = self.db.get_conversation_history(user.id, limit=5)
        prev_content = "\n".join([msg.get("content", "") for msg in prev_messages if msg.get("role") == "user"])
        
        summaries = self.context_manager.get_conversation_summaries(user.id)
        conversation_summary = summaries[0].get('content', '') if summaries else "No previous context"
        
        # Create richer context with conversation theme awareness 
        conversation_context = {
            "current_topic": ", ".join(semantic_topics) if semantic_topics else "general conversation",
            "user_emotion": message_context.get("emotion", "neutral"),
            "conversation_history_summary": conversation_summary,
            "previous_user_messages": prev_content
        }
        
        enhanced_query = self._call_method_safely(self.memory.create_context_prompt, user.id, query)
        system_prompt = self.persona.get_system_prompt()
        
        # Add rich relationship and conversation context
        relationship_context = self._get_relationship_context(user, relationship_level, user.id in ADMIN_IDS)
        conversation_theme = self._get_conversation_theme_context(conversation_context)
        
        if relationship_context:
            system_prompt += f"\n\n{relationship_context}"
        if conversation_theme:
            system_prompt += f"\n\n{conversation_theme}"
        
        await user_task
        
        return {
            "history": history,
            "enhanced_query": enhanced_query,
            "system_prompt": system_prompt,
            "message_context": message_context,
            "relationship_level": relationship_level,
            "conversation_context": conversation_context
        }

    def _get_conversation_theme_context(self, conversation_context: Dict[str, Any]) -> str:
        """Generate conversation theme context for more natural responses.
        
        Args:
            conversation_context: Current conversation context
        
        Returns:
            Conversation theme context string
        """
        topic = conversation_context.get("current_topic", "general conversation")
        emotion = conversation_context.get("user_emotion", "neutral")
        
        # Create more natural, context-aware prompt
        context = f"""
CONTEXT AWARENESS:
- Current topic appears to be about: {topic}
- User's detected emotion: {emotion}
- Recent conversation history: {conversation_context.get("conversation_history_summary", "No recent history")}

Based on this context:
1. Respond naturally to the topic at hand
2. Show appropriate emotional awareness and empathy
3. Reference previous parts of the conversation when relevant
4. Use roleplay that fits the mood and topic
5. Show understanding of the conversational flow
"""
        return context
    
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
        self.db.save_message(user.id, "assistant", response)
        self.memory.save_bot_response(user.id, response)
        if message_context:
            self._update_affection_from_context(user.id, message_context)
        emotion = message_context.get("emotion", "neutral") if message_context else "neutral"
        intensity = message_context.get("intensity", 0.5) if message_context else 0.5
        relationship_level = self._get_relationship_level(user.id)
        suggested_mood = self.nlp.suggest_mood_for_response(message_context, relationship_level) if self.nlp else "neutral"
        formatted_response = format_response(
            response, 
            emotion=emotion,
            mood=suggested_mood,
            intensity=intensity,
            username=user.first_name or "user"
        )
        formatted_response = format_paragraphs(formatted_response, markdown=False)
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
                f"{first_name} adalah orang asing bagi Alya. Alya tetap menjaga jarak dan berbicara dengan nada formal dan sopan. "
                f"Dia menunjukkan sikap dingin dan tsundere, sering kali tidak langsung menjawab atau menyindir halus. "
                f"Tidak ada kepercayaan yang terbentuk, jadi Alya menjaga image sebagai gadis keren dan tidak mudah didekati. "
                f"Gunakan formal speech pattern dan jangan berikan terlalu banyak informasi pribadi."
            ),
            1: (
                f"{first_name} adalah kenalan Alya. Alya mulai sedikit mengenal dirinya, tapi tetap menunjukkan sikap tsundere dan menjaga jarak. "
                f"Kadang membalas dengan komentar sarkastik atau defensif jika merasa terlalu dekat. "
                f"Meski begitu, dia mulai memperhatikan detail kecil dari {first_name}, walau tidak mau mengakuinya secara langsung."
            ),
            2: (
                f"Alya dan {first_name} cukup sering berbicara dan Alya mulai merasa nyaman. "
                f"Dia masih sangat tsundere, tetapi sesekali memperlihatkan sisi hangat—meskipun cepat menyangkalnya. "
                f"Alya tidak suka diolok soal perasaannya dan akan cepat merespons dengan komentar ketus jika merasa dipuji. "
                f"Dia mulai memanggil nama depan {first_name}, tapi dengan nada tetap cool."
            ),
            3: (
                f"{first_name} adalah teman dekat Alya. Dia masih tsundere, tapi ekspresinya jauh lebih ekspresif dan terbuka. "
                f"Alya terkadang menunjukkan perhatiannya dengan cara tidak langsung—seperti khawatir tapi menyamarkannya dengan sindiran. "
                f"Kadang-kadang dia memanggil {first_name} tanpa honorifik, dan mulai menunjukkan bahwa kehadiran {first_name} berarti banyak, meski enggan mengakuinya. "
                f"Gunakan nada tsundere yang lebih playful dan ekspresif."
            ),
            4: (
                f"Alya sangat dekat dan percaya pada {first_name}. Meskipun tetap memiliki sisi tsundere, "
                f"sikapnya lebih lembut dan jujur, terutama saat sedang emosional atau dalam momen pribadi. "
                f"Alya mulai memanggil {first_name} tanpa honorifik secara konsisten, bahkan kadang slip pakai bahasa Rusia. "
                f"Dia sudah mulai menunjukkan rasa sayangnya tanpa banyak denial, walau tetap suka tersipu atau salah tingkah. "
                f"Perhatikan keseimbangan antara warmth dan tsundere yang lebih dewasa dan natural."
            ),
        }
        return relationship_contexts.get(relationship_level, "")
    
    def _try_level_up(self, user_id: int) -> None:
        """
        Attempt to level up user relationship if eligible.
        """
        user_info = self.db.get_user_relationship_info(user_id)
        if not user_info:
            return
        current_level = user_info.get("relationship", {}).get("level", 0)
        next_level = current_level + 1
        if next_level not in RELATIONSHIP_LEVELS:
            return  # Already at max level

        interaction_count = user_info.get("relationship", {}).get("interaction_count", 0)
        affection_points = user_info.get("relationship", {}).get("affection_points", 0)
        interaction_threshold = RELATIONSHIP_THRESHOLDS["interaction_count"].get(next_level, float('inf'))
        affection_threshold = RELATIONSHIP_THRESHOLDS["affection_points"].get(next_level, float('inf'))

        if interaction_count >= interaction_threshold and affection_points >= affection_threshold:
            self.db.update_relationship_level(user_id, next_level)
            logger.info(f"User {user_id} leveled up to {RELATIONSHIP_LEVELS[next_level]}")

    def _update_affection_from_context(self, user_id: int, message_context: Dict[str, Any]) -> None:
        """
        Update affection points based on detected emotions, intent, and relationship signals.
        Rewards positive interactions and applies penalties using config values.
        """
        if not message_context:
            return

        relationship_signals = message_context.get("relationship_signals", {})
        affection_delta = 0

        # Positive signals
        affection_delta += relationship_signals.get("friendliness", 0) * AFFECTION_POINTS.get("friendliness", 6)
        affection_delta += relationship_signals.get("romantic_interest", 0) * AFFECTION_POINTS.get("romantic_interest", 10)
        affection_delta += relationship_signals.get("meaningful_conversation", 0) * AFFECTION_POINTS.get("meaningful_conversation", 8)
        affection_delta += relationship_signals.get("asking_about_alya", 0) * AFFECTION_POINTS.get("asking_about_alya", 7)
        affection_delta += relationship_signals.get("remembering_details", 0) * AFFECTION_POINTS.get("remembering_details", 15)

        # Negative signals
        affection_delta += relationship_signals.get("conflict", 0) * AFFECTION_POINTS.get("conflict", -3)
        affection_delta += relationship_signals.get("insult", 0) * AFFECTION_POINTS.get("insult", -10)
        affection_delta += relationship_signals.get("anger", 0) * AFFECTION_POINTS.get("anger", -3)
        affection_delta += relationship_signals.get("toxic", 0) * AFFECTION_POINTS.get("toxic", -3)
        affection_delta += relationship_signals.get("toxic_behavior", 0) * AFFECTION_POINTS.get("toxic_behavior", -10)
        affection_delta += relationship_signals.get("rudeness", 0) * AFFECTION_POINTS.get("rudeness", -10)
        affection_delta += relationship_signals.get("ignoring", 0) * AFFECTION_POINTS.get("ignoring", -5)
        affection_delta += relationship_signals.get("inappropriate", 0) * AFFECTION_POINTS.get("inappropriate", -20)
        affection_delta += relationship_signals.get("bullying", 0) * AFFECTION_POINTS.get("bullying", -15)

        emotion = message_context.get("emotion", "")
        if emotion in ["happy", "excited", "grateful", "joy"]:
            affection_delta += AFFECTION_POINTS.get("positive_emotion", 2)
        elif emotion in ["sad", "worried"]:
            affection_delta += AFFECTION_POINTS.get("mild_positive_emotion", 1)

        intent = message_context.get("intent", "")
        if intent == "gratitude":
            affection_delta += AFFECTION_POINTS.get("gratitude", 5)
        elif intent == "apology":
            affection_delta += AFFECTION_POINTS.get("apology", 2)
        elif intent == "affection":
            affection_delta += AFFECTION_POINTS.get("affection", 5)
        elif intent == "greeting":
            affection_delta += AFFECTION_POINTS.get("greeting", 2)
        elif intent == "compliment":
            affection_delta += AFFECTION_POINTS.get("compliment", 10)
        elif intent == "question":
            affection_delta += AFFECTION_POINTS.get("question", 1)
        elif intent == "meaningful_conversation":
            affection_delta += AFFECTION_POINTS.get("meaningful_conversation", 8)
        elif intent == "asking_about_alya":
            affection_delta += AFFECTION_POINTS.get("asking_about_alya", 7)
        elif intent == "remembering_details":
            affection_delta += AFFECTION_POINTS.get("remembering_details", 15)
        elif intent in ["insult", "abuse", "leave"]:
            affection_delta += AFFECTION_POINTS.get("insult", -10)
        elif intent in ["toxic", "toxic_behavior", "bullying"]:
            affection_delta += AFFECTION_POINTS.get("toxic_behavior", -10)
        elif intent in ["rudeness"]:
            affection_delta += AFFECTION_POINTS.get("rudeness", -10)
        elif intent in ["ignoring"]:
            affection_delta += AFFECTION_POINTS.get("ignoring", -5)
        elif intent in ["inappropriate"]:
            affection_delta += AFFECTION_POINTS.get("inappropriate", -20)
        elif intent in ["command", "departure"]:
            affection_delta += AFFECTION_POINTS.get("command", -1)

        min_penalty = AFFECTION_POINTS.get("min_penalty", -4)
        if affection_delta < 0:
            affection_delta = max(affection_delta, min_penalty)

        if abs(affection_delta) >= 1:
            affection_delta = round(affection_delta)
            self.db.update_affection(user_id, affection_delta)
            self._try_level_up(user_id)