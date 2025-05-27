"""
Conversation handlers for Alya Bot.
"""
import logging
import random
from typing import Dict, List, Optional, Any
import asyncio

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config.settings import COMMAND_PREFIX, FEATURES, ADMIN_IDS, SAUCENAO_PREFIX
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
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("stats", self.stats_command),
            CommandHandler("reset", self.reset_command),
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{COMMAND_PREFIX}\\b"), 
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
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Check if user is admin and create/update user record
        is_admin = self._create_or_update_user(user)
        
        # Get appropriate greeting based on relationship level
        relationship_level = self._get_relationship_level(user.id)
        
        # Choose appropriate roleplay expression based on relationship level
        roleplay_actions = {
            0: "sedikit menunduk dengan formal",  # Stranger
            1: "tersenyum kecil dengan sikap formal",  # Acquaintance
            2: "tersenyum ramah",  # Friend
            3: "tersenyum lebar dengan mata berbinar"  # Close Friend
        }
        
        roleplay = roleplay_actions.get(relationship_level, "tersenyum menyambut")
        
        # Special greeting for admins
        if is_admin:
            greeting = f"<i>{roleplay}</i>\n\nAh! {user.first_name}-sama! Alya sangat senang melihatmu kembali~ 💖"
        else:
            # Get greeting from persona with proper roleplay
            greeting = f"<i>{roleplay}</i>\n\n{self.persona.get_greeting(username=user.first_name or 'user')}"
        
        await update.message.reply_html(greeting)
        
        # Add a small delay before sending help message
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Send help message after greeting with proper formatting
        help_message = self._format_help_message(user.first_name or "user")
        await update.message.reply_html(help_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Format help message with proper HTML and roleplay action
        help_message = self._format_help_message(user.first_name or "user")
        await update.message.reply_html(help_message)
    
    def _format_help_message(self, username: str) -> str:
        """Format help message with proper HTML formatting and roleplay.
        
        Args:
            username: User's first name
            
        Returns:
            Formatted HTML help message
        """
        # Get base message from persona
        base_message = self.persona.get_help_message(
            username=username,
            prefix=COMMAND_PREFIX
        )
        
        # Random roleplay actions for help command
        roleplay_options = [
            "membuka buku catatan OSIS dengan rapi",
            "mengeluarkan papan klip dengan daftar bantuan",
            "merapikan kacamata dengan sikap profesional",
            "menunjukkan pose wakil ketua OSIS yang berwibawa"
        ]
        
        # Choose a random roleplay action
        roleplay = random.choice(roleplay_options)
        
        # Format with HTML and custom roleplay
        return f"<i>{roleplay}</i>\n\n{base_message}"
        
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command to show relationship stats.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Get user's relationship info
        relationship_info = self.db.get_user_relationship_info(user.id)
        
        if not relationship_info:
            await update.message.reply_html(
                "<i>Hmph! Alya belum mengenalmu dengan baik...</i> 😤"
            )
            return
        
        # Format stats message based on relationship level
        rel = relationship_info.get("relationship", {})
        aff = relationship_info.get("affection", {})
        stats = relationship_info.get("stats", {})
        
        # Format progress bar for relationship level
        rel_progress = self._format_progress_bar(min(100, rel.get("progress_percent", 0)))
        
        # Format affection bar
        aff_progress = self._format_progress_bar(min(100, aff.get("progress_percent", 0)))
        
        # Different messages based on relationship level
        level_messages = [
            "<i>Hmm? K-kenapa kamu ingin tahu? Alya belum mengenalmu!</i> 😤",
            "<i>Alya mulai mengingatmu sedikit...</i> 🤔",
            "<i>Alya pikir kita sudah cukup berteman...</i> ✨",
            "<i>A-alya senang bisa mengobrol denganmu sejauh ini!</i> 💫"
        ]
        
        level_msg = level_messages[min(rel.get("level", 0), len(level_messages)-1)]
        
        # Format the stats message
        stats_message = (
            f"<b>Statistik Hubungan {user.first_name}</b>\n\n"
            f"<b>Level:</b> {rel.get('level', 0)} - {rel.get('name', 'Stranger')}\n"
            f"{rel_progress} {rel.get('progress_percent', 0):.1f}%\n"
            f"<b>Interaksi:</b> {rel.get('interactions', 0)}/{rel.get('next_level_at', '∞')}\n\n"
            
            f"<b>Affection Points:</b> {aff.get('points', 0)}\n"
            f"{aff_progress}\n\n"
            
            f"<b>Total Pesan:</b> {stats.get('total_messages', 0)}\n"
            f"<b>Interaksi Positif:</b> {stats.get('positive_interactions', 0)}\n"
            f"<b>Interaksi Negatif:</b> {stats.get('negative_interactions', 0)}\n\n"
            f"{level_msg}"
        )
        
        await update.message.reply_html(stats_message)
    
    def _format_progress_bar(self, percent: float, length: int = 10) -> str:
        """Format a progress bar for display.
        
        Args:
            percent: Percentage (0-100)
            length: Length of the progress bar
            
        Returns:
            Formatted progress bar string
        """
        filled_length = int(length * percent / 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return f"[{bar}]"
        
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle memory reset command.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        success = self.memory.reset_memory(user.id)
        
        if success:
            reset_message = self.persona.get_memory_reset_message(
                username=user.first_name or "user"
            )
            formatted_reset = format_response(reset_message, "surprised")
            await update.message.reply_html(formatted_reset)
        else:
            await self._send_error_response(update, user.first_name)
    
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
        
        # Extract the actual query (remove command prefix)
        query = message_text.replace(COMMAND_PREFIX, "", 1).strip()
        
        if not query:
            # Empty query, send help message
            help_message = self.persona.get_help_message(
                username=user.first_name or "user",
                prefix=COMMAND_PREFIX
            )
            formatted_help = format_response(help_message, "neutral")
            await update.message.reply_html(formatted_help)
            return
        
        # Send typing action first - ASAP for user feedback
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        try:
            # Check or create user
            is_admin = self._create_or_update_user(user)
            
            # Start parallel processing to improve latency
            user_context = await self._prepare_conversation_context(user, query)
            
            # Generate response from Gemini - this is the main bottleneck
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
        # Save bot response to memory
        if asyncio.iscoroutinefunction(self.memory.save_bot_response):
            save_task = asyncio.create_task(self.memory.save_bot_response(user.id, response))
            # Ensure memory saving completes but don't block the response
            await save_task
        else:
            self.memory.save_bot_response(user.id, response)
        
        # Process response in parallel while saving to memory
        if "emotion" in message_context:
            if asyncio.iscoroutinefunction(self.db.update_last_mood):
                asyncio.create_task(
                    self.db.update_last_mood(user.id, message_context.get("emotion", "neutral"))
                )
            else:
                self.db.update_last_mood(user.id, message_context.get("emotion", "neutral"))
        
        # Update affection based on message context
        self._update_affection_from_context(user.id, message_context)
        
        # Get user's emotional state and intensity for response formatting
        emotion = message_context.get("emotion", "neutral")
        intensity = message_context.get("intensity", 0.5)
        
        # Get user's relationship level
        relationship_level = self._get_relationship_level(user.id)
        
        # Get appropriate mood for the response based on context
        suggested_mood = self.nlp.suggest_mood_for_response(message_context, relationship_level)
        
        # Format response with all the context information
        formatted_response = format_response(
            response, 
            emotion=emotion,
            mood=suggested_mood,
            intensity=intensity,
            username=user.first_name or "user"
        )
        
        # Send response to user
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