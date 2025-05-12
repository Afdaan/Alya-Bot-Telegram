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

        # Check for group message prefix
        if chat_type in ['group', 'supergroup']:
            if not message_text.startswith(CHAT_PREFIX):
                return
            message_text = message_text.replace(CHAT_PREFIX, "", 1).strip()

        # Skip empty messages
        if not message_text:
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Add username context to message
        user_context = f"{user.first_name}: {message_text}"
        
        # Generate response with history
        response = generate_chat_response(
            user_context,  # Pass message with username context
            user.id,  # Pass user ID for history tracking
            persona_context=get_enhanced_persona()
        )
        
        # Format and send response
        safe_response = format_markdown_response(
            response,
            username=user.first_name  # Pass username to formatter
        )
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