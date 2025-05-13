import logging
from telegram import Update
from telegram.ext import CallbackContext
from datetime import datetime

from config.settings import CHAT_PREFIX
from core.models import generate_chat_response
from core.personas import WAIFU_PERSONA, TOXIC_PERSONA  # Import personas directly
from utils.formatters import format_markdown_response
from utils.commands import is_roast_command

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
        
        # Check for roasting command
        is_roast, target, is_github, keywords, user_info = is_roast_command(update.message)
        
        # Generate response with persona context
        response = generate_chat_response(
            message_text,
            user.id,
            context=context,
            persona_context=TOXIC_PERSONA if is_roast else WAIFU_PERSONA  # Use persona directly
        )

        # Format and send response
        safe_response = format_markdown_response(
            response,
            username=user.first_name
        )

        # If debug mode, show simple debug info
        if context.bot_data.get('debug_mode', False):
            debug_info = (
                "*📊 Debug Info*\n"
                f"👤 User ID: `{user.id}`\n"
                f"📝 Username: `@{user.username or 'None'}`\n"
                f"💬 Chat ID: `{update.effective_chat.id}`\n"
                f"💭 Chat Type: `{chat_type}`\n"
                f"📨 Message ID: `{update.message.message_id}`\n"
                f"⏰ Time: `{update.message.date.strftime('%H:%M:%S')}`\n\n"
                f"*💌 Message:*\n"
                f"`{message_text}`\n\n"
                f"*🤖 Response:*\n"
            ) + safe_response

            safe_response = debug_info

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