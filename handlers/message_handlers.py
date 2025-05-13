import logging
import asyncio
from telegram import Update
from telegram.ext import CallbackContext
from datetime import datetime

from config.settings import CHAT_PREFIX
from core.models import generate_chat_response
from core.personas import WAIFU_PERSONA, TOXIC_PERSONA, SMART_PERSONA
from utils.formatters import format_markdown_response, split_long_message
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
        
        # Extract mentioned username for proper handling
        mentioned_username = None
        telegram_mention = None
        
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":  # This is a @username mention
                    telegram_mention = message_text[entity.offset:entity.offset + entity.length]
                    # Extract username without @ for potential use in message
                    mentioned_username = telegram_mention[1:]  # Remove the @ symbol
                    break

        # Handle search command with "!search" prefix
        if message_text.lower().startswith('!search'):
            args = message_text.split(' ')[1:]
            context.args = args
            from handlers.command_handlers import handle_search
            return await handle_search(update, context)

        # Check for group message prefix
        if chat_type in ['group', 'supergroup']:
            if not message_text.startswith(CHAT_PREFIX):
                return
            message_text = message_text.replace(CHAT_PREFIX, "", 1).strip()

        if not message_text:
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Check for roasting command
        is_roast, target, is_github, keywords, user_info = is_roast_command(update.message)

        # Use appropriate persona
        if is_roast:
            persona = TOXIC_PERSONA
        else:
            # If user asks for detail/advanced, or question is long, use SMART_PERSONA
            info_keywords = ['jadwal', 'siapa', 'apa', 'dimana', 'kapan', 'bagaimana', 
                            'mengapa', 'cara', 'berapa', 'info', 'cari', 'carikan', 'detail', '-d', '--detail']
            is_info_query = any(keyword in message_text.lower() for keyword in info_keywords)
            is_advanced = (
                'detail' in message_text.lower() or
                '-d' in message_text.lower() or
                '--detail' in message_text.lower() or
                len(message_text.split()) > 12  # consider advanced if question is long
            )
            persona = SMART_PERSONA if (is_info_query and is_advanced) else WAIFU_PERSONA
        
        # Generate response with persona context and timeout handling
        try:
            response = await asyncio.wait_for(
                generate_chat_response(
                    message_text,
                    user.id,
                    context=context,
                    persona_context=persona
                ),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Response generation timed out for user {user.id}")
            await update.message.reply_text(
                "Aduh\\, maaf ya\\~ Alya\\-chan butuh waktu lebih lama untuk memikirkan jawaban yang tepat\\. Coba tanyakan dengan cara yang lebih sederhana ya\\? 🥺💕",
                parse_mode='MarkdownV2'
            )
            return

        # Format and send response, pass both first_name AND mentioned username when available
        # This is key - we pass both to handle mentions correctly
        safe_response = format_markdown_response(
            response,
            username=user.first_name,
            telegram_username=telegram_mention,
            mentioned_username=mentioned_username  # Add this parameter
        )

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

        if len(safe_response) > 4000:
            parts = split_long_message(safe_response, 4000)
            for i, part in enumerate(parts):
                await update.message.reply_text(
                    part,
                    reply_to_message_id=update.message.message_id if i == 0 else None,
                    parse_mode='MarkdownV2'
                )
                await asyncio.sleep(0.5)
        else:
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