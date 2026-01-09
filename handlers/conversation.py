"""
Conversation for Alya Bot.
"""
import logging
import random
from typing import Dict, List, Optional, Any
import asyncio
import re

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
    DEFAULT_LANGUAGE
)
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.memory import MemoryManager
from database.database_manager import db_manager, get_user_lang
from core.nlp import NLPEngine, ContextManager
from utils.formatters import format_response, format_error_response, format_paragraphs, format_persona_response
from core.sticker_manager import StickerManager


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
        self.db = db_manager
        self.context_manager = ContextManager(self.db)  # <-- DB-backed context manager
        self.nlp = nlp_engine or NLPEngine()
    
    def get_handlers(self) -> List:
        handlers = [
            MessageHandler(
                filters.TEXT 
                & filters.ChatType.PRIVATE 
                & ~filters.COMMAND 
                & ~filters.Regex(r"^!(?!ai)"),  # Ignore ! commands except !ai
                self.chat_command
            ),
            MessageHandler(
                (
                    filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND &
                    ~filters.Regex(r"^!(?!ai)") &  # Ignore ! commands except !ai (same as private)
                    (
                        filters.Regex(f"^{COMMAND_PREFIX}") |
                        filters.REPLY
                    )
                ),
                self.chat_command
            ),
        ]
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
    
    async def _send_error_response(self, update: Update, username: str, lang: str) -> None:
        error_message = self.persona.get_error_message(username=username or "user", lang=lang)
        formatted_error = format_error_response(error_message)
        await update.message.reply_html(formatted_error)
            
    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message_text = update.message.text
        lang = get_user_lang(user.id) # Get user language

        reply_context = ""
        is_reply_to_alya = False
        replied_message_is_conversation = False
        if update.message.reply_to_message:
            replied = update.message.reply_to_message
            if replied.from_user and replied.from_user.is_bot:
                if replied.from_user.id == context.bot.id:
                    reply_context = replied.text or ""
                    is_reply_to_alya = True
                    if replied.text and replied.text.endswith("\u200C"):
                        replied_message_is_conversation = True

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
                prefix=COMMAND_PREFIX,
                lang=lang  # Pass language parameter
            )
            formatted_help = format_persona_response(help_message, use_html=True)
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
            self.context_manager.apply_sliding_window(user.id)
            
            # === STEP 1: Analyze message context FIRST (for affection calculation) ===
            message_context = {}
            if FEATURES.get("emotion_detection", False) and self.nlp:
                message_context = self.nlp.get_message_context(query, user.id)
                logger.debug(f"Message context for user {user.id}: {message_context}")
            
            # === STEP 2: Calculate affection delta (before applying) ===
            affection_delta = 0
            if message_context:
                affection_delta = self._calculate_affection_delta(user.id, message_context)
            
            # === STEP 3: Get current mood and calculate new mood ===
            from core.mood_manager import MoodManager
            mood_manager = MoodManager()
            
            current_mood_data = self.db.get_user_mood(user.id)
            user_info = self.db.get_user_relationship_info(user.id)
            
            new_mood_state = mood_manager.calculate_mood(
                current_mood=current_mood_data["mood"],
                current_intensity=current_mood_data["intensity"],
                affection_delta=affection_delta,
                emotion_context=message_context,
                relationship_level=user_info["relationship_level"],
                last_mood_change=current_mood_data["last_change"]
            )
            
            # === STEP 4: Apply mood modifier to affection delta ===
            mood_modifier = mood_manager.get_affection_modifier(
                new_mood_state.mood, 
                affection_delta
            )
            modified_affection_delta = int(affection_delta * mood_modifier)
            
            logger.info(
                f"[MOOD] User {user.id}: {current_mood_data['mood']} → {new_mood_state.mood} "
                f"(intensity: {new_mood_state.intensity}) | "
                f"Affection: {affection_delta} → {modified_affection_delta} (×{mood_modifier:.1f})"
            )
            
            # === STEP 5: Update affection with mood-modified delta ===
            if modified_affection_delta != 0:
                self.db.update_affection(user.id, modified_affection_delta)
            
            # === STEP 6: Update mood in database ===
            updated_history = mood_manager.add_to_mood_history(
                current_mood_data["history"],
                new_mood_state
            )
            self.db.update_user_mood(
                user.id,
                new_mood_state.mood,
                new_mood_state.intensity,
                updated_history
            )
            
            # === STEP 7: Increment interaction count (will recalculate level) ===
            self.db.increment_interaction_count(user.id)
            
            # === STEP 8: Prepare context with LATEST relationship level and MOOD ===
            user_context = await self._prepare_conversation_context(
                user, query, lang, message_context, new_mood_state, mood_manager
            )
            history = self.context_manager.get_context_window(user.id)
            response = await self.gemini.generate_response(
                user_id=user.id,
                username=user.first_name or "user",
                message=user_context["enhanced_query"],
                context=user_context["system_prompt"],
                relationship_level=user_context["relationship_level"],
                is_admin=user.id in ADMIN_IDS or self.db.is_admin(user.id),
                lang=lang,
                retry_count=3,
                is_media_analysis=False,
                media_context=None
            )
            if response:
                logger.info(f"[RESPONSE_RECEIVED] Got response from Gemini, length={len(response)}")
                await self._process_and_send_response(update, user, response, user_context["message_context"], lang, new_mood_state)
            else:
                logger.warning(f"[RESPONSE_RECEIVED] Response is empty or None")
                await self._send_error_response(update, user.first_name, lang)
        except Exception as e:
            logger.error(f"Error in chat command: {e}", exc_info=True)
            await self._send_error_response(update, user.first_name, lang)

    async def _send_chat_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str
    ) -> None:
        try:
            if hasattr(update.message, "message_thread_id") and update.message.message_thread_id:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=action,
                    message_thread_id=update.message.message_thread_id
                )
            else:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=action
                )
        except Exception as e:
            logger.warning(f"Failed to send chat action: {e}")
    
    async def _prepare_conversation_context(
        self, 
        user, 
        query: str, 
        lang: str, 
        message_context: Dict[str, Any],
        mood_state = None,
        mood_manager = None
    ) -> Dict[str, Any]:
        """Build conversation context with persona prompt, history, relationship level, and mood."""
        user_task = asyncio.create_task(self._get_user_info(user))
        
        user_info = self.db.get_user_relationship_info(user.id)
        relationship_level = user_info.get("relationship_level", 0)
        
        logger.info(
            f"[Conversation] User {user.id}: level={relationship_level}, "
            f"affection={user_info.get('affection_points', 0)}"
        )
        
        persona_prompt = self.persona.get_chat_prompt(
            username=user.first_name,
            message=query,
            context="\n".join([str(c) for c in self.context_manager.get_context_window(user.id)]) if self.context_manager.get_context_window(user.id) else "",
            relationship_level=relationship_level,
            is_admin=user.id in ADMIN_IDS or self.db.is_admin(user.id),
            lang=lang
        )
        
        # Add mood-specific personality modifier
        if mood_state and mood_manager:
            mood_prompt = mood_manager.get_mood_prompt_modifier(
                mood_state.mood,
                mood_state.intensity,
                lang
            )
            persona_prompt += mood_prompt
            
            # Add mood-appropriate Russian expressions hint
            mood_expressions = mood_manager.get_mood_russian_expressions(mood_state.mood)
            if mood_expressions:
                expressions_hint = f"\n\nSuggested Russian expressions for current mood: {', '.join(mood_expressions[:4])}"
                persona_prompt += expressions_hint
        
        # Extract semantic topics from provided message_context
        semantic_topics = message_context.get("semantic_topics", []) if message_context else []
        
        # Analyze conversation flow if NLP available
        if FEATURES.get("emotion_detection", False) and self.nlp and message_context:
            flow_analysis = self.nlp.analyze_conversation_flow(user.id, query)
            message_context["conversation_flow"] = flow_analysis
            if flow_analysis.get("is_continuation", False):
                persona_prompt += "\n\nCONVERSATION CONTEXT: Continuation of previous topic. Maintain context continuity."
            if flow_analysis.get("user_engagement_level") == "high":
                persona_prompt += "\n\nUSER ENGAGEMENT: User is engaged. Match their energy and be expressive."
            elif flow_analysis.get("user_engagement_level") == "low":
                persona_prompt += "\n\nUSER ENGAGEMENT: User seems less engaged. Be encouraging."
        
        # Gather conversation history
        history = self.context_manager.get_context_window(user.id)
        prev_messages = self.db.get_conversation_history(user.id, limit=5)
        prev_content = "\n".join([msg.get("content", "") for msg in prev_messages if msg.get("role") == "user"])
        summaries = self.context_manager.get_conversation_summaries(user.id)
        conversation_summary = summaries[0].get('content', '') if summaries else "No previous context"
        enhanced_query = self._call_method_safely(self.memory.create_context_prompt, user.id, query, lang)
        
        conversation_context = {
            "current_topic": ", ".join(semantic_topics) if semantic_topics else "general conversation",
            "user_emotion": message_context.get("emotion", "neutral") if message_context else "neutral",
            "conversation_history_summary": conversation_summary,
            "previous_user_messages": prev_content
        }
        relationship_context = self._get_relationship_context(user, relationship_level, user.id in ADMIN_IDS, lang)
        conversation_theme = self._get_conversation_theme_context(conversation_context)
        if relationship_context:
            persona_prompt += f"\n\n{relationship_context}"
        if conversation_theme:
            persona_prompt += f"\n\n{conversation_theme}"
        await user_task
        return {
            "history": history,
            "enhanced_query": enhanced_query,
            "system_prompt": persona_prompt,
            "message_context": message_context,
            "relationship_level": relationship_level,
            "conversation_context": conversation_context
        }

    def _get_conversation_theme_context(self, conversation_context: Dict[str, Any]) -> str:
        """Build context-aware prompt from conversation topic and emotion."""
        topic = conversation_context.get("current_topic", "general conversation")
        emotion = conversation_context.get("user_emotion", "neutral")
        summary = conversation_context.get("conversation_history_summary", "No recent history")
        
        return f"""CONTEXT AWARENESS:
- Topic: {topic}
- User emotion: {emotion}
- Recent history: {summary}

Respond naturally, empathetically, and reference prior conversation when relevant."""
    
    def _call_method_safely(self, method, *args, **kwargs):
        if asyncio.iscoroutinefunction(method):
            return asyncio.create_task(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)
        
    async def _ensure_language(self, text: str, lang: str, user) -> str:
        """Ensure text is in the user's preferred language using LLM translation if needed."""
        from utils.formatters import get_translate_prompt
        import langdetect
        preferred_lang = lang or DEFAULT_LANGUAGE
        try:
            detected_lang = langdetect.detect(text)
        except Exception:
            detected_lang = preferred_lang
        if detected_lang != preferred_lang:
            translate_prompt = get_translate_prompt(text, preferred_lang)
            try:
                translated = await self.gemini.generate_response(
                    user_id=user.id,
                    username=user.first_name or "user",
                    message=translate_prompt,
                    context="",
                    relationship_level=1,
                    is_admin=False,
                    lang=preferred_lang,
                    retry_count=2,
                    is_media_analysis=False,
                    media_context=None
                )
                if translated and isinstance(translated, str):
                    return translated.strip()
            except Exception as e:
                logger.error(f"Translation step failed: {e}")
        return text

    def _split_mixed_quote_paragraphs(self, response: str) -> str:
        """
        Aggressively split paragraphs that mix narration and quoted dialogue.
        Handles dialogue tags, multiple quotes, emoji, and complex nested structures.
        
        Args:
            response: Raw response text from Gemini
            
        Returns:
            Response with quotes separated into their own paragraphs
        """
        if not response:
            return response
        
        def extract_emoji(text: str) -> tuple[str, str]:
            """Extract emoji from text using Unicode character categories."""
            import unicodedata
            
            emoji_chars = []
            clean_chars = []
            
            for char in text:
                cat = unicodedata.category(char)
                if (cat in ('So', 'Sk') or 
                    char in ('\uFE0F', '\u200D') or
                    ord(char) >= 0x1F000):
                    emoji_chars.append(char)
                else:
                    clean_chars.append(char)
            
            return ''.join(clean_chars).strip(), ''.join(emoji_chars).strip()
        
        paragraphs = response.split('\n\n')
        cleaned_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if '"' not in para:
                cleaned_paragraphs.append(para)
                continue
            
            if para.startswith('"') and para.endswith('"') and para.count('"') == 2:
                cleaned_paragraphs.append(para)
                continue
            
            parts = []
            current_pos = 0
            in_quote = False
            quote_start = -1
            
            i = 0
            while i < len(para):
                if para[i] == '"':
                    if not in_quote:
                        if current_pos < i:
                            narration = para[current_pos:i].strip().rstrip(',').strip()
                            if narration:
                                parts.append(('narration', narration))
                        quote_start = i
                        in_quote = True
                    else:
                        quote_text = para[quote_start+1:i].strip()
                        if quote_text:
                            parts.append(('quote', quote_text))
                        current_pos = i + 1
                        in_quote = False
                i += 1
            
            if current_pos < len(para):
                remaining = para[current_pos:].strip()
                if remaining:
                    remaining_no_emoji, emoji_str = extract_emoji(remaining)
                    remaining_no_emoji = remaining_no_emoji.rstrip(',').strip()
                    
                    if remaining_no_emoji:
                        parts.append(('narration', remaining_no_emoji))
                    
                    if emoji_str:
                        if parts and parts[-1][0] == 'quote':
                            last_quote = parts[-1][1]
                            parts[-1] = ('quote', f"{last_quote} {emoji_str}")
                        elif parts and parts[-1][0] == 'narration':
                            last_narration = parts[-1][1]
                            parts[-1] = ('narration', f"{last_narration} {emoji_str}")
                        else:
                            parts.append(('narration', emoji_str))
            
            for part_type, text in parts:
                if part_type == 'quote':
                    cleaned_paragraphs.append(f'"{text}"')
                else:
                    cleaned_paragraphs.append(text)
        
        return '\n\n'.join(cleaned_paragraphs)

    async def _process_and_send_response(
        self,
        update: Update,
        user,
        response: str,
        message_context: Dict[str, Any],
        lang: str,
        mood_state = None
    ) -> None:
        """Clean, format, and send response to Telegram."""
        try:
            self.db.save_message(user.id, "assistant", response)
            self.memory.save_bot_response(user.id, response)

            # Step 1: Split mixed quote-narration paragraphs
            response = self._split_mixed_quote_paragraphs(response)
            
            # Step 2: Clean and append Russian translation
            response = self._clean_and_append_russian_translation(response, lang)
            
            # Step 3: Format for Telegram
            formatted_response = format_persona_response(response, use_html=True)
            formatted_response = f"{formatted_response}\u200C"
            
            # Step 4: Sticker + GIF Injection based on mood
            await self._send_response_with_sticker_and_gif(
                update=update,
                formatted_response=formatted_response,
                user_id=user.id,
                message_text=update.message.text,
                mood_state=mood_state,
                message_context=message_context,
            )
            
        except Exception as e:
            logger.error(f"Error processing response: {e}", exc_info=True)
            await self._send_error_response(update, user.first_name, lang)

    async def _send_response_with_sticker_and_gif(
        self,
        update: Update,
        formatted_response: str,
        user_id: int,
        message_text: str,
        mood_state = None,
        message_context: Dict[str, Any] = None
    ) -> None:
        """Send response with sticker and GIF based on mood and relationship level."""
        try:
            from config.settings import STICKER_GIF_SETTINGS
            
            # Check if feature is enabled globally
            if not STICKER_GIF_SETTINGS.get("enabled", True):
                await update.message.reply_html(formatted_response)
                return
            
            # Get user preferences (check if user disabled feature)
            user_data = self.db.get_user(user_id)
            user_preferences = user_data.get("preferences", {}) if user_data else {}
            sticker_enabled_for_user = user_preferences.get("sticker_enabled", True)
            
            # Check if user disabled sticker feature
            if not sticker_enabled_for_user:
                logger.debug(f"[STICKER] User {user_id} disabled sticker feature")
                await update.message.reply_html(formatted_response)
                return
            
            # Get relationship level
            user_relationship = self.db.get_user_relationship_info(user_id)
            relationship_level = user_relationship.get("relationship_level", 0)
            
            sticker_mgr = StickerManager()
            mood = mood_state.mood if mood_state else "neutral"
            
            logger.info(
                f"[STICKER] Starting sticker logic: user={user_id}, "
                f"mood={mood}, mood_state={mood_state}, "
                f"relationship_level={relationship_level}"
            )
            
            # === CHECK STICKER UNLOCK LEVEL ===
            min_sticker_level = STICKER_GIF_SETTINGS.get("min_relationship_level_for_sticker", 3)
            allow_sticker_override = STICKER_GIF_SETTINGS.get("allow_sticker_before_relationship", False)
            
            sticker_id = None
            if relationship_level >= min_sticker_level or allow_sticker_override:
                sticker_id = sticker_mgr.get_sticker_for_mood(
                    mood=mood,
                    user_message=message_text,
                    relationship_level=relationship_level
                )
                logger.info(
                    f"[STICKER] get_sticker_for_mood returned: {sticker_id} "
                    f"(mood={mood}, message_text={message_text})"
                )
            else:
                logger.debug(
                    f"[STICKER] User {user_id} level {relationship_level} < "
                    f"required {min_sticker_level}, sticker locked"
                )
            
            # Send sticker if available and unlocked
            if sticker_id:
                try:
                    await update.message.reply_sticker(sticker=sticker_id)
                    logger.info(f"[STICKER] Sent sticker for mood '{mood}' to user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to send sticker: {e}")
                    
            # Send main text response
            await update.message.reply_html(formatted_response)
            logger.info(f"[RESPONSE] Sent text response to user {user_id}")
            
            # CHECK GIF UNLOCK LEVEL
            min_gif_level = STICKER_GIF_SETTINGS.get("min_relationship_level_for_gif", 3)
            gif_probability = STICKER_GIF_SETTINGS.get("gif_send_probability", 0.3)
            
            # Only send GIF if relationship level is high enough
            if relationship_level >= min_gif_level and random.random() < gif_probability:
                gif_url = sticker_mgr.get_gif_url_for_mood(
                    mood=mood,
                    user_message=message_text
                )
                if gif_url:
                    try:
                        await update.message.reply_animation(gif_url)
                        logger.debug(f"[GIF] Sent GIF for mood '{mood}' to user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to send GIF: {e}")
            elif relationship_level < min_gif_level:
                logger.debug(
                    f"[GIF] User {user_id} level {relationship_level} < "
                    f"required {min_gif_level}, GIF locked"
                )
                        
        except Exception as e:
            logger.error(f"Error sending response with sticker and GIF: {e}", exc_info=True)
            await update.message.reply_html(formatted_response)
    
    def _clean_and_append_russian_translation(self, response: str, lang: str = DEFAULT_LANGUAGE) -> str:
        """Extract and translate Russian expressions (both marked and unmarked)."""
        from utils.russian_translator import (
            detect_russian_expressions,
            RUSSIAN_TRANSLATIONS
        )
        
        clean_response = response.strip()
        translations_dict: Dict[str, str] = {}
        
        ru_marker_pattern = r'\[RU:\s*([^|]+)\|([^\]]+)\]'
        marked_matches = re.findall(ru_marker_pattern, clean_response, flags=re.IGNORECASE)
        
        for word, translation in marked_matches:
            word_clean = word.strip().lower()
            translations_dict[word_clean] = translation.strip()
        
        clean_response = re.sub(
            ru_marker_pattern,
            lambda m: m.group(1).strip(),
            clean_response,
            flags=re.IGNORECASE
        )
        
        detected_russian = detect_russian_expressions(clean_response)
        for word in detected_russian:
            word_lower = word.lower()
            if word_lower not in translations_dict and word_lower in RUSSIAN_TRANSLATIONS:
                translations_dict[word_lower] = RUSSIAN_TRANSLATIONS[word_lower]
        
        clean_response = re.sub(
            r'(?i)(💬\s*)?(?:Terjemahan|Translation)\s+Russian.*',
            '',
            clean_response
        )
        clean_response = re.sub(r'\n{3,}', '\n\n', clean_response.strip())
        
        if translations_dict:
            translation_lines = []
            for word_key, translation in sorted(translations_dict.items()):
                translation_lines.append(f"{word_key} = {translation}")
            
            if translation_lines:
                header = "💬 Terjemahan Russian:" if lang == "id" else "💬 Russian Translation:"
                translation_block = header + "\n" + "\n".join(translation_lines)
                clean_response = f"{clean_response}\n\n{translation_block}"
        
        return clean_response

    async def _get_user_info(self, user) -> Dict[str, Any]:
        """Get user admin status and relationship level."""
        is_admin = user.id in ADMIN_IDS or (self.db and self.db.is_admin(user.id))
        if self.db:
            self._create_or_update_user(user)
            user_info = self.db.get_user_relationship_info(user.id)
            relationship_level = user_info.get("relationship_level", 0)
        else:
            relationship_level = 0
        return {'is_admin': is_admin, 'relationship_level': relationship_level}

    def _get_relationship_context(self, user: Any, relationship_level: int, is_admin: bool, lang: str = DEFAULT_LANGUAGE) -> str:
        """Get relationship context based on level."""
        first_name = getattr(user, 'first_name', None) or "user"
        return self.persona.get_relationship_context(
            username=first_name,
            relationship_level=relationship_level,
            is_admin=is_admin,
            lang=lang
        )

    def _calculate_affection_delta(self, user_id: int, message_context: Dict[str, Any]) -> int:
        """Calculate affection delta based on user's emotion, intent, and relationship signals."""
        if not message_context:
            return AFFECTION_POINTS.get("conversation", 1)

        affection_delta = 0

        # User's emotions towards Alya
        emotion = message_context.get("emotion", "")
        if emotion in ["happy", "excited", "grateful", "joy", "love", "admiration", "amusement", "optimism", "relief", "pride", "caring", "approval"]:
            affection_delta += AFFECTION_POINTS.get("positive_emotion", 2)
            logger.debug(f"User {user_id} shows positive emotion '{emotion}': +{AFFECTION_POINTS.get('positive_emotion', 2)}")
        elif emotion in ["sad", "worried", "disappointed"]:
            affection_delta += AFFECTION_POINTS.get("mild_positive_emotion", 1)
            logger.debug(f"User {user_id} shows vulnerable emotion '{emotion}': +{AFFECTION_POINTS.get('mild_positive_emotion', 1)}")
        elif emotion in ["angry", "frustrated", "annoyed"] and not message_context.get("directed_at_alya", False):
            affection_delta += AFFECTION_POINTS.get("mild_positive_emotion", 1)
        elif emotion in ["angry", "frustrated", "annoyed"] and message_context.get("directed_at_alya", True):
            affection_delta += AFFECTION_POINTS.get("anger", -3)
            logger.debug(f"User {user_id} is angry at Alya: {AFFECTION_POINTS.get('anger', -3)}")

        # User's intentions towards Alya
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
        elif intent in ["insult", "abuse"]:
            affection_delta += AFFECTION_POINTS.get("insult", -10)
        elif intent in ["toxic", "toxic_behavior", "bullying"]:
            affection_delta += AFFECTION_POINTS.get("toxic_behavior", -10)
        elif intent == "rudeness":
            affection_delta += AFFECTION_POINTS.get("rudeness", -10)
        elif intent == "ignoring":
            affection_delta += AFFECTION_POINTS.get("ignoring", -5)
        elif intent == "inappropriate":
            affection_delta += AFFECTION_POINTS.get("inappropriate", -20)
        elif intent in ["command", "departure"]:
            affection_delta += AFFECTION_POINTS.get("command", -1)

        # Relationship signals
        relationship_signals = message_context.get("relationship_signals", {})
        signal_delta = 0
        signal_delta += relationship_signals.get("friendliness", 0) * AFFECTION_POINTS.get("friendliness", 6)
        signal_delta += relationship_signals.get("romantic_interest", 0) * AFFECTION_POINTS.get("romantic_interest", 10)
        signal_delta += relationship_signals.get("conflict", 0) * AFFECTION_POINTS.get("conflict", -3)
        
        if signal_delta != 0:
            logger.debug(f"[AFFECTION] User {user_id} signal bonuses: friendliness={relationship_signals.get('friendliness', 0) * 6:.1f}, romantic={relationship_signals.get('romantic_interest', 0) * 10:.1f}, conflict={relationship_signals.get('conflict', 0) * -3:.1f}")
        
        affection_delta += signal_delta
        min_penalty = AFFECTION_POINTS.get("min_penalty", -4)
        if affection_delta < 0:
            affection_delta = max(affection_delta, min_penalty)

        if affection_delta == 0:
            affection_delta = AFFECTION_POINTS.get("conversation", 1)

        if abs(affection_delta) >= 1:
            affection_delta = round(affection_delta)
            logger.info(f"[AFFECTION] User {user_id}: {affection_delta:+d} | emotion={emotion}, intent={intent}")
            return affection_delta
        else:
            logger.debug(f"[AFFECTION] User {user_id}: no change (delta={affection_delta:.1f})")
            return 0
        