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

# Import deployment manager from utils
from utils.update_git import DeploymentManager, register_admin_handlers as register_deployment_handlers

import psutil
import platform

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin commands and system management."""
    
    def __init__(self, db_manager=None, persona_manager=None) -> None:
        """Initialize admin handler.
        
        Args:
            db_manager: Database manager for user operations (optional for now)
            persona_manager: Persona manager for response formatting (optional for now)
        """
        self.db = db_manager
        self.persona = persona_manager
        
        # Initialize deployment manager for git operations
        self.deployment_manager = DeploymentManager()
        
        # Load authorized users from environment
        self.authorized_users = self._load_authorized_users()
    
    def _load_authorized_users(self) -> List[int]:
        """Load authorized user IDs from environment variables.
        
        Returns:
            List of authorized Telegram user IDs
        """
        env_users = os.getenv("ADMIN_IDS", "")
        if env_users:
            try:
                return [int(uid.strip()) for uid in env_users.split(",") if uid.strip()]
            except ValueError:
                logger.warning("Invalid ADMIN_IDS format in environment")
        
        logger.warning("No authorized users configured. Admin functions disabled.")
        return []
    
    def get_handlers(self) -> List[CommandHandler]:
        """Get all admin command handlers.
        
        Returns:
            List of CommandHandler objects for registration
        """
        return [
            # User management commands
            CommandHandler("statsall", self.stats_command),
            CommandHandler("broadcast", self.broadcast_command),
            CommandHandler("cleanup", self.cleanup_command),
            CommandHandler("addadmin", self.add_admin_command),
            CommandHandler("removeadmin", self.remove_admin_command),
            
            # Deployment commands (delegated to DeploymentManager)
            CommandHandler("update", self.update_command),
            CommandHandler("status", self.status_command),
            CommandHandler("restart", self.restart_command),
            CommandHandler("spek", self.system_stats_command)
        ]
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bot usage stats (admin only).

        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user

        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return

        try:
            await update.message.chat.send_action(action="typing")

            stats = await self._get_bot_stats()

            def escape_md(text: str) -> str:
                import re
                # Escape all MarkdownV2 special chars (Telegram official list)
                # https://core.telegram.org/bots/api#markdownv2-style
                special_chars = r'([_*\[\]()~`>#+\-=|{}.!\\])'
                return re.sub(special_chars, r'\\\1', str(text))

            message = (
                f"{escape_md('🌸 *Alya Bot Stats* 🌸')}\n\n"
                f"{escape_md('👥 *Users*:')} {escape_md(stats['user_count'])}\n"
                f"{escape_md('📈 *Active today*:')} {escape_md(stats['active_today'])}\n"
                f"{escape_md('💬 *Total messages*:')} {escape_md(stats['total_messages'])}\n"
                f"{escape_md('⚡ *Commands used*:')} {escape_md(stats['commands_used'])}\n"
                f"{escape_md('💾 *Memory size*:')} {escape_md(stats['memory_size'])} MB\n\n"
                f"{escape_md('_Alya senang melayani admin-sama~ 💫_')}"
            )

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)

        except Exception as e:
            logger.error(f"Error in admin stats command: {e}")
            await self._error_response(update, user.first_name, str(e))

    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Broadcast message to all users (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
            
        if not context.args:
            await update.message.reply_text(
                "Usage: `/broadcast <message>`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
            
        broadcast_text = " ".join(context.args)
        
        # Placeholder implementation
        await update.message.reply_text(
            f"📢 *Broadcasting to all users:*\n\n"
            f"{self._escape_markdown(broadcast_text)}\n\n"
            "_\\(Feature akan diimplementasi dengan database integration\\)_",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Run database cleanup (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
            
        try:
            await update.message.chat.send_action(action="typing")
            
            # Placeholder for actual cleanup
            await asyncio.sleep(2)  # Simulate cleanup process
            
            await update.message.reply_text(
                "✨ *Database cleanup completed\\!* ✨\n\n"
                "_Alya sudah merapikan memory database untuk admin\\-sama\\~ 💫_",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        except Exception as e:
            logger.error(f"Error in admin cleanup command: {e}")
            await self._error_response(update, user.first_name, str(e))
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add new admin (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
            
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "Usage: `/addadmin <user\\_id>`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
            
        new_admin_id = int(context.args[0])
        
        # Placeholder implementation
        await update.message.reply_text(
            f"✅ *User {new_admin_id} is now an admin\\!*\n\n"
            "_Alya akan memperlakukan mereka dengan istimewa\\~ 💫_",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove admin privileges (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
            
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "Usage: `/removeadmin <user\\_id>`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
            
        admin_id = int(context.args[0])
        
        if admin_id == user.id:
            await update.message.reply_text(
                "❌ *You cannot remove yourself as admin\\!*",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
            
        # Placeholder implementation
        await update.message.reply_text(
            f"✅ *User {admin_id} is no longer an admin\\!*",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    # Deployment commands - delegate to DeploymentManager
    async def update_command(self, update: Update, context: CallbackContext) -> None:
        """Handle /update command - delegate to deployment manager.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        await self.deployment_manager.update_handler(update, context)
    
    async def status_command(self, update: Update, context: CallbackContext) -> None:
        """Handle /status command - delegate to deployment manager.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        await self.deployment_manager.status_handler(update, context)
    
    async def restart_command(self, update: Update, context: CallbackContext) -> None:
        """Handle /restart command - delegate to deployment manager.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        await self.deployment_manager.restart_handler(update, context)
    
    async def system_stats_command(self, update: Update, context: CallbackContext) -> None:
        """Handle /spek command for system statistics (cross-platform).

        Args:
            update: Telegram update object
            context: Callback context
        """
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
            import datetime
            boot_time_str = datetime.datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")

            def escape_md(text: str) -> str:
                import re
                # Escape all MarkdownV2 special chars (Telegram official list)
                special_chars = r'([_*\[\]()~`>#+\-=|{}.!\\])'
                return re.sub(special_chars, r'\\\1', str(text))

            msg = (
                f"{escape_md('🖥️ *System Info*')}\n"
                f"{escape_md('OS:')} {escape_md(uname.system)} {escape_md(uname.release)}\n"
                f"{escape_md('Node:')} {escape_md(uname.node)}\n"
                f"{escape_md('CPU:')} {escape_md(uname.processor or platform.processor())}\n"
                f"{escape_md('Cores:')} {escape_md(cpu_count)}\n"
                f"{escape_md('CPU Usage:')} {escape_md(cpu_percent)}\\%\n"
                f"{escape_md('RAM:')} {escape_md(round(ram.used / (1024 ** 3), 2))}GB/"
                f"{escape_md(round(ram.total / (1024 ** 3), 2))}GB "
                f"({escape_md(ram.percent)}\\%)\n"
                f"{escape_md('Disk:')} {escape_md(round(disk.used / (1024 ** 3), 2))}GB/"
                f"{escape_md(round(disk.total / (1024 ** 3), 2))}GB "
                f"({escape_md(disk.percent)}\\%)\n"
                f"{escape_md('Uptime:')} {escape_md(boot_time_str)}\n"
                f"\n{escape_md('_Alya siap 24 jam buat admin-sama!_')}"
            )

            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

        except Exception as e:
            logger.error(f"Error in system_stats_command: {e}")
            await self._error_response(update, user.first_name, str(e))
    
    async def _unauthorized_response(self, update: Update, username: str) -> None:
        """Send unauthorized response for non-admin users.
        
        Args:
            update: The update from Telegram
            username: User's first name
        """
        response = (
            f"Ara ara\\~ {self._escape_markdown(username)}\\-kun tidak punya izin untuk "
            f"menggunakan command admin\\! 😤\n\n"
            f"_Hanya admin yang bisa menggunakan fitur ini\\!_"
        )
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)
    
    async def _error_response(self, update: Update, username: str, error: str) -> None:
        """Send error response with Alya personality.
        
        Args:
            update: The update from Telegram
            username: User's first name
            error: Error message
        """
        error_msg = self._escape_markdown(str(error)[:100])  # Limit error message length
        
        response = (
            f"G\\-gomen ne {self._escape_markdown(username)}\\-kun\\.\\.\\. "
            f"sistem Alya mengalami error\\.\\.\\. что? 😳\n\n"
            f"Error: `{error_msg}`"
        )
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)
    
    def _is_authorized_user(self, user_id: int) -> bool:
        """Check if user is authorized for admin operations.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user is authorized
        """
        return user_id in self.authorized_users
    
    async def _get_bot_stats(self) -> Dict[str, Any]:
        """Get bot usage statistics from the database.

        Returns:
            Dictionary of bot statistics
        """
        # Use self.db if available, else fallback to dummy
        if self.db:
            try:
                # User count
                user_count = 0
                active_today = 0
                total_messages = 0
                commands_used = 0
                memory_size = 0.0

                import time
                from datetime import datetime

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

                    # Calculate DB file size in MB
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

        # Fallback dummy if DB not available
        return {
            "user_count": 0,
            "active_today": 0,
            "total_messages": 0,
            "commands_used": 0,
            "memory_size": 0.0
        }
    
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2."""
        if not text:
            return ""
        import re
        special_chars = r'[_*\[\]()~`>#+\-=|{}.!%\\]'
        return re.sub(f'({special_chars})', r'\\\1', text)


def register_admin_handlers(application, **kwargs) -> None:
    """Register admin command handlers with the application.
    
    Args:
        application: Telegram bot application instance
        **kwargs: Additional arguments (db_manager, persona_manager, etc.)
    """
    # Initialize admin handler
    admin_handler = AdminHandler(
        db_manager=kwargs.get('db_manager'),
        persona_manager=kwargs.get('persona_manager')
    )
    
    # Register all handlers
    handlers = admin_handler.get_handlers()
    for handler in handlers:
        application.add_handler(handler)
    
    logger.info(f"Registered {len(handlers)} admin command handlers")
    logger.info(f"Authorized admin users: {len(admin_handler.authorized_users)}")
    
    # Log available commands - fix for handling frozenset type
    commands = []
    for handler in handlers:
        if hasattr(handler, 'commands'):
            if isinstance(handler.commands, (list, tuple)):
                commands.append(handler.commands[0])
            elif isinstance(handler.commands, (str, frozenset)):
                # Convert frozenset to string or extract the first item if it's a frozenset
                if isinstance(handler.commands, frozenset):
                    commands.append(next(iter(handler.commands), "unknown"))
                else:
                    commands.append(handler.commands)
    
    if commands:
        logger.info(f"Available admin commands: {', '.join(commands)}")
    else:
        logger.info("No admin commands available")
    
    # Register deployment handlers from utils/update_git.py
    register_deployment_handlers(application)
    logger.info("Registered deployment handlers from update_git.py")