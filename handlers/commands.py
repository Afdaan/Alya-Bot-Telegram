import logging
import os
import tempfile
import time

from telegram import Update, BotCommand
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler

from config.settings import SAUCENAO_PREFIX, COMMAND_PREFIX
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
        # Assuming gemini_client and persona_manager are accessible, e.g., from application context
        # This might need adjustment based on your actual application structure
        gemini_client = getattr(application, 'gemini_client', None)
        persona_manager = getattr(application, 'persona_manager', None)
        
        if not gemini_client or not persona_manager:
            # This is a fallback. Ideally, these clients should be passed during initialization.
            # For now, let's log a warning.
            logger.warning("GeminiClient or PersonaManager not found on application object. RoastHandler might not work.")
            # You might want to raise an error or handle this more gracefully
            # For the purpose of this refactor, we'll proceed but some features might fail.
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
        # Register roast handlers if available
        if self.roast_handler:
            for handler in self.roast_handler.get_handlers():
                self.application.add_handler(handler)
            logger.info("Registered roast handlers successfully")

        # SauceNAO handlers
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{SAUCENAO_PREFIX}"),
                self.handle_sauce_command
            )
        )
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO & filters.CaptionRegex(f".*{SAUCENAO_PREFIX}.*"),
                self.handle_sauce_command  # Re-route to the main handler
            )
        )
        
        # Other command handlers
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
                filters.TEXT & filters.ChatType.PRIVATE & filters.Regex(f"^{analyze_prefix}"),
                self.handle_analyze_text
            )
        )
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.ChatType.GROUPS & filters.Regex(f"^{analyze_prefix}"),
                self.handle_analyze_text
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
            photo_file = await photo_to_process.get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                await photo_file.download_to_drive(temp_file.name)
                temp_path = temp_file.name
            
            search_results = await self.saucenao_searcher.search(temp_path)
            
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
            logger.error(f"General error in sauce command for user {user.id}: {e}")
            await status_message.edit_text(sauce_texts["error_unknown"])
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    async def handle_analyze_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._send_chat_action(update, context, ChatAction.TYPING)
        message = update.effective_message
        caption = message.caption or message.text or ""
        caption = caption.replace("!ask", "", 1).strip()
        context.args = caption.split() if caption else []
        logger.info(f"Handling !ask media analysis from {update.effective_user.id} with args: {context.args}")
        await MediaAnalyzer.handle_analysis_command(update, context)

    async def handle_analyze_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._send_chat_action(update, context, ChatAction.TYPING)
        message = update.effective_message
        text = message.text.replace("!ask", "", 1).strip()
        if not text and update.effective_chat.type in ["group", "supergroup"]:
            lang = get_user_lang(update.effective_user.id)
            response = analyze_response(lang=lang)
            await message.reply_html(response, reply_to_message_id=message.message_id)
            return
        context.args = text.split() if text else []
        logger.info(f"Handling !ask text analysis from {update.effective_user.id} with query: {text[:50]}...")
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

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /ping command to check bot latency."""
    start_time = time.time()
    lang = get_user_lang(update.effective_user.id)
    
    # The initial message is simple and language-agnostic.
    # The final response will be in the user's language.
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
    """Handles the /reset command to clear user's conversation history."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not db_manager:
        logger.error("Database manager not found for reset command.")
        await update.message.reply_html(get_system_error_response(lang))
        return

    if context.args and context.args[0].lower() == 'confirm':
        try:
            success = db_manager.reset_user_conversation(user_id)
            response = get_reset_response(lang=lang, success=success)
            if success:
                logger.info(f"Successfully reset conversation history for user {user_id}")
            else:
                logger.warning(f"Reset conversation history failed for user {user_id}, db returned false")
        except Exception as e:
            logger.error(f"Error resetting conversation history for user {user_id}: {e}")
            response = get_reset_response(lang=lang, success=False)
        
        await update.message.reply_html(response)
    else:
        response = get_reset_confirmation_response(lang=lang)
        await update.message.reply_html(response)


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
    """Handles the /lang command to change user's language preference."""
    user_id = update.effective_user.id
    
    if not db_manager:
        logger.error("Database manager not found for lang command.")
        # Default to English for this specific error message if we can't even get lang
        await update.message.reply_html(get_system_error_response('en'))
        return
    
    if context.args:
        new_lang = context.args[0].lower()
        if new_lang in ['en', 'id']:
            try:
                db_manager.update_user_settings(user_id, {'language': new_lang})
                # The response function now only needs the new language
                response = get_lang_response(lang=new_lang, new_lang=new_lang)
                logger.info(f"User {user_id} changed language to {new_lang}")
                await set_bot_commands(context.application, lang=new_lang)
            except Exception as e:
                current_lang = get_user_lang(user_id)
                logger.error(f"Failed to update language for user {user_id}: {e}")
                response = get_system_error_response(current_lang)
        else:
            # If the arg is invalid, get current lang to show usage in the correct language
            current_lang = get_user_lang(user_id)
            response = get_lang_response(lang=current_lang)
    else:
        # If no args, get current lang to show usage
        current_lang = get_user_lang(user_id)
        response = get_lang_response(lang=current_lang)
        
    await update.message.reply_html(response)


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
    # This function can be expanded to set commands in different languages
    # For now, we'll set them in English as a default
    
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
        # Set commands for English users
        await application.bot.set_my_commands(
            commands=commands_en,
            language_code="en"
        )
        # Set commands for Indonesian users
        await application.bot.set_my_commands(
            commands=commands_id,
            language_code="id"
        )
        # Set default commands
        await application.bot.set_my_commands(commands=commands_id)
        
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

def register_commands(application) -> None:
    """Registers all command handlers for the bot."""
    CommandsHandler(application)
    logger.info("All command handlers registered successfully")