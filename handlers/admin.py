"""
Admin command handlers for Alya Bot.
"""
import logging
import os
import json
from typing import Dict, List, Any, Optional

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from config.settings import ADMIN_IDS
from core.database import DatabaseManager
from core.persona import PersonaManager
from utils.formatters import format_response, format_error_response

logger = logging.getLogger(__name__)

class AdminHandler:
    """Handler for admin commands."""
    
    def __init__(self, db_manager: DatabaseManager, persona_manager: PersonaManager) -> None:
        """Initialize admin handler.
        
        Args:
            db_manager: Database manager for user operations
            persona_manager: Persona manager for response formatting
        """
        self.db = db_manager
        self.persona = persona_manager
        
    def get_handlers(self) -> List:
        """Get admin command handlers.
        
        Returns:
            List of admin command handlers
        """
        return [
            CommandHandler("stats", self.stats_command),
            CommandHandler("broadcast", self.broadcast_command),
            CommandHandler("cleanup", self.cleanup_command),
            CommandHandler("addadmin", self.add_admin_command),
            CommandHandler("removeadmin", self.remove_admin_command)
        ]
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bot stats (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Check if user is admin
        if not self._is_admin(user.id):
            await self._unauthorized_response(update)
            return
            
        try:
            # Send typing action
            await update.message.chat.send_action(action="typing")
            
            # Get basic usage stats from DB - would implement in DatabaseManager
            stats = await self._get_bot_stats()
            
            # Format stats as HTML
            message = (
                "<b>🌸 Alya Bot Stats 🌸</b>\n\n"
                f"<b>Users:</b> {stats['user_count']}\n"
                f"<b>Active today:</b> {stats['active_today']}\n"
                f"<b>Total messages:</b> {stats['total_messages']}\n"
                f"<b>Commands used:</b> {stats['commands_used']}\n"
                f"<b>Memory size:</b> {stats['memory_size']} MB\n\n"
                "<i>Alya is happy to serve you, admin-sama~ 💫</i>"
            )
            
            await update.message.reply_html(message)
            
        except Exception as e:
            logger.error(f"Error in admin stats command: {e}")
            error_message = self.persona.get_error_message(username=user.first_name)
            await update.message.reply_html(format_error_response(error_message))
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Broadcast a message to all users (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Check if user is admin
        if not self._is_admin(user.id):
            await self._unauthorized_response(update)
            return
            
        # Check if message is provided
        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return
            
        broadcast_text = " ".join(context.args)
        
        # Here we would implement the actual broadcast
        # This would involve getting all user IDs and sending messages
        # For now, just acknowledge the command
        await update.message.reply_html(
            f"<b>Broadcasting to all users:</b>\n\n{broadcast_text}\n\n"
            "<i>This would send to all users in a real implementation</i>"
        )
    
    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Run database cleanup (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Check if user is admin
        if not self._is_admin(user.id):
            await self._unauthorized_response(update)
            return
            
        try:
            # Send typing action
            await update.message.chat.send_action(action="typing")
            
            # Run cleanup
            self.db.cleanup_old_data()
            
            await update.message.reply_html(
                "<b>Database cleanup completed!</b>\n\n"
                "<i>Alya tidied up the memory database for you, admin-sama~ 💫</i>"
            )
            
        except Exception as e:
            logger.error(f"Error in admin cleanup command: {e}")
            error_message = self.persona.get_error_message(username=user.first_name)
            await update.message.reply_html(format_error_response(error_message))
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add a new admin (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Check if user is admin
        if not self._is_admin(user.id):
            await self._unauthorized_response(update)
            return
            
        # Check if user ID is provided
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /addadmin <user_id>")
            return
            
        new_admin_id = int(context.args[0])
        
        # Add admin status in database
        self.db.get_or_create_user(
            user_id=new_admin_id, 
            is_admin=True
        )
        
        await update.message.reply_html(
            f"<b>User {new_admin_id} is now an admin!</b>\n\n"
            "<i>Alya will treat them with special care~ 💫</i>"
        )
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove admin privileges (admin only).
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        
        # Check if user is admin
        if not self._is_admin(user.id):
            await self._unauthorized_response(update)
            return
            
        # Check if user ID is provided
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /removeadmin <user_id>")
            return
            
        admin_id = int(context.args[0])
        
        # Don't allow removing self
        if admin_id == user.id:
            await update.message.reply_html(
                "<b>You cannot remove yourself as admin!</b>"
            )
            return
            
        # Update admin status in database
        conn = self.db._get_connection()
        try:
            conn.execute(
                'UPDATE users SET is_admin = 0 WHERE user_id = ?',
                (admin_id,)
            )
            conn.commit()
            
            await update.message.reply_html(
                f"<b>User {admin_id} is no longer an admin!</b>"
            )
        except Exception as e:
            logger.error(f"Error removing admin: {e}")
            await update.message.reply_html(
                "<b>Failed to remove admin privileges.</b>"
            )
        finally:
            conn.close()
    
    async def _unauthorized_response(self, update: Update) -> None:
        """Send unauthorized response for non-admin users.
        
        Args:
            update: The update from Telegram
        """
        user = update.effective_user
        
        # Get special tsundere response for unauthorized access
        angry_response = self.persona.get_mood_response(
            "tsundere_cold", username=user.first_name
        )
        
        if not angry_response:
            angry_response = f"Hmph! {user.first_name}-kun bukan admin! Jangan coba-coba! 😤"
            
        await update.message.reply_html(format_response(angry_response, "anger"))
        
    def _is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user is admin, False otherwise
        """
        # Check against ADMIN_IDS in settings
        if hasattr(ADMIN_IDS, '__iter__') and user_id in ADMIN_IDS:
            return True
            
        # Check in database
        return self.db.is_admin(user_id)
    
    async def _get_bot_stats(self) -> Dict[str, Any]:
        """Get bot usage statistics.
        
        Returns:
            Dictionary of bot statistics
        """
        # In a real implementation, this would query the database
        # For now, return dummy data
        
        # Get DB file size
        db_size_mb = 0
        if os.path.exists(self.db.db_path):
            db_size_mb = os.path.getsize(self.db.db_path) / (1024 * 1024)
            
        # Here we would implement actual database queries
        # This is a placeholder
        return {
            "user_count": 10,
            "active_today": 3,
            "total_messages": 150,
            "commands_used": 25,
            "memory_size": round(db_size_mb, 2)
        }
