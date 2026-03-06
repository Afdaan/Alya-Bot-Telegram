"""
Voice language response generator for Alya Bot.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

async def get_voice_lang_keyboard():
    """Build voice language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("English 🇺🇸", callback_data="setvlang_en")],
        [InlineKeyboardButton("Indonesia 🇮🇩", callback_data="setvlang_id")],
        [InlineKeyboardButton("日本語 🎌", callback_data="setvlang_ja")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_voice_lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /voicelang command."""
    await update.message.reply_html(
        "🎙️ <b>Voice Settings</b>\nSelect your preferred TTS language for Alya:",
        reply_markup=await get_voice_lang_keyboard()
    )

async def handle_voice_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice language selection callback."""
    query = update.callback_query
    await query.answer()
    
    lang_code = query.data.split("_")[1]
    lang_name = {"en": "English", "id": "Indonesia", "ja": "Japanese"}.get(lang_code, "English")
    
    # Update DB if available
    from main import db_manager
    if db_manager:
        db_manager.update_user_voice_language(query.from_user.id, lang_code)
    
    await query.edit_message_text(
        text=f"✅ Voice language set to <b>{lang_name}</b>!",
        parse_mode='HTML'
    )