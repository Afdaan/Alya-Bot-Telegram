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
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode


import psutil
import platform
import html

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin commands and system management."""

    def __init__(self, db_manager=None, persona_manager=None) -> None:
        self.db = db_manager
        self.persona = persona_manager
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
            CommandHandler("cleanup", self.cleanup_command),
            CommandHandler("addadmin", self.add_admin_command),
            CommandHandler("removeadmin", self.remove_admin_command),
            CommandHandler("spek", self.system_stats_command),
            CommandHandler("voiceadd", self.voice_add_command),
            CommandHandler("voiceremove", self.voice_remove_command),
            CommandHandler("voicelist", self.voice_list_command)
        ]

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bot statistics using MySQL database."""
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

    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cleanup old conversations and optimize MySQL tables."""
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        try:
            await update.message.chat.send_action(action="typing")
            conn = self.db._get_connection()
            try:
                # Example: delete conversations older than 30 days
                from datetime import timedelta
                cutoff = datetime.now() - timedelta(days=30)
                conn.execute("DELETE FROM conversations WHERE timestamp < %s", (cutoff,))
                conn.execute("OPTIMIZE TABLE conversations")
                conn.commit()
            finally:
                conn.close()
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
        """Add a new admin user to MySQL database."""
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        new_admin_id = await self._get_target_user_id(update, context)
        
        if not new_admin_id:
            await update.message.reply_text(
                self._escape_markdown("Usage: /addadmin <user_id|@username>\nOr reply to a user's message."),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        try:
            conn = self.db._get_connection()
            try:
                conn.execute("INSERT IGNORE INTO admins (user_id) VALUES (%s)", (new_admin_id,))
                conn.commit()
            finally:
                conn.close()
            self.authorized_users.append(new_admin_id)
            await update.message.reply_text(
                self._escape_markdown(
                    f"✅ *User {new_admin_id} is now an admin!*\n\n"
                    "_Alya akan memperlakukan mereka dengan istimewa~ 💫_"
                ),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error in add_admin_command: {e}")
            await self._error_response(update, user.first_name, str(e))

    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove an admin user from MySQL database."""
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        admin_id = await self._get_target_user_id(update, context)
        
        if not admin_id:
            await update.message.reply_text(
                self._escape_markdown("Usage: /removeadmin <user_id|@username>\nOr reply to a user's message."),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        if admin_id == user.id:
            await update.message.reply_text(
                self._escape_markdown("❌ *You cannot remove yourself as admin!*"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        try:
            conn = self.db._get_connection()
            try:
                conn.execute("DELETE FROM admins WHERE user_id = %s", (admin_id,))
                conn.commit()
            finally:
                conn.close()
            if admin_id in self.authorized_users:
                self.authorized_users.remove(admin_id)
            await update.message.reply_text(
                self._escape_markdown(f"✅ *User {admin_id} is no longer an admin!*"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error in remove_admin_command: {e}")
            await self._error_response(update, user.first_name, str(e))


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
    
    async def voice_add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add a user to the voice feature whitelist."""
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        
        target_user_id = await self._get_target_user_id(update, context)
        
        if not target_user_id:
            await update.message.reply_text(
                "📝 <b>Usage:</b> <code>/voiceadd &lt;user_id|@username&gt;</code>\n"
                "Or reply to a user's message with <code>/voiceadd</code>\n\n"
                "Example: <code>/voiceadd @nikogemini</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            # Get user object (not dict)
            target_user = self.db.get_user_object(target_user_id)
            
            if not target_user:
                # User doesn't exist, create them first
                self.db.get_or_create_user(
                    user_id=target_user_id,
                    username=f"User_{target_user_id}",
                    first_name="Unknown",
                    last_name=None
                )
                # Now get the User object
                target_user = self.db.get_user_object(target_user_id)
            
            if target_user and target_user.voice_enabled:
                await update.message.reply_text(
                    f"ℹ️ User <code>{target_user_id}</code> already has voice access!",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Enable voice access
            success = self.db.update_user_voice_access(target_user_id, True)
            
            if success:
                await update.message.reply_text(
                    f"✅ <b>Voice Access Granted!</b>\n\n"
                    f"User <code>{target_user_id}</code> can now use voice messages and TTS.\n\n"
                    f"<i>Alya akan berbicara dengan mereka~ 🎤</i>",
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"✅ Admin {user.id} granted voice access to user {target_user_id}")
            else:
                await update.message.reply_text(
                    f"❌ Failed to grant voice access to user <code>{target_user_id}</code>",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error in voice_add_command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ <b>Error:</b> {html.escape(str(e)[:100])}",
                parse_mode=ParseMode.HTML
            )
    
    async def voice_remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove a user from the voice feature whitelist."""
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        
        target_user_id = await self._get_target_user_id(update, context)
        
        if not target_user_id:
            await update.message.reply_text(
                "📝 <b>Usage:</b> <code>/voiceremove &lt;user_id|@username&gt;</code>\n"
                "Or reply to a user's message with <code>/voiceremove</code>\n\n"
                "Example: <code>/voiceremove @nikogemini</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            # Get user object (not dict)
            target_user = self.db.get_user_object(target_user_id)
            
            if not target_user:
                await update.message.reply_text(
                    f"❌ User <code>{target_user_id}</code> not found in database.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            if not target_user.voice_enabled:
                await update.message.reply_text(
                    f"ℹ️ User <code>{target_user_id}</code> doesn't have voice access.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Disable voice access
            self.db.update_user_voice_access(target_user_id, False)
            
            await update.message.reply_text(
                f"✅ <b>Voice Access Revoked!</b>\n\n"
                f"User <code>{target_user_id}</code> can no longer use voice messages.\n\n"
                f"<i>Alya tidak akan berbicara dengan mereka lagi... 😔</i>",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"✅ Admin {user.id} revoked voice access from user {target_user_id}")
            
        except Exception as e:
            logger.error(f"Error in voice_remove_command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ <b>Error:</b> {html.escape(str(e)[:100])}",
                parse_mode=ParseMode.HTML
            )
    
    async def voice_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all users with voice feature access."""
        user = update.effective_user
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        
        try:
            # Get all users with voice enabled
            voice_users = self.db.get_voice_enabled_users()
            
            if not voice_users:
                await update.message.reply_text(
                    "📝 <b>Voice Whitelist</b>\n\n"
                    "No users have voice access yet.\n\n"
                    "Use <code>/voiceadd &lt;user_id&gt;</code> to grant access.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Build user list
            user_list = []
            for idx, voice_user in enumerate(voice_users, 1):
                display_name = voice_user.get_display_name()
                user_list.append(
                    f"{idx}. <code>{voice_user.id}</code> - {html.escape(display_name)}"
                )
            
            message = (
                f"🎤 <b>Voice Feature Whitelist</b>\n"
                f"Total: {len(voice_users)} users\n\n"
                + "\n".join(user_list) +
                "\n\n<i>These users can send and receive voice messages.</i>"
            )
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in voice_list_command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ <b>Error:</b> {html.escape(str(e)[:100])}",
                parse_mode=ParseMode.HTML
            )

    async def _get_target_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
        """Resolve a target user ID from reply, entities, or command arguments."""
        # 1. Check if it's a reply
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user.id
            
        # 2. Check entities (text mentions - users without usernames)
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == 'text_mention' and entity.user:
                    return entity.user.id
                    
        # 3. Check arguments
        if context.args:
            arg = context.args[0]
            
            # Numeric ID
            if arg.isdigit():
                return int(arg)
                
            # Mention (@username)
            if arg.startswith('@'):
                target_user_id = self.db.get_user_id_by_mention(arg)
                if target_user_id:
                    return target_user_id
                    
        return None

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
        """Get bot stats from MySQL database."""
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
                        'SELECT COUNT(*) FROM users WHERE last_interaction >= %s', (today_start,)
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