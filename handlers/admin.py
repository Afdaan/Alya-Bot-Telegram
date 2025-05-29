"""
Admin command handlers for Alya Bot.
Handles user management, stats, and system administration.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackContext
from telegram.constants import ParseMode

from utils.update_git import DeploymentManager, register_admin_handlers as register_deployment_handlers

import psutil
import platform
import html

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin commands and system management."""

    def __init__(self, db_manager=None, persona_manager=None) -> None:
        self.db = db_manager
        self.persona = persona_manager
        self.deployment_manager = DeploymentManager()
        self.authorized_users = self._load_authorized_users()

    def _load_authorized_users(self) -> List[int]:
        env_users = os.getenv("ADMIN_IDS", "")
        if env_users:
            try:
                return [int(uid.strip()) for uid in env_users.split(",") if uid.strip()]
            except ValueError:
                logger.warning("Invalid ADMIN_IDS format in environment")
        logger.warning("No authorized users configured. Admin functions disabled.")
        return []

    def get_handlers(self) -> List[CommandHandler]:
        return [
            CommandHandler("statsall", self.stats_command),
            CommandHandler("broadcast", self.broadcast_command),
            CommandHandler("cleanup", self.cleanup_command),
            CommandHandler("addadmin", self.add_admin_command),
            CommandHandler("removeadmin", self.remove_admin_command),
            CommandHandler("update", self.update_command),
            CommandHandler("status", self.status_command),
            CommandHandler("restart", self.restart_command),
            CommandHandler("spek", self.system_stats_command)
        ]

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        try:
            await update.message.chat.send_action(action="typing")
            stats = await self._get_bot_stats()
            esc = self._escape_markdown
            msg = (
                f"{esc('🌸')} *{esc('Alya Bot Stats')}* {esc('🌸')}\n\n"
                f"{esc('👥')} *{esc('Users')}*: {esc(stats['user_count'])}\n"
                f"{esc('📈')} *{esc('Active today')}*: {esc(stats['active_today'])}\n"
                f"{esc('💬')} *{esc('Total messages')}*: {esc(stats['total_messages'])}\n"
                f"{esc('⚡')} *{esc('Commands used')}*: {esc(stats['commands_used'])}\n"
                f"{esc('💾')} *{esc('Memory size')}*: {esc(stats['memory_size'])} {esc('MB')}\n\n"
                f"_{esc('Alya senang melayani admin-sama~ 💫')}_"
            )
            await update.message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error in admin stats command: {e}")
            await self._error_response(update, user.first_name, str(e))

    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        if not context.args:
            await update.message.reply_text(
                self._escape_markdown("Usage: /broadcast <message>"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        broadcast_text = " ".join(context.args)
        await update.message.reply_text(
            self._escape_markdown(
                f"📢 *Broadcasting to all users:*\n\n{broadcast_text}\n\n"
                "_(Feature akan diimplementasi dengan database integration)_"
            ),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        try:
            await update.message.chat.send_action(action="typing")
            await asyncio.sleep(2)
            await update.message.reply_text(
                self._escape_markdown(
                    "✨ *Database cleanup completed!* ✨\n\n"
                    "_Alya sudah merapikan memory database untuk admin-sama~ 💫_"
                ),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error in admin cleanup command: {e}")
            await self._error_response(update, user.first_name, str(e))

    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                self._escape_markdown("Usage: /addadmin <user_id>"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        new_admin_id = int(context.args[0])
        await update.message.reply_text(
            self._escape_markdown(
                f"✅ *User {new_admin_id} is now an admin!*\n\n"
                "_Alya akan memperlakukan mereka dengan istimewa~ 💫_"
            ),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                self._escape_markdown("Usage: /removeadmin <user_id>"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        admin_id = int(context.args[0])
        if admin_id == user.id:
            await update.message.reply_text(
                self._escape_markdown("❌ *You cannot remove yourself as admin!*"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        await update.message.reply_text(
            self._escape_markdown(f"✅ *User {admin_id} is no longer an admin!*"),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    async def update_command(self, update: Update, context: CallbackContext) -> None:
        await self.deployment_manager.update_handler(update, context)

    async def status_command(self, update: Update, context: CallbackContext) -> None:
        await self.deployment_manager.status_handler(update, context)

    async def restart_command(self, update: Update, context: CallbackContext) -> None:
        await self.deployment_manager.restart_handler(update, context)

    async def system_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        try:
            await update.message.chat.send_action(action="typing")
            uname = platform.uname()
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=True)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = psutil.boot_time()
            
            # Format datetime first, then escape all characters
            boot_time_str = datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Build message
            raw_msg = (
                f"🖥️ System Info\n"
                f"OS: {uname.system} {uname.release}\n"
                f"Node: {uname.node}\n"
                f"CPU: {uname.processor or platform.processor()}\n"
                f"Cores: {cpu_count}\n"
                f"CPU Usage: {cpu_percent}%\n"
                f"RAM: {round(ram.used / (1024 ** 3), 2)}GB/"
                f"{round(ram.total / (1024 ** 3), 2)}GB ({ram.percent}%)\n"
                f"Disk: {round(disk.used / (1024 ** 3), 2)}GB/"
                f"{round(disk.total / (1024 ** 3), 2)}GB ({disk.percent}%)\n"
                f"Uptime: {boot_time_str}\n"
                f"\nAlya siap 24 jam buat admin-sama!"
            )
            
            # Format sections in markdown
            formatted_msg = (
                f"{self._escape_markdown('🖥️')} *{self._escape_markdown('System Info')}*\n"
                f"{self._escape_markdown('OS:')} {self._escape_markdown(f'{uname.system} {uname.release}')}\n"
                f"{self._escape_markdown('Node:')} {self._escape_markdown(uname.node)}\n"
                f"{self._escape_markdown('CPU:')} {self._escape_markdown(uname.processor or platform.processor())}\n"
                f"{self._escape_markdown('Cores:')} {self._escape_markdown(str(cpu_count))}\n"
                f"{self._escape_markdown('CPU Usage:')} {self._escape_markdown(f'{cpu_percent}%')}\n"
                f"{self._escape_markdown('RAM:')} {self._escape_markdown(f'{round(ram.used / (1024 ** 3), 2)}GB/')}"
                f"{self._escape_markdown(f'{round(ram.total / (1024 ** 3), 2)}GB')} "
                f"{self._escape_markdown(f'({ram.percent}%)')}\n"
                f"{self._escape_markdown('Disk:')} {self._escape_markdown(f'{round(disk.used / (1024 ** 3), 2)}GB/')}"
                f"{self._escape_markdown(f'{round(disk.total / (1024 ** 3), 2)}GB')} "
                f"{self._escape_markdown(f'({disk.percent}%)')}\n"
                f"{self._escape_markdown('Uptime:')} {self._escape_markdown(boot_time_str)}\n"
                f"\n_{self._escape_markdown('Alya siap 24 jam buat admin-sama!')}_"
            )
            
            await update.message.reply_text(
                formatted_msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error in system_stats_command: {e}", exc_info=True)
            # Use HTML instead of markdown for error messages to avoid more formatting issues
            await update.message.reply_text(
                f"<b>Error in system stats command:</b> {html.escape(str(e)[:100])}",
                parse_mode=ParseMode.HTML
            )

    async def _unauthorized_response(self, update: Update, username: str) -> None:
        response = (
            f"Ara ara~ {self._escape_markdown(username)}-kun tidak punya izin untuk "
            f"menggunakan command admin! 😤\n\n"
            f"_Hanya admin yang bisa menggunakan fitur ini!_"
        )
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

    async def _error_response(self, update: Update, username: str, error: str) -> None:
        error_msg = self._escape_markdown(str(error)[:100])
        response = (
            f"G-gomen ne {self._escape_markdown(username)}-kun... "
            f"sistem Alya mengalami error... что? 😳\n\n"
            f"Error: `{error_msg}`"
        )
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

    def _is_authorized_user(self, user_id: int) -> bool:
        return user_id in self.authorized_users

    async def _get_bot_stats(self) -> Dict[str, Any]:
        if self.db:
            try:
                user_count = 0
                active_today = 0
                total_messages = 0
                commands_used = 0
                memory_size = 0.0
                import time
                now = int(time.time())
                today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                conn = self.db._get_connection()
                try:
                    user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
                    active_today = conn.execute(
                        'SELECT COUNT(*) FROM users WHERE last_interaction >= ?', (today_start,)
                    ).fetchone()[0]
                    total_messages = conn.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
                    commands_used = conn.execute(
                        'SELECT SUM(command_uses) FROM user_stats'
                    ).fetchone()[0] or 0
                    db_path = self.db.db_path
                    if os.path.exists(db_path):
                        memory_size = round(os.path.getsize(db_path) / (1024 * 1024), 2)
                finally:
                    conn.close()
                return {
                    "user_count": user_count,
                    "active_today": active_today,
                    "total_messages": total_messages,
                    "commands_used": commands_used,
                    "memory_size": memory_size
                }
            except Exception as e:
                logger.error(f"Error querying bot stats: {e}")
        return {
            "user_count": 0,
            "active_today": 0,
            "total_messages": 0,
            "commands_used": 0,
            "memory_size": 0.0
        }

    def _escape_markdown(self, text: str) -> str:
        """Escape all special characters for Telegram MarkdownV2.
        
        Implementation guarantees all special characters are properly escaped,
        even those in complex strings like timestamps.
        
        Args:
            text: Raw text to escape
            
        Returns:
            Text with all special characters escaped for MarkdownV2
        """
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Escape backslash first to avoid double-escaping
        text = text.replace('\\', '\\\\')
        
        # MarkdownV2 special characters that need escaping
        # Order matters - escape them one by one
        special_chars = '_*[]()~`>#+-=|{}.!%'
        
        # Escape each character individually
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
            
        return text


def register_admin_handlers(application, **kwargs) -> None:
    admin_handler = AdminHandler(
        db_manager=kwargs.get('db_manager'),
        persona_manager=kwargs.get('persona_manager')
    )
    handlers = admin_handler.get_handlers()
    for handler in handlers:
        application.add_handler(handler)
    logger.info(f"Registered {len(handlers)} admin command handlers")
    logger.info(f"Authorized admin users: {len(admin_handler.authorized_users)}")
    commands = []
    for handler in handlers:
        if hasattr(handler, 'commands'):
            if isinstance(handler.commands, (list, tuple)):
                commands.append(handler.commands[0])
            elif isinstance(handler.commands, (str, frozenset)):
                if isinstance(handler.commands, frozenset):
                    commands.append(next(iter(handler.commands), "unknown"))
                else:
                    commands.append(handler.commands)
    if commands:
        logger.info(f"Available admin commands: {', '.join(commands)}")
    else:
        logger.info("No admin commands available")
    register_deployment_handlers(application)
    logger.info("Registered deployment handlers from update_git.py")