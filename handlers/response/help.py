from typing import Literal

def get_help_response(lang: Literal['id', 'en'], username: str = "user") -> str:
    """
    Generates a help response for the bot in the specified language.

    Args:
        lang: The language for the response ('id' or 'en').
        username: The user's first name.

    Returns:
        The help message string.
    """
    if lang == 'id':
        return """<b>✨ Selamat datang di Student Council Support System! ✨</b>

Alya sebagai wakil ketua OSIS siap membantu kamu dengan berbagai keperluan:

<b>🎓 Layanan Chat:</b>
• Ngobrol santai dengan Alya untuk diskusi dan curhat.
• <code>!ask [pertanyaan]</code> - Tanya apa saja ke Alya, bisa tentang gambar atau dokumen juga.

<b>📚 Fitur Bot:</b>
• <code>/help</code> - Panduan lengkap fitur bot.
• <code>/stats</code> - Lihat statistik interaksi kamu dengan Alya.
• <code>/ping</code> - Cek kecepatan respon Alya.
• <code>/lang</code> - Ganti preferensi bahasa (en/id).
• <code>/reset</code> - Mulai percakapan dari awal.

<b>🔧 Utilitas:</b>
• <code>!sauce [reply ke gambar]</code> - Cari sumber gambar anime/manga.

Alya akan berusaha sebaik mungkin membantumu! 💫

<i>Ah, dan Alya akan mengingat semua percakapan kita... jadi jangan bilang hal yang aneh-aneh ya! 😤</i>"""
    else:
        return """<b>✨ Welcome to the Student Council Support System! ✨</b>

Alya, as the vice president of the student council, is ready to help you with various needs:

<b>🎓 Chat Services:</b>
• Have a casual chat with Alya for discussions and venting.
• <code>!ask [question]</code> - Ask Alya anything, can be about images or documents too.

<b>📚 Bot Features:</b>
• <code>/help</code> - Complete guide to bot features.
• <code>/stats</code> - See your interaction statistics with Alya.
• <code>/ping</code> - Check Alya's response speed.
• <code>/lang</code> - Change language preference (en/id).
• <code>/reset</code> - Start the conversation from the beginning.

<b>🔧 Utilities:</b>
• <code>!sauce [reply to image]</code> - Find the source of an anime/manga image.

Alya will do her best to help you! 💫

<i>Ah, and Alya will remember all our conversations... so don't say anything weird! 😤</i>"""