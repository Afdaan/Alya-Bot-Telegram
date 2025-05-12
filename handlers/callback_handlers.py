import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'chat':
        context.user_data['mode'] = 'chat'
        await query.edit_message_text(
            text="Mode Chat aktif. Silakan kirim pesan Anda untuk berbicara dengan Gemini 2.0!"
        )
    elif query.data == 'image':
        context.user_data['mode'] = 'image'
        await query.edit_message_text(
            text="Mode Generate Image aktif. Silakan kirim deskripsi gambar yang ingin Anda buat!"
        )