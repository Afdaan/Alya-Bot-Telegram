import logging
from telegram import Update
from telegram.ext import CallbackContext

from config.settings import CHAT_PREFIX
from core.models import generate_chat_response
from core.personas import get_enhanced_persona
from utils.formatters import format_markdown_response

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle incoming messages."""
    try:
        if not update.message or not update.message.text:
            return

        message_text = update.message.text
        chat_type = update.message.chat.type
        user = update.effective_user

        # Check if it's a group message
        if chat_type in ['group', 'supergroup']:
            # Return if not using prefix
            if not message_text.startswith(CHAT_PREFIX):
                return
            # Remove prefix
            message_text = message_text.replace(CHAT_PREFIX, "", 1).strip()

        # Skip if message is empty
        if not message_text:
            return

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Process message with enhanced persona
        response = generate_chat_response(
            f"User: {user.first_name}\nMessage: {message_text}",
            persona_context=get_enhanced_persona()
        )
        
        # Format and send response
        safe_response = format_markdown_response(response)
        await update.message.reply_text(
            safe_response,
            reply_to_message_id=update.message.message_id,
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        await update.message.reply_text(
            "Gomenasai\\~ Ada masalah kecil\\. Alya akan lebih baik lagi ya\\~ 🥺💕",
            parse_mode='MarkdownV2'
        )