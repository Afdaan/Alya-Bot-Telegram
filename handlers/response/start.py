from typing import Literal
from config.settings import DEFAULT_LANGUAGE


def get_start_response(lang: Literal['id', 'en'] = DEFAULT_LANGUAGE, username: str = "User") -> str:
    """
    Generates a start response for the bot in the specified language.

    Args:
        lang: The language for the response ('id' or 'en').
        username: The user's first name.

    Returns:
        The start message string.
    """
    if lang == 'id':
        return (
            f"<b>Hai, {username}-kun!</b>\n\n"
            "Alya di sini siap nemenin kamu ngobrol, bantuin tugas, atau sekadar curhat~ "
            "Jangan malu-malu, tanya aja apa pun ke Alya ya! ✨\n\n"
            "<i>Kalau bingung, ketik /help buat lihat semua fitur Alya.</i>"
        )
    else:
        return (
            f"<b>Hi, {username}-kun!</b>\n\n"
            "Alya is here to chat with you, help with your tasks, or just listen to you vent~ "
            "Don't be shy, just ask Alya anything! ✨\n\n"
            "<i>If you're confused, type /help to see all of Alya's features.</i>"
        )