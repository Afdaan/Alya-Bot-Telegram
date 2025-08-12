from typing import Literal

def get_system_error_response(lang: Literal['id', 'en']) -> str:
    """
    Returns an Alya-style system error message in the specified language.

    Args:
        lang: The language for the response ('id' or 'en').

    Returns:
        The error message string with Alya's tsundere personality.
    """
    if lang == 'id':
        return "Eh... что?! Ada yang error nih... 😳\n\nB-bukan salahku ya! Sistemnya lagi bermasalah... дурак teknologi ini! 💫\n\nCoba lagi nanti, okay? A-aku akan bantu fix ini... tapi bukan karena peduli sama kamu atau apa! 🌸"
    else:
        return "Eh... что?! Something went wrong... 😳\n\nI-It's not my fault! The system is having issues... дурак technology! 💫\n\nTry again later, okay? I-I'll help fix this... but it's not like I care about you or anything! 🌸"
