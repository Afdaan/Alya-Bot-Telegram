# /home/afdaan/alya-telegram-new/handlers/response/system.py
from typing import Literal

def get_system_error_response(lang: Literal['id', 'en']) -> str:
    """
    Returns a generic system error message in the specified language.

    Args:
        lang: The language for the response ('id' or 'en').

    Returns:
        The error message string.
    """
    if lang == 'id':
        return "Maaf, terjadi kesalahan. Tim kami telah diberitahu dan akan segera menanganinya. Coba lagi nanti ya. 🙏"
    else:
        return "Sorry, an error occurred. Our team has been notified and will handle it shortly. Please try again later. 🙏"
