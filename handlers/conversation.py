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
        """Initialize conversation handler.
        
        Args:
            gemini_client: Gemini client for AI generation
            persona_manager: Persona manager for response formatting
            memory_manager: Memory manager for conversation context
            nlp_engine: Optional NLP engine for emotion detection
        """
        self.gemini = gemini_client
        self.persona = persona_manager
        self.memory = memory_manager
        self.nlp = nlp_engine or NLPEngine()
        self.db = DatabaseManager()
        
        # Initialize specialized handlers - now with correct parameters
        self.roast_handler = RoastHandler(gemini_client, persona_manager)
    
    def get_handlers(self) -> List:
        """Get conversation handlers.
        
        Returns:
            List of handlers for the dispatcher
        """
        handlers = [
            # Private chat: no prefix needed
            MessageHandler(
                filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
                self.chat_command
            ),
            # Group: use prefix or reply to Alya
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
        
        # Add specialized handlers
        handlers.extend(self.roast_handler.get_handlers())
        
        return handlers
    
    # Helper methods to avoid duplicate logic
    def _create_or_update_user(self, user) -> bool:
        """Create or update user in database.
        
        Args:
            user: Telegram user object
            
        Returns:
            True if user is admin
        """
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
        """Get relationship level for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Relationship level (0-3)
        """
        user_info = self.db.get_user_relationship_info(user_id)
        return user_info.get("relationship", {}).get("level", 0) if user_info else 0
    
    async def _send_error_response(self, update: Update, username: str) -> None:
        """Send error response to user.
        
        Args:
            update: The update from Telegram
            username: User's first name
        """
        error_message = self.persona.get_error_message(username=username or "user")
        formatted_error = format_error_response(error_message)
        await update.message.reply_html(formatted_error)
            
    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle chat command with AI.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        message_text = update.message.text

        # --- Tambahan untuk group: cek reply_to_message ---
        reply_context = ""
        is_reply_to_alya = False
        if update.message.reply_to_message:
            replied = update.message.reply_to_message
            # Cek apakah reply ke Alya (bot)
            if replied.from_user and replied.from_user.is_bot:
                reply_context = replied.text or ""
                is_reply_to_alya = True

        # Extract the actual query (remove command prefix jika ada)
        if update.message.chat.type in ["group", "supergroup"]:
            # Di group: kalau reply ke Alya, boleh tanpa prefix
            if is_reply_to_alya:
                query = message_text.strip()
            else:
                # Kalau bukan reply ke Alya, tetap harus pakai prefix
                if message_text.startswith(COMMAND_PREFIX):
                    query = message_text.replace(COMMAND_PREFIX, "", 1).strip()
                else:
                    # Bukan reply ke Alya dan tanpa prefix, abaikan (biar ga spam)
                    return
        else:
            # Private chat: bebas, langsung chat
            query = message_text.strip()

        # Gabungkan context reply (kalau ada)
        if reply_context:
            query = f"{reply_context}\n\n{query}"
        
        if not query:
            # Empty query, send help message
            help_message = self.persona.get_help_message(
                username=user.first_name or "user",
                prefix=COMMAND_PREFIX
            )
            formatted_help = format_response(help_message, "neutral")
            await update.message.reply_html(formatted_help)
            return
        
        # Send typing action for both private and group chat, including topics
        chat = update.effective_chat
        try:
            # For group topics (forum), send typing to the correct message thread
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
            # Always create/update user and stats in DB
            self._create_or_update_user(user)
            # Save user message to DB (conversations, user_stats, users)
            self.db.save_message(user.id, "user", query)

            # Optionally: update memory context (if needed for Gemini)
            self.memory.save_user_message(user.id, query)

            # Prepare context for Gemini
            user_context = await self._prepare_conversation_context(user, query)

            # Generate response from Gemini
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
        """Prepare all necessary context for conversation response.
        
        Args:
            user: Telegram user object
            query: User's message text
            
        Returns:
            Dictionary with all context info for response generation
        """
        # Start async tasks for operations that can run in parallel
        user_task = asyncio.create_task(self._get_user_info(user))
        
        # Save user message
        self.memory.save_user_message(user.id, query)
        
        # Get relationship level for context
        relationship_level = self._get_relationship_level(user.id)
        
        # Analyze user message with NLP for deeper understanding
        message_context = {}
        if FEATURES.get("emotion_detection", False) and self.nlp:
            message_context = self.nlp.get_message_context(query, user.id)
        
        # Get conversation history
        history = self._call_method_safely(self.memory.get_conversation_context, user.id)
        
        # Create context-aware prompt
        enhanced_query = self._call_method_safely(self.memory.create_context_prompt, user.id, query)
        
        # Get system prompt from persona
        system_prompt = self.persona.get_system_prompt()
        
        # Add relationship context to system prompt
        relationship_context = self._get_relationship_context(user, relationship_level, user.id in ADMIN_IDS)
        if relationship_context:
            system_prompt += f"\n\n{relationship_context}"
        
        # Wait for parallel tasks to complete
        await user_task
        
        # Log message context for debugging
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
        """Call a method safely, handling both sync and async methods.
        
        Args:
            method: Method to call
            *args: Arguments for method
            **kwargs: Keyword arguments for method
            
        Returns:
            Result of method call
        """
        if asyncio.iscoroutinefunction(method):
            # We can't return a coroutine directly, so we'll need to use
            # asyncio.run in calling code - but be careful about event loop issues
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
        """Process Gemini response and send it to user.
        
        Args:
            update: The update from Telegram
            user: Telegram user object
            response: Response text from Gemini
            message_context: Message context from NLP
        """
        # Save bot response to DB (conversations, user_stats, users)
        self.db.save_message(user.id, "assistant", response)
        # Optionally: update memory context
        self.memory.save_bot_response(user.id, response)

        # Update affection if context available
        if message_context:
            self._update_affection_from_context(user.id, message_context)

        # Format and send response
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
        await update.message.reply_html(formatted_response)
    
    async def _get_user_info(self, user) -> Dict[str, Any]:
        """Get user information with optimized DB access.
        
        Args:
            user: Telegram user object
            
        Returns:
            Dict containing user info including relationship level and admin status
        """
        is_admin = user.id in ADMIN_IDS or (self.db and self.db.is_admin(user.id))
        
        # Create or update user record
        if self.db:
            self._create_or_update_user(user)
            
            # Get relationship level
            relationship_level = self._get_relationship_level(user.id)
        else:
            relationship_level = 0
            
        return {
            'is_admin': is_admin,
            'relationship_level': relationship_level
        }

    def _get_relationship_context(self, user: Any, relationship_level: int, is_admin: bool) -> str:
        """Get relationship-specific context to add to system prompt.
        
        Args:
            user: Telegram user object
            relationship_level: Current relationship level
            is_admin: Whether the user is an admin
            
        Returns:
            Relationship context string
        """
        # Get user's first name safely with fallback
        first_name = getattr(user, 'first_name', None) or "user"
        
        if is_admin:
            return (
                f"PENTING: {first_name} adalah admin bot dan orang yang sangat special untuk Alya. "
                f"Hubungan Alya dengan {first_name} sangat dekat, seperti pacar, "
                f"tapi Alya tetap tsundere. Alya sangat senang bisa mengobrol dengannya dan "
                f"sangat perhatian padanya. Gunakan sesekali honorifik -sama dan tunjukkan "
                f"bahwa Alya sangat menyayangi {first_name}."
            )
        
        # Map relationship levels to context
        relationship_contexts = {
            0: (  # Stranger
                f"Hubungan Alya dengan {first_name}: STRANGER. "
                f"Alya masih bersikap formal, agak dingin dan tsundere. "
                f"Masih menggunakan formal speech pattern."
            ),
            1: (  # Acquaintance
                f"Hubungan Alya dengan {first_name}: ACQUAINTANCE. "
                f"Alya mulai sedikit terbuka, tapi masih tsundere. "
                f"Sesekali menunjukkan sisi caring tapi cepat defensive jika dipuji."
            ),
            2: (  # Friend
                f"Hubungan Alya dengan {first_name}: FRIEND. "
                f"Alya cukup dekat dan nyaman, sisi tsundere berkurang, "
                f"lebih banyak menunjukkan sisi dere dan lebih expresif. "
                f"Alya lebih banyak berbagi cerita pribadi."
            ),
            3: (  # Close Friend
                f"Hubungan Alya dengan {first_name}: CLOSE FRIEND. "
                f"Alya sangat nyaman dan terbuka, masih tsundere tapi sangat caring. "
                f"Kadang menggunakan nama langsung tanpa honorifik. "
                f"Alya sangat perhatian dan menganggap {first_name} sebagai "
                f"orang yang sangat penting dalam hidupnya."
            )
        }
        
        return relationship_contexts.get(relationship_level, "")
    
    def _update_affection_from_context(self, user_id: int, message_context: Dict[str, Any]) -> None:
        """Update affection points based on message context.
        
        Args:
            user_id: Telegram user ID
            message_context: Context information from the message
        """
        # If no context available, do nothing
        if not message_context:
            return
            
        # Extract relationship signals
        relationship_signals = message_context.get("relationship_signals", {})
        
        # Calculate affection change
        affection_delta = 0
        
        # Positive signals
        affection_delta += relationship_signals.get("friendliness", 0) * 10
        affection_delta += relationship_signals.get("romantic_interest", 0) * 20
        
        # Negative signals
        affection_delta -= relationship_signals.get("conflict", 0) * 15
        
        # Apply based on intent
        intent = message_context.get("intent", "")
        if intent == "gratitude":
            affection_delta += 5
        elif intent == "apology":
            affection_delta += 3
        elif intent == "affection":
            affection_delta += 10
        
        # Only update if there's a meaningful change
        if abs(affection_delta) >= 1:
            # Round to integer
            affection_delta = round(affection_delta)
            self.db.update_affection(user_id, affection_delta)