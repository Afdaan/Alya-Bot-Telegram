# /home/afdaan/alya-telegram-new/handlers/response/lang.py
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
        else: # en
            return "✨ Language successfully changed to English."
    else:
        # This is the usage message
        if lang == 'id':
            return (
                "Pengaturan bahasa saat ini adalah: `Indonesia`\n\n"
                "Untuk mengubah, gunakan: `/lang en` atau `/lang id`"
            )
        else: # en
            return (
                "Current language setting is: `English`\n\n"
                "To change, use: `/lang en` or `/lang id`"
            )
