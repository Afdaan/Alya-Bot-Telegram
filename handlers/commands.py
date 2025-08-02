import logging
import os
import tempfile
import time
from typing import Any, Dict

from telegram import Update, BotCommand
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler

from config.settings import SAUCENAO_PREFIX
from utils.saucenao import SauceNAOSearcher, SauceNAOError
from utils.search_engine import search_web
from utils.analyze import MediaAnalyzer
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

# Helper function to get user's language preference
def get_user_lang(user_id: int, db_manager: Any) -> str:
    """Gets user language preference from the database."""
    if db_manager:
        user_settings = db_manager.get_user_settings(user_id)
        if user_settings and user_settings.get('language'):
            return user_settings['language']
    return 'id'  # Default to Indonesian

# Centralized response getter for simple text responses
def get_response(command: str, user_id: int, db_manager: Any, **kwargs) -> str:
    """
    Gets a response in the user's preferred language.
    This is for simple, non-complex responses.
    """
    lang = get_user_lang(user_id, db_manager)
    
    response_functions = {
        "start": get_start_response,
        "help": get_help_response,
        "ping": get_ping_response,
        "stats": get_stats_response,
        "lang": get_lang_response,
        "analyze": analyze_response,
        "reset": get_reset_response,
        "reset_confirmation": get_reset_confirmation_response,
        "search_usage": search_usage_response,
        "search_error": search_error_response,
        "search_results": format_search_results,
    }

    response_function = response_functions.get(command)
    
    if response_function:
        # Pass lang to all response functions that accept it
        func_args = response_function.__code__.co_varnames
        if 'lang' in func_args:
            kwargs['lang'] = lang
        
        # Remove args not needed by the function
        final_kwargs = {k: v for k, v in kwargs.items() if k in func_args}
        
        return response_function(**final_kwargs)
    
    logger.warning(f"No response function found for command: {command}")
    return get_system_error_response(lang)


class CommandsHandler:
    def __init__(self, application) -> None:
        self.application = application
        self.saucenao_searcher = SauceNAOSearcher()
        self._register_handlers()
        logger.info("Command handlers initialized and registered")

    def _register_handlers(self) -> None:
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
        db_manager = context.bot_data.get("db_manager")
        lang = get_user_lang(user.id, db_manager)
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
            db_manager = context.bot_data.get("db_manager")
            response = get_response("analyze", update.effective_user.id, db_manager)
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
    start_time = time.time()
    db_manager = context.bot_data.get("db_manager")
    lang = get_user_lang(update.effective_user.id, db_manager)
    
    ping_message = "Pinging..." if lang == 'id' else "Pinging..."
    message = await update.message.reply_text(ping_message)
    
    end_time = time.time()
    latency = (end_time - start_time) * 1000
    
    response = get_response("ping", update.effective_user.id, db_manager, latency=latency)
    await message.edit_text(response, parse_mode="HTML")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_manager = context.bot_data.get("db_manager")
    response = get_response("start", user.id, db_manager, username=user.first_name)
    await update.message.reply_text(response, parse_mode="HTML")
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /start: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_manager = context.bot_data.get("db_manager")
    response = get_response("help", user.id, db_manager)
    await update.message.reply_text(response, parse_mode="HTML")
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /help: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /reset command to clear user's conversation history."""
    user_id = update.effective_user.id
    db_manager = context.bot_data.get("db_manager")
    
    if not db_manager:
        lang = get_user_lang(user_id, None)
        logger.error("Database manager not found in bot_data for reset command")
        await update.message.reply_html(get_system_error_response(lang))
        return

    if context.args and context.args[0].lower() == 'confirm':
        try:
            success = db_manager.reset_user_conversation(user_id)
            response_key = "reset"
            kwargs = {'success': success}
            if success:
                logger.info(f"Successfully reset conversation history for user {user_id}")
            else:
                logger.warning(f"Reset conversation history failed for user {user_id}, db returned false")
        except Exception as e:
            logger.error(f"Error resetting conversation history for user {user_id}: {e}")
            response_key = "reset"
            kwargs = {'success': False}
        
        response = get_response(response_key, user_id, db_manager, **kwargs)
        await update.message.reply_html(response)
    else:
        response = get_response("reset_confirmation", user_id, db_manager)
        await update.message.reply_html(response)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_manager = context.bot_data.get("db_manager")
    user_id = update.effective_user.id
    response = get_response("stats", user_id, db_manager, user_id=user_id)
    await update.message.reply_html(response)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /search command with bilingual support."""
    user = update.effective_user
    db_manager = context.bot_data.get("db_manager")

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
        usage_text = get_response("search_usage", user.id, db_manager)
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
        
        response_text = get_response(
            "search_results",
            user.id,
            db_manager,
            query=query,
            results=search_results,
            search_type=search_type,
            show_username_tip=show_username_tip
        )
        
        await update.message.reply_html(response_text, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}")
        error_text = get_response("search_error", user.id, db_manager, error_message=str(e))
        await update.message.reply_html(error_text)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /lang command to change user language."""
    user_id = update.effective_user.id
    db_manager = context.bot_data.get("db_manager")
    
    if not db_manager:
        lang = get_user_lang(user_id, None)
        logger.error("Database manager not found in bot_data")
        await update.message.reply_text(get_system_error_response(lang))
        return

    if not context.args:
        response = get_response("lang", user_id, db_manager, usage=True)
        await update.message.reply_html(response)
        return

    new_lang = context.args[0].lower()
    if new_lang not in ['id', 'en']:
        response = get_response("lang", user_id, db_manager, usage=True)
        await update.message.reply_html(response)
        return

    try:
        db_manager.update_user_settings(user_id, {'language': new_lang})
        # We need to call get_lang_response directly here since get_response uses the old lang
        response = get_lang_response(lang=new_lang, new_lang=new_lang)
        await update.message.reply_html(response)
        logger.info(f"User {user_id} changed language to {new_lang}")
        # Update commands for the new language
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to update language for user {user_id}: {e}")
        lang = get_user_lang(user_id, db_manager)
        await update.message.reply_text(get_system_error_response(lang))

async def set_bot_commands(application) -> None:
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
    logger.info("Command handlers registered successfully")