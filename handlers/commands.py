import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

from telegram import Update, Message, BotCommand, BotCommandScope
from telegram.constants import ChatAction, BotCommandScopeType
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from config.settings import SAUCENAO_PREFIX
from utils.saucenao import search_with_saucenao
from utils.formatters import format_response
from utils.search_engine import search_web
from utils.analyze import MediaAnalyzer
from handlers.response.help import help_response
from handlers.response.start import start_response
from handlers.response.ping import ping_response
from handlers.response.stats import stats_response

logger = logging.getLogger(__name__)

class CommandsHandler:
    def __init__(self, application) -> None:
        self.application = application
        self._register_handlers()
        logger.info("Command handlers initialized and registered")

    def _register_handlers(self) -> None:
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & filters.Regex(f"^{SAUCENAO_PREFIX}"),
                self.handle_sauce_command
            )
        )
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO & filters.CaptionRegex(f".*{SAUCENAO_PREFIX}.*"),
                self.handle_image_auto_sauce
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
        logger.info("Registered sauce and utility commands successfully")

    async def handle_sauce_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message.reply_to_message and message.reply_to_message.photo:
            photo = message.reply_to_message.photo[-1]
            status_message = await message.reply_text("🔍 Alya sedang menganalisis gambar...")
            try:
                photo_file = await photo.get_file()
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    await photo_file.download_to_drive(temp_file.name)
                    temp_path = temp_file.name
                await search_with_saucenao(status_message, temp_path)
            except Exception as e:
                logger.error(f"Sauce command error: {e}")
                await status_message.edit_text(
                    "❌ Terjadi kesalahan saat mencari sumber gambar. Coba lagi nanti ya~",
                    parse_mode='HTML'
                )
            finally:
                try:
                    if 'temp_path' in locals():
                        os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
        else:
            await message.reply_text(
                "❓ <b>Cara pakai:</b>\n\n"
                "Reply ke gambar dengan <code>!sauce</code> untuk mencari sumber gambar anime/manga.\n\n"
                "<i>~Alya akan membantu mencari sumber gambar. Bukan karena peduli sama kamu atau apa~</i> 😳",
                parse_mode='HTML'
            )

    async def handle_image_auto_sauce(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        message_text = message.caption or ""
        if SAUCENAO_PREFIX.lower() in message_text.lower():
            photo = message.photo[-1]
            status_message = await message.reply_text("🔍 Mencari sumber gambar...")
            try:
                photo_file = await photo.get_file()
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    await photo_file.download_to_drive(temp_file.name)
                    temp_path = temp_file.name
                await search_with_saucenao(status_message, temp_path)
            except Exception as e:
                logger.error(f"Auto sauce error: {e}")
                await status_message.edit_text(
                    "❌ Gagal mencari sumber gambar. Coba lagi nanti~",
                    parse_mode="HTML"
                )
            finally:
                try:
                    if 'temp_path' in locals():
                        os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

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
            from handlers.response.analyze import analyze_resposne
            await message.reply_html(analyze_resposne(), reply_to_message_id=message.message_id)
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
    message = await update.message.reply_text("Pinging...")
    end_time = time.time()
    latency = (end_time - start_time) * 1000
    response = ping_response(latency_ms=latency)
    await message.edit_text(
        format_response(response, username=update.effective_user.first_name),
        parse_mode="HTML"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    response = start_response(username=user.first_name or "user")
    await update.message.reply_text(
        format_response(response, username=user.first_name),
        parse_mode="HTML"
    )
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /start: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    response = help_response()
    formatted_help = response.format(username=user.first_name or "user")
    await update.message.reply_html(formatted_help)
    try:
        await set_bot_commands(context.application)
    except Exception as e:
        logger.error(f"Failed to set bot commands on /help: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    memory_manager = context.bot_data.get("memory_manager")
    db_manager = context.bot_data.get("db_manager")
    if not memory_manager or not db_manager:
        logger.error("Memory manager or database manager not found in bot_data")
        await update.message.reply_text(
            "Maaf, terjadi kesalahan sistem. Tolong coba lagi nanti ya~ 😳",
            parse_mode="MarkdownV2"
        )
        return

    success = memory_manager.reset_conversation_context(user.id)
    if success:
        memory_manager.store_message(
            user_id=user.id,
            message="Conversation context has been reset.",
            is_user=False,
            metadata={"type": "system_notification"}
        )
        user_data = db_manager.get_user_relationship_info(user.id)
        relationship = user_data.get("relationship", {})
        friendship_level = relationship.get("name", "stranger").lower() if relationship else "stranger"
        if friendship_level == "close_friend":
            response = (
                "Baiklah, aku sudah melupakan percakapan kita sebelumnya~ Tapi tentu saja aku masih ingat siapa kamu! ✨"
            )
        elif friendship_level == "friend":
            response = (
                "Hmph! Jadi kamu ingin memulai dari awal? Baiklah, aku sudah reset percakapan kita! 😳"
            )
        else:
            response = (
                "Percakapan kita sudah direset. A-aku harap kita bisa bicara lebih baik kali ini... b-bukan berarti aku peduli atau apa! 💫"
            )
        await update.message.reply_text(format_response(response))
        memory_manager.store_message(
            user_id=user.id,
            message=response,
            is_user=False,
            metadata={"type": "reset_response"}
        )
    else:
        await update.message.reply_text(format_response(
            "Maaf, ada kesalahan saat mereset percakapan kita. Bisa coba lagi nanti? 😳"
        ))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_manager = context.bot_data.get("db_manager")
    if not db_manager:
        logger.error("Database manager not found in bot_data")
        await update.message.reply_text(
            "Maaf, terjadi kesalahan sistem. Coba lagi nanti ya~ 😳",
            parse_mode="HTML"
        )
        return

    stats = db_manager.get_user_relationship_info(user.id)
    if not stats or not stats.get("relationship"):
        await update.message.reply_text(
            "Belum ada data hubungan. Coba kirim pesan dulu ke Alya ya~ 😳",
            parse_mode="HTML"
        )
        return

    logger.debug(f"Stats data for user {user.id}: {stats}")
    response = stats_response(
        name=stats.get('name', user.first_name),
        relationship=stats.get("relationship", {}),
        affection=stats.get("affection", {}),
        stats=stats.get("stats", {})
    )
    await update.message.reply_html(response)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
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
        from handlers.response.search import search_usage_response
        usage_text = search_usage_response()
        await update.message.reply_text(
            format_response(usage_text, username=user.first_name),
            parse_mode="HTML"
        )
        return
    await update.message.chat.send_action("typing")
    try:
        if search_type == 'profile':
            search_results = await search_web(
                query=query,
                max_results=8,
                search_type="profile",
                safe_search="off"
            )
        elif search_type == 'news':
            search_results = await search_web(
                query=query,
                max_results=8,
                search_type="news",
                safe_search="off"
            )
        elif search_type == 'image':
            search_results = await search_web(
                query=query,
                max_results=8,
                search_type="image",
                safe_search="off"
            )
        else:
            search_results = await search_web(
                query=query,
                max_results=8,
                safe_search="off"
            )
        from handlers.response.search import format_search_results
        show_username_tip = search_type == 'profile' and (not search_results or len(search_results) < 2)
        response_text = format_search_results(
            query,
            search_results,
            search_type,
            show_username_tip=show_username_tip
        )
        await update.message.reply_text(
            response_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        from handlers.response.search import search_error_response
        error_text = search_error_response(str(e))
        await update.message.reply_text(
            format_response(error_text, username=user.first_name),
            parse_mode="HTML"
        )

async def set_bot_commands(application) -> None:
    all_commands = [
        BotCommand("start", "Mulai percakapan dengan Alya"),
        BotCommand("help", "Lihat semua fitur Alya"),
        BotCommand("ping", "Cek respons bot"),
        BotCommand("stats", "Lihat statistik hubungan kamu dengan Alya"),
        BotCommand("reset", "Reset percakapan dan memulai dari awal"),
        BotCommand("search", "Cari informasi di internet"),
        BotCommand("search_profile", "Cari profil/sosial media"),
        BotCommand("search_news", "Cari berita terbaru"),
        BotCommand("search_image", "Cari gambar")
    ]
    try:
        await application.bot.set_my_commands(all_commands)
        private_scope = BotCommandScope(type=BotCommandScopeType.ALL_PRIVATE_CHATS)
        await application.bot.set_my_commands(all_commands, scope=private_scope)
        logger.info(f"Registered {len(all_commands)} bot commands to Telegram menu successfully")
    except Exception as e:
        logger.error(f"Failed to register bot commands: {e}")

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
    application.add_handler(CommandHandler("start", start_command), group=0)
    application.add_handler(CommandHandler("help", help_command), group=0)
    application.add_handler(CommandHandler("ping", ping_command), group=0)
    application.add_handler(CommandHandler("stats", stats_command), group=0)
    application.add_handler(CommandHandler("reset", reset_command), group=0)
    application.add_handler(CommandHandler("search", search_command), group=0)
    application.add_handler(CommandHandler("search_profile", search_profile_command), group=0)
    application.add_handler(CommandHandler("search_news", search_news_command), group=0)
    application.add_handler(CommandHandler("search_image", search_image_command), group=0)
    CommandsHandler(application)
    logger.info("Command handlers registered successfully")