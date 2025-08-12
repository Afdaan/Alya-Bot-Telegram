"""
Bilingual response generator for the /lang command.
"""
from typing import Optional

def get_lang_response(lang: str, new_lang: Optional[str] = None) -> str:
    """
    Generates the response for the /lang command.

    Args:
        lang: The language for the response message ('id' or 'en').
        new_lang: The new language if it was successfully changed.

    Returns:
        A formatted response string.
    """
    if new_lang:
        if new_lang == 'id':
            return "✨ Bahasa berhasil diubah ke Bahasa Indonesia."
        else:
            return "✨ Language successfully changed to English."
    else:
        if lang == 'id':
            return (
                "Pengaturan bahasa saat ini adalah: <code>Indonesia</code>\n\n"
                "Untuk mengubah, gunakan: <code>/lang en</code> atau <code>/lang id</code>"
            )
        else:
            return (
                "Current language setting is: <code>English</code>\n\n"
                "To change, use: <code>/lang en</code> or <code>/lang id</code>"
            )