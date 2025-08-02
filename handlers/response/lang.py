# /home/afdaan/alya-telegram-new/handlers/response/lang.py
from typing import Literal

def get_lang_response(lang: Literal['id', 'en'], usage: bool = False, new_lang: str = None) -> str:
    """
    Returns the response for the /lang command.

    Args:
        lang: The language to use for the response.
        usage: If True, returns the usage instructions.
        new_lang: The new language that has been set.

    Returns:
        The response string.
    """
    if usage:
        if lang == 'id':
            return (
                "Gunakan perintah ini untuk mengatur preferensi bahasa Anda.\n\n"
                "Contoh:\n"
                "`/lang en` untuk mengubah bahasa ke Bahasa Inggris.\n"
                "`/lang id` untuk mengubah bahasa ke Bahasa Indonesia."
            )
        else:
            return (
                "Use this command to set your language preference.\n\n"
                "Example:\n"
                "`/lang en` to change the language to English.\n"
                "`/lang id` to change the language to Indonesian."
            )
    
    if new_lang:
        if lang == 'id':
            return f"Bahasa telah diubah ke Bahasa Indonesia. ✨"
        else:
            return f"Language has been changed to English. ✨"
    
    # This part should ideally not be reached if logic in commands.py is correct
    if lang == 'id':
        return "Terjadi kesalahan saat mengubah bahasa. Silakan coba lagi."
    else:
        return "An error occurred while changing the language. Please try again."
