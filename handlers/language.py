"""
Language switching command handler for Alya Bot.
Allows users to switch between Indonesian and English responses.
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext

from core.language_manager import language_manager
from database.database_manager import DatabaseManager
from utils.formatters import escape_html

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


async def lang_command(update: Update, context: CallbackContext) -> None:
    """
    Handle /lang command to switch user language preference.
    
    Usage:
    /lang - Show current language and available options
    /lang id - Switch to Indonesian
    /lang en - Switch to English
    """
    try:
        user = update.effective_user
        if not user:
            return
            
        message = update.message
        if not message or not message.text:
            return
            
        # Parse command arguments
        args = context.args
        
        # Get current user language
        current_lang = db_manager.get_user_language(user.id)
        
        if not args:
            # Show current language and usage
            current_text = language_manager.get_text("language_current", current_lang)
            usage_text = language_manager.get_text("language_usage", current_lang)
            
            response = f"{current_text}\n\n{usage_text}"
            
        elif len(args) == 1:
            new_lang = args[0].lower().strip()
            
            if not language_manager.is_supported_language(new_lang):
                # Language not supported
                error_text = language_manager.get_text(
                    "language_unsupported", 
                    current_lang, 
                    new_lang
                )
                usage_text = language_manager.get_text("language_usage", current_lang)
                response = f"{error_text}\n\n{usage_text}"
                
            elif new_lang == current_lang:
                # Already using this language
                current_text = language_manager.get_text("language_current", current_lang)
                response = f"{current_text}\n\nAlya is already speaking this language~ ✨"
                
            else:
                # Update user language preference
                success = db_manager.update_user_language(user.id, new_lang)
                
                if success:
                    # Language changed successfully
                    response = language_manager.get_text("language_changed", new_lang)
                    logger.info(f"User {user.id} ({user.first_name}) changed language to {new_lang}")
                else:
                    # Database error
                    error_text = language_manager.get_text(
                        "language_current", 
                        current_lang
                    ).replace("Current", "Failed to change")
                    response = f"{error_text}\n\nSomething went wrong... 😳"
        else:
            # Too many arguments
            usage_text = language_manager.get_text("language_usage", current_lang)
            response = f"Too many arguments!\n\n{usage_text}"
        
        # Send response
        await message.reply_text(
            escape_html(response),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in lang_command: {e}")
        try:
            if update.message:
                await update.message.reply_text(
                    "Sorry, something went wrong with the language command... 😳"
                )
        except Exception as reply_error:
            logger.error(f"Failed to send error message: {reply_error}")


async def get_user_language_preference(user_id: int) -> str:
    """
    Helper function to get user's language preference.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        str: User's preferred language code
    """
    return db_manager.get_user_language(user_id)
