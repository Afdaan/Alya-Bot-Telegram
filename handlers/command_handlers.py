import logging
from telegram import Update
from telegram.ext import CallbackContext

from config.settings import (
    CHAT_PREFIX, 
    ANALYZE_PREFIX, 
    SAUCE_PREFIX
)
from core.models import user_chats
from core.search_engine import SearchEngine

logger = logging.getLogger(__name__)

search_engine = SearchEngine()

async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"*Konnichiwa {user.first_name}\\-san\\!* 🌸\n\n"
        "Alya\\-chan di sini\\~ Aku sangat senang bisa berbicara denganmu\\!\n"
        "_Bagaimana kabarmu hari ini?_ ✨"
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='MarkdownV2'
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "*Konnichiwa\\!* 🌸 *Alya\\-chan di sini\\~*\n\n"
        "Ini adalah perintah yang bisa kamu gunakan:\n\n"
        "*Basic Commands:*\n"
        "`/start` \\- Mulai berbicara dengan Alya\\-chan\n"
        "`/help` \\- Bantuan dari Alya\\-chan\n"
        "`/reset` \\- Hapus history chat\n"
        "`/ping` \\- Cek status bot\n\n"
        
        "*Chat Commands:*\n"
        "\\- Chat Private: _Langsung kirim pesan ke Alya\\-chan_\n"
        f"\\- Chat Grup: Gunakan `{CHAT_PREFIX}` di awal pesan\n"
        f"Contoh: `{CHAT_PREFIX} Ohayou Alya\\-chan\\~`\n\n"
        
        "*Image/Document Analysis:*\n"
        f"\\- Kirim gambar/dokumen dengan caption `{ANALYZE_PREFIX}`\n"
        f"Contoh: `{ANALYZE_PREFIX} Tolong analisis gambar ini`\n\n"
        
        "*Reverse Image Search:*\n"
        f"\\- Kirim gambar dengan caption `{SAUCE_PREFIX}`\n"
        f"Contoh: `{SAUCE_PREFIX}` untuk mencari sumber gambar anime/artwork\n\n"
        
        "*Smart Search:*\n"
        "\\- Command: `!search <query>`\n"
        "\\- Detail search: `!search -d <query>`\n"
        "\\- Contoh: `!search jadwal KRL lempuyangan jogja`\n"
        "\\- Alya juga bisa langsung menjawab pertanyaan informasi faktual\n"
        f"\\- Contoh: `{CHAT_PREFIX} carikan jadwal kereta dari Bandung ke Jakarta`\n\n"
        
        "*Roasting Mode:*\n"
        "1\\. Roast Biasa:\n"
        f"`{CHAT_PREFIX} roast <username> [keywords]`\n"
        "2\\. Roast GitHub:\n"
        f"`{CHAT_PREFIX} roast github <username>`\n"
        "Contoh: `!ai roast username wibu nolep`\n\n"
        
        "_Prefix Commands:_\n"
        f"`{CHAT_PREFIX}` \\- Untuk chat dengan Alya di grup\n"
        f"`{ANALYZE_PREFIX}` \\- Analisis gambar/dokumen\n"
        f"`{SAUCE_PREFIX}` \\- Cari source gambar\n"
        "`!search` \\- Cari informasi di internet\n"
        f"`{CHAT_PREFIX} roast` \\- Mode toxic queen\n\n"
        
        "_Fitur Smart:_\n"
        "\\- Alya bisa mencari informasi faktual otomatis\n"
        "\\- Tanya tentang jadwal, berita, cuaca, atau informasi lainnya\n"
        "\\- Support pencarian pintar tentang: jadwal kereta, pesawat, bus, dll\n"
        "\\- Akan otomatis mencari di internet dan merangkum hasilnya\n\n"
        
        "_Yoroshiku onegaishimasu\\!_ ✨"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='MarkdownV2'
    )

async def reset_command(update: Update, context: CallbackContext) -> None:
    """Reset chat history."""
    user_id = update.effective_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    
    await update.message.reply_text("History chat telah dihapus!")

async def handle_search(update: Update, context: CallbackContext):
    """Handle search requests"""
    # For messages that start with !search, extract the query
    if update.message.text and update.message.text.startswith('!search'):
        query = update.message.text.replace('!search', '', 1).strip()
    else:
        # For /search command (if still used)
        query = ' '.join(context.args)
    
    if not query:
        await update.message.reply_text(
            "Cara penggunaan:\n!search <kata kunci>\n\n"
            "Contoh:\n!search jadwal KRL lempuyangan jogja"
        )
        return

    # Check if detailed search is requested
    detailed = any(flag in query.lower() for flag in ['-d', '--detail', 'detail'])
    if detailed:
        query = query.replace('-d', '').replace('--detail', '').replace('detail', '').strip()

    await update.message.reply_text("🔍 Sedang mencari informasi...")
    result = await search_engine.search(query, detailed=detailed)
    await update.message.reply_text(result, parse_mode='HTML')