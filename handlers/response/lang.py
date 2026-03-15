"""
Language response generator for Alya Bot.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config.settings import DEFAULT_LANGUAGE

async def get_lang_keyboard():
    """Build language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("English 🇺🇸", callback_data="setlang_en")],
        [InlineKeyboardButton("Indonesia 🇮🇩", callback_data="setlang_id")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang command."""
    await update.message.reply_html(
        "🌐 <b>Language Settings</b>\nSelect your preferred interface language:",
        reply_markup=await get_lang_keyboard()
    )

async def handle_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()
    
    lang_code = query.data.split("_")[1]
    lang_name = {"en": "English", "id": "Indonesia"}.get(lang_code, "English")
    
    # Update DB if available
    from database.database_manager import db_manager
    if db_manager:
        db_manager.update_user_settings(query.from_user.id, {'language': lang_code})
    
    await query.edit_message_text(
        text=f"✅ Language set to <b>{lang_name}</b>!",
        parse_mode='HTML'
    )