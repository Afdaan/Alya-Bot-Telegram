import logging
import os
import tempfile
import time

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler, CallbackQueryHandler

from config.settings import SAUCENAO_PREFIX, COMMAND_PREFIX, DEFAULT_LANGUAGE
from database.database_manager import db_manager, get_user_lang
from utils.saucenao import SauceNAOSearcher, SauceNAOError
from utils.search_engine import search_web
from utils.analyze import MediaAnalyzer
from utils.roast import RoastHandler
from handlers.response.start import get_start_response
from handlers.response.help import get_help_response
from handlers.response.ping import get_ping_response
from handlers.response.stats import get_stats_response
from handlers.response.lang import get_lang_response
from handlers.response.system import get_system_error_response
from handlers.response.analyze import analyze_response
from handlers.response.reset import get_reset_response, get_reset_confirmation_response
from handlers.response.sauce import format_sauce_results, get_texts as get_sauce_texts
from handlers.response.search import (
    search_usage_response,
    search_error_response,
    format_search_results,
)

logger = logging.getLogger(__name__)

class CommandsHandler:
    def __init__(self, application) -> None:
        self.application = application
        self.saucenao_searcher = SauceNAOSearcher()
        gemini_client = getattr(application, 'gemini_client', None)
        persona_manager = getattr(application, 'persona_manager', None)
        
        if not gemini_client or not persona_manager:
            logger.warning("GeminiClient or PersonaManager not found on application object. RoastHandler might not work.")
            self.roast_handler = None
        else:
            self.roast_handler = RoastHandler(
                gemini_client=gemini_client,
                persona_manager=persona_manager,
                db_manager=db_manager
            )

        self._register_handlers()
        logger.info("Command handlers initialized and registered")

    def _register_handlers(self) -> None:
        if self.roast_handler:
            for handler in self.roast_handler.get_handlers():
                self.application.add_handler(handler)
            logger.info("Registered roast handlers successfully")

        # Reset callback handler for buttons
        self.application.add_handler(
            CallbackQueryHandler(self.handle_reset_callback, pattern="^reset_")
        )

        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{SAUCENAO_PREFIX}"),
                self.handle_sauce_command
            )
        )
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO & filters.CaptionRegex(f".*{SAUCENAO_PREFIX}.*"),
                self.handle_sauce_command
            )
        )
        
        analyze_prefix = "!ask"
        
        self.application.add_handler(
            MessageHandler(
                (filters.PHOTO | filters.Document.ALL) & 
                filters.CaptionRegex(f".*{analyze_prefix}.*"),
                self.handle_analyze_media
            )
        )
        
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{analyze_prefix}"),
                self.handle_analyze_command
            )
        )
        self.application.add_handler(CommandHandler("ping", ping_command))
        self.application.add_handler(CommandHandler("stats", stats_command))
        self.application.add_handler(CommandHandler("reset", reset_command))
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("lang", lang_command))
        self.application.add_handler(CommandHandler("search", search_command))
        self.application.add_handler(CommandHandler("search_profile", search_profile_command))
        self.application.add_handler(CommandHandler("search_news", search_news_command))
        self.application.add_handler(CommandHandler("search_image", search_image_command))
        self.application.add_handler(CommandHandler("sticker_on", sticker_on_command))
        self.application.add_handler(CommandHandler("sticker_off", sticker_off_command))
        logger.info("Registered sauce and utility commands successfully")

    async def handle_sauce_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles both replied-to images and captioned images for SauceNAO."""
        message = update.effective_message
        user = update.effective_user
        lang = get_user_lang(user.id)
        sauce_texts = get_sauce_texts(lang)

        photo_to_process = None
        if message.reply_to_message and message.reply_to_message.photo:
            photo_to_process = message.reply_to_message.photo[-1]
        elif message.photo:
            photo_to_process = message.photo[-1]

        if not photo_to_process:
            await message.reply_html(sauce_texts["usage"])
            return

        status_message = await message.reply_text(sauce_texts["searching"])
        temp_path = None
        try:
            logger.info(f"Processing sauce request from user {user.id}")
            photo_file = await photo_to_process.get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                await photo_file.download_to_drive(temp_file.name)
                temp_path = temp_file.name
            
            logger.info(f"Image downloaded to {temp_path}, sending to SauceNAO")
            search_results = await self.saucenao_searcher.search(temp_path)
            logger.info(f"SauceNAO returned {len(search_results.get('results', []))} processed results")
            
            response_text, keyboard = format_sauce_results(search_results, lang)
            
            await status_message.edit_text(
                response_text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

        except SauceNAOError as e:
            logger.error(f"SauceNAO specific error for user {user.id}: {e}")
            error_key = "error_rate_limit" if "rate limit" in str(e).lower() else "error_api"
            await status_message.edit_text(sauce_texts[error_key])
        except Exception as e:
            logger.error(f"General error in sauce command for user {user.id}: {e}", exc_info=True)
            await status_message.edit_text(sauce_texts["error_unknown"])
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    async def handle_analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Unified handler for !ask commands. Routes based on actual user reply intent."""
        await self._send_chat_action(update, context, ChatAction.TYPING)
        message = update.effective_message
        
        is_actual_reply = False
        
        if message.reply_to_message is not None:
            replied_msg = message.reply_to_message
            
            has_media = replied_msg.photo or replied_msg.document or replied_msg.video
            has_meaningful_text = replied_msg.text and len(replied_msg.text.strip()) > 0

            is_same_message = replied_msg.message_id == message.message_id
            
            thread_id = getattr(message, 'message_thread_id', None)
            is_general_topic = thread_id == 1 or thread_id is None
            
            if not is_same_message and (has_media or has_meaningful_text):
                is_actual_reply = True
        
        thread_id = getattr(message, 'message_thread_id', None)
        
        if is_actual_reply:
            logger.info(f"[!ask REPLY] User {update.effective_user.id} | Chat: {update.effective_chat.type} | Thread: {thread_id} | Replied to: {message.reply_to_message.message_id}")
            await MediaAnalyzer.handle_analysis_command(update, context)
        else:
            logger.info(f"[!ask TEXT] User {update.effective_user.id} | Chat: {update.effective_chat.type} | Thread: {thread_id}")
            logger.debug(f"[!ask TEXT] Raw message text: {repr(message.text)}")
            
            original_text = message.text or ""
            if original_text.startswith("!ask"):
                text = original_text[4:].strip()
            else:
                text = original_text.replace("!ask", "", 1).replace("!ASK", "", 1).strip()
            
            logger.debug(f"[!ask TEXT] Text after removing prefix: {repr(text)} (length: {len(text)})")
            
            if not text or len(text) == 0:
                logger.info(f"[!ask TEXT] Empty query, showing usage")
                lang = get_user_lang(update.effective_user.id)
                from handlers.response.analyze import analyze_response
                response = analyze_response(lang=lang)
                await message.reply_html(response)
                return
            
            logger.info(f"[!ask TEXT] Processing query: {text[:50]}...")

            context.user_data['extracted_query'] = text
            
            await MediaAnalyzer.handle_analysis_command(update, context)

    async def handle_analyze_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle !ask when replying to a message (DEPRECATED - use handle_analyze_command)."""
        await self._send_chat_action(update, context, ChatAction.TYPING)
        message = update.effective_message
        has_reply = message.reply_to_message is not None
        logger.info(f"[!ask REPLY] User {update.effective_user.id} | Has reply_to_message: {has_reply} | Chat: {update.effective_chat.type}")
        await MediaAnalyzer.handle_analysis_command(update, context)

    async def handle_analyze_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._send_chat_action(update, context, ChatAction.TYPING)
        message = update.effective_message
        caption = message.caption or message.text or ""
        caption = caption.replace("!ask", "", 1).strip()
        context.args = caption.split() if caption else []
        logger.info(f"Handling !ask media analysis from {update.effective_user.id} with args: {context.args}")
        await MediaAnalyzer.handle_analysis_command(update, context)

    async def handle_analyze_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle !ask with text query (DEPRECATED - use handle_analyze_command)."""
        await self._send_chat_action(update, context, ChatAction.TYPING)
        message = update.effective_message
        
        logger.info(f"[!ask TEXT] User {update.effective_user.id} | Chat: {update.effective_chat.type} | Has reply: {message.reply_to_message is not None}")
        logger.debug(f"[!ask TEXT] Raw message text: {repr(message.text)}")
        
        original_text = message.text or ""
        
        if original_text.startswith("!ask"):
            text = original_text[4:].strip()
        else:
            text = original_text.replace("!ask", "", 1).replace("!ASK", "", 1).strip()
        
        logger.debug(f"[!ask TEXT] Text after removing prefix: {repr(text)} (length: {len(text)})")
        
        if not text or len(text) == 0:
            logger.info(f"[!ask TEXT] Empty query from user {update.effective_user.id}, showing usage")
            lang = get_user_lang(update.effective_user.id)
            from handlers.response.analyze import analyze_response
            response = analyze_response(lang=lang)
            await message.reply_html(response)
            return
            
        logger.info(f"[!ask TEXT] Processing query from {update.effective_user.id}: {text[:50]}...")
        await MediaAnalyzer.handle_analysis_command(update, context)

    async def _send_chat_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str
    ) -> None:
        chat = update.effective_chat
        try:
            if hasattr(update.message, "message_thread_id") and update.message.message_thread_id:
                await context.bot.send_chat_action(
                    chat_id=chat.id,
                    action=action,
                    message_thread_id=update.message.message_thread_id
                )
            else:
                await context.bot.send_chat_action(
                    chat_id=chat.id,
                    action=action
                )
        except Exception as e:
            logger.warning(f"Failed to send chat action: {e}")

    async def handle_reset_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reset confirmation buttons."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        lang = get_user_lang(user_id)
        
        if not db_manager:
            logger.error("Database manager not found for reset callback.")
            await query.edit_message_text(get_system_error_response(lang), parse_mode="HTML")
            return

        if query.data == "reset_yes":
            try:
                success = db_manager.reset_user_conversation(user_id)
                response = get_reset_response(lang=lang, success=success)
                if success:
                    logger.info(f"Successfully reset conversation history for user {user_id}")
                else:
                    logger.warning(f"Reset conversation history failed for user {user_id}")
            except Exception as e:
                logger.error(f"Error resetting conversation history for user {user_id}: {e}")
                response = get_reset_response(lang=lang, success=False)
            
            await query.edit_message_text(response, parse_mode="HTML")
            
        elif query.data == "reset_no":
            from handlers.response.reset import get_reset_cancel_response
            cancel_response = get_reset_cancel_response(lang=lang)
            await query.edit_message_text(cancel_response, parse_mode="HTML")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /ping command to check bot latency."""
    start_time = time.time()
    lang = get_user_lang(update.effective_user.id)
    
    message = await update.message.reply_text("Pinging...")
    
    end_time = time.time()
    latency = (end_time - start_time) * 1000
    
    response = get_ping_response(lang=lang, latency=latency)
    await message.edit_text(response, parse_mode="HTML")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = update.effective_user
    lang = get_user_lang(user.id)
    response = get_start_response(lang=lang, username=user.first_name)
    await update.message.reply_text(response, parse_mode="HTML")
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /start: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command."""
    user = update.effective_user
    lang = get_user_lang(user.id)
    
    response = get_help_response(lang=lang, username=user.first_name or "user")
    await update.message.reply_text(response, parse_mode="HTML")
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /help: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /reset command with Yes/No confirmation buttons."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not db_manager:
        logger.error("Database manager not found for reset command.")
        await update.message.reply_html(get_system_error_response(lang))
        return

    # Create inline keyboard for Yes/No confirmation
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Ya, reset!" if lang == "id" else "✅ Yes, reset!", 
                callback_data="reset_yes"
            ),
            InlineKeyboardButton(
                "❌ Batal" if lang == "id" else "❌ Cancel", 
                callback_data="reset_no"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get confirmation message
    response = get_reset_confirmation_response(lang=lang)
    await update.message.reply_html(response, reply_markup=reply_markup)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /stats command to show bot statistics."""
    lang = get_user_lang(update.effective_user.id)
    try:
        stats = db_manager.get_stats()
        response = get_stats_response(lang=lang, db_manager=db_manager, user_id=update.effective_user.id, stats=stats)
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        response = get_system_error_response(lang)
    await update.message.reply_html(response)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /lang command to change user language preference."""
    
    user_id = update.effective_user.id
    current_lang = get_user_lang(user_id)
    
    if not db_manager:
        logger.error("Database manager not found for lang_command")
        await update.message.reply_html(get_system_error_response(current_lang))
        return
    
    if not context.args or len(context.args) == 0:
        response = get_lang_response(lang=current_lang)
        await update.message.reply_html(response)
        return
    
    new_lang = context.args[0].lower().strip()
    
    if new_lang not in ['en', 'id']:
        response = get_lang_response(lang=current_lang)
        await update.message.reply_html(response)
        return
    
    try:
        db_manager.update_user_settings(user_id, {'language': new_lang})
        logger.info(f"User {user_id} changed language from {current_lang} to {new_lang}")
        response = get_lang_response(lang=new_lang, new_lang=new_lang)
        await update.message.reply_html(response)
    except Exception as e:
        logger.error(f"Failed to update language for user {user_id}: {e}", exc_info=True)
        await update.message.reply_html(get_system_error_response(current_lang))


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /search command with bilingual support."""
    user = update.effective_user
    lang = get_user_lang(user.id)

    args = context.args if context.args else []
    search_type = None
    if args and args[0].startswith('-'):
        flag = args[0].lower()
        if flag in ['-p', '-profile']:
            search_type = 'profile'
            args = args[1:]
        elif flag in ['-n', '-news']:
            search_type = 'news'
            args = args[1:]
        elif flag in ['-i', '-image']:
            search_type = 'image'
            args = args[1:]
    
    query = " ".join(args) if args else ""
    if not query:
        usage_text = search_usage_response(lang=lang)
        await update.message.reply_html(usage_text)
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        search_results = await search_web(
            query=query,
            max_results=8,
            search_type=search_type,
            safe_search="off"
        )
        
        show_username_tip = search_type == 'profile' and (not search_results or len(search_results) < 2)
        
        response_text = format_search_results(
            lang=lang,
            query=query,
            results=search_results,
            search_type=search_type,
            show_username_tip=show_username_tip
        )
        
        await update.message.reply_html(response_text, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}")
        error_text = search_error_response(lang=lang, error_message=str(e))
        await update.message.reply_html(error_text)

async def set_bot_commands(application, lang='en') -> None:
    """Sets the bot commands based on user language."""
    commands_en = [
        BotCommand("start", "✨ Start the bot"),
        BotCommand("help", "❓ Show help message"),
        BotCommand("ping", "🏓 Check bot latency"),
        BotCommand("stats", "📊 Show bot statistics"),
        BotCommand("lang", "🌐 Change language (en/id)"),
        BotCommand("reset", "🔄 Reset your conversation history"),
        BotCommand("search", "🔍 Search the web"),
    ]
    
    commands_id = [
        BotCommand("start", "✨ Memulai bot"),
        BotCommand("help", "❓ Tampilkan pesan bantuan"),
        BotCommand("ping", "🏓 Cek latensi bot"),
        BotCommand("stats", "📊 Tampilkan statistik bot"),
        BotCommand("lang", "🌐 Ganti bahasa (en/id)"),
        BotCommand("reset", "🔄 Atur ulang riwayat percakapanmu"),
        BotCommand("search", "🔍 Cari di web"),
    ]

    try:
        await application.bot.set_my_commands(commands=commands_en, language_code="en")
        await application.bot.set_my_commands(commands=commands_id, language_code="id")
        default_commands = commands_en if DEFAULT_LANGUAGE == "en" else commands_id
        await application.bot.set_my_commands(commands=default_commands)
        logger.info("Successfully set bot commands for all languages.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

async def search_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args if context.args else []
    context.args = ["-p"] + args
    await search_command(update, context)

async def search_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args if context.args else []
    context.args = ["-n"] + args
    await search_command(update, context)

async def search_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args if context.args else []
    context.args = ["-i"] + args
    await search_command(update, context)

async def sticker_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable sticker and GIF feature for current user."""
    user = update.effective_user
    lang = get_user_lang(user.id)
    
    try:
        # Get user preferences
        user_data = db_manager.get_user(user.id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please /start first.")
            return
        
        # Update preferences
        preferences = user_data.get("preferences", {})
        preferences["sticker_enabled"] = True
        db_manager.update_user_preferences(user.id, preferences)
        
        # Response based on language
        if lang == "id":
            response = "✨ Fitur sticker dan GIF Alya sudah diaktifkan! Nikmati ekspresi Alya yang lebih hidup~ 💫"
        else:
            response = "✨ Alya's sticker and GIF feature is now enabled! Enjoy her lively expressions~ 💫"
        
        await update.message.reply_text(response)
        logger.info(f"[STICKER] User {user.id} enabled sticker feature")
        
    except Exception as e:
        logger.error(f"Error in sticker_on_command: {e}")
        error_response = "😅 Ada error saat mengubah preferensi..." if lang == "id" else "😅 Error changing preferences..."
        await update.message.reply_text(error_response)

async def sticker_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable sticker and GIF feature for current user."""
    user = update.effective_user
    lang = get_user_lang(user.id)
    
    try:
        # Get user preferences
        user_data = db_manager.get_user(user.id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please /start first.")
            return
        
        # Update preferences
        preferences = user_data.get("preferences", {})
        preferences["sticker_enabled"] = False
        db_manager.update_user_preferences(user.id, preferences)
        
        # Response based on language
        if lang == "id":
            response = "🤐 Fitur sticker dan GIF Alya sudah dinonaktifkan. Kamu hanya akan menerima pesan teks saja."
        else:
            response = "🤐 Alya's sticker and GIF feature is now disabled. You'll only receive text messages."
        
        await update.message.reply_text(response)
        logger.info(f"[STICKER] User {user.id} disabled sticker feature")
        
    except Exception as e:
        logger.error(f"Error in sticker_off_command: {e}")
        error_response = "😅 Ada error saat mengubah preferensi..." if lang == "id" else "😅 Error changing preferences..."
        await update.message.reply_text(error_response)

def register_commands(application) -> None:
    """Registers all command handlers for the bot."""
    CommandsHandler(application)
    logger.info("All command handlers registered successfully")