import logging
import tempfile
from telegram import Update
from telegram.ext import CallbackContext
import re
from utils.saucenao import reverse_search_image
import aiohttp

logger = logging.getLogger(__name__)

async def format_sauce_results(result: dict, username: str) -> str:
    """Format sauce search results for display."""
    if not result['success']:
        return f"Gomen ne {username}\\-kun\\~ Alya tidak menemukan sauce yang tepat 😔"
    
    sauce_text = f"*Hasil pencarian untuk {username}\\-kun\\:*\n\n"
    for i, item in enumerate(result['results'], 1):
        sauce_text += (
            f"*Source {i}:*\n"
            f"• Similarity: `{item['similarity']}%`\n"
            f"• Source: `{item['source']}`\n"
            f"• Link: [Click here]({item['url']})\n"
            f"• Creator: `{item.get('author', 'Unknown')}`\n\n"
        )
    return sauce_text

async def handle_image_search(message, mode: str, user) -> str:
    """Handle reverse image search."""
    try:
        photo = message.photo[-1]  # Get largest photo size
        file = await photo.get_file()
        
        if mode == 'anime':
            # Try SauceNAO
            result = await reverse_search_image(file)
            if result['success']:
                return await format_sauce_results(result, user.first_name)
            else:
                # If no results, suggest trying Lens
                return (
                    f"*Gomen ne {user.first_name}\\-kun\\~* 😔\n\n"
                    "Alya tidak menemukan sumber anime/manga\\.\n"
                    "Coba pakai Google Lens untuk gambar umum ya\\~"
                )
        
        elif mode == 'lens':
            # Get image URL for Lens
            img_url = file.file_path
            lens_url = f"https://lens.google.com/uploadbyurl?url={img_url}"
            return (
                f"*{user.first_name}\\-kun\\~* Alya sudah siapkan linknya\\!\n\n"
                f"[🔍 Klik di sini]({lens_url}) untuk mencari dengan Google Lens\\~"
            )
    
    except Exception as e:
        logger.error(f"Error in image search: {e}")
        return "Gomen ne\\~ Ada masalah saat memproses gambar\\. \\. \\. 🥺"

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle callback queries."""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data.startswith('sauce_'):
            mode = query.data.split('_')[1]
            original_message = query.message.reply_to_message
            
            if not original_message or not original_message.photo:
                await query.edit_message_text(
                    "Gomen ne\\~ Alya tidak bisa menemukan gambarnya\\. \\. \\. 🥺\n"
                    "Coba kirim ulang ya\\~",
                    parse_mode='MarkdownV2'
                )
                return

            result_text = await handle_image_search(original_message, mode, update.effective_user)
            await query.edit_message_text(
                result_text,
                parse_mode='MarkdownV2',
                disable_web_page_preview=False
            )
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        await query.edit_message_text(
            "Gomen ne\\~ Ada kesalahan saat memproses permintaan\\. \\. \\. 🥺",
            parse_mode='MarkdownV2'
        )