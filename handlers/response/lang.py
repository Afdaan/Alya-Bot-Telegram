"""
Bilingual response generator for the /lang command.

Provides language preference settings and confirmation responses with
support for Indonesian (id) and English (en) languages.
"""
from typing import Optional
from config.settings import DEFAULT_LANGUAGE


def get_lang_response(
    lang: str = DEFAULT_LANGUAGE,
    new_lang: Optional[str] = None
) -> str:
    """Generate response for /lang command with language preference settings.

    Args:
        lang: Current language for the response message ('id' or 'en')
        new_lang: The language code if successfully changed ('id' or 'en')

    Returns:
        str: Formatted HTML response with language settings or confirmation
    """
    if new_lang:
        # Language was successfully changed
        if new_lang == 'id':
            return (
                "✨ <b>Bahasa berhasil diubah!</b>\n\n"
                "Pengaturan bahasa sekarang adalah: <code>Bahasa Indonesia</code>\n\n"
                "Semua respons dari Alya akan dalam Bahasa Indonesia. "
                "Kamu bisa mengubah kembali dengan <code>/lang en</code> 💫"
            )
        else:
            return (
                "✨ <b>Language changed successfully!</b>\n\n"
                "Current language setting: <code>English</code>\n\n"
                "All responses from Alya will be in English. "
                "You can change back with <code>/lang id</code> 💫"
            )
    else:
        # Show current language setting (no change)
        if lang == 'id':
            return (
                "<b>⚙️ Pengaturan Bahasa</b>\n\n"
                "Bahasa saat ini: <code>Bahasa Indonesia</code> 🇮🇩\n\n"
                "<b>Untuk mengubah bahasa:</b>\n"
                "• <code>/lang en</code> - Ubah ke English 🇬🇧\n"
                "• <code>/lang id</code> - Tetap Bahasa Indonesia 🇮🇩\n\n"
                "Alya akan merespons dalam bahasa pilihan mu ✨"
            )
        else:
            return (
                "<b>⚙️ Language Settings</b>\n\n"
                "Current language: <code>English</code> 🇬🇧\n\n"
                "<b>To change language:</b>\n"
                "• <code>/lang en</code> - Keep English 🇬🇧\n"
                "• <code>/lang id</code> - Switch to Bahasa Indonesia 🇮🇩\n\n"
                "Alya will respond in your preferred language ✨"
            )