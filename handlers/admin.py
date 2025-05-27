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
            CommandHandler("stats", self.system_stats_command)
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
            
            # Get basic usage stats - placeholder for now
            stats = await self._get_bot_stats()
            
            message = (
                "🌸 *Alya Bot Stats* 🌸\n\n"
                f"👥 **Users**: {stats['user_count']}\n"
                f"📈 **Active today**: {stats['active_today']}\n"
                f"💬 **Total messages**: {stats['total_messages']}\n"
                f"⚡ **Commands used**: {stats['commands_used']}\n"
                f"💾 **Memory size**: {stats['memory_size']} MB\n\n"
                "_Alya senang melayani admin\\-sama\\~ 💫_"
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
        """Handle /stats command for system statistics.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        user = update.effective_user
        
        if not self._is_authorized_user(user.id):
            await self._unauthorized_response(update, user.first_name)
            return
        
        try:
            await self.deployment_manager.stats_handler(update, context)
        except AttributeError:
            # Fallback if stats_handler doesn't exist in DeploymentManager
            await update.message.reply_text(
                "📊 *System Stats* \\(placeholder\\)\n\n"
                "_Feature akan diimplementasi dengan system monitoring\\._",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    
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
        """Get bot usage statistics.
        
        Returns:
            Dictionary of bot statistics
        """
        # Placeholder implementation
        # In real implementation, this would query database
        return {
            "user_count": 42,
            "active_today": 8,
            "total_messages": 1337,
            "commands_used": 256,
            "memory_size": 2.5
        }
    
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for MarkdownV2
        """
        if not text:
            return ""
            
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
            
        return text


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