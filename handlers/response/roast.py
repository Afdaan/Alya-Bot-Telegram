"""
Bilingual response generator for the roast commands.
"""
from typing import Optional
from config.settings import DEFAULT_LANGUAGE

def get_roast_response(lang: str = DEFAULT_LANGUAGE, roast_text: Optional[str] = None, error: Optional[str] = None, username: Optional[str] = None) -> str:
    """
    Generates the final response for the roast command.

    Args:
        lang: The user's language ('id' or 'en').
        roast_text: The generated roast text.
        error: An error key if something went wrong.
        username: The username being roasted (for gitroast).

    Returns:
        A formatted response string.
    """
    if error:
        return _get_error_messages(lang, error, username)
    
    if roast_text:
        if lang == 'id':
            return f"Heh, dengerin nih, {username if username else 'bego'}!\n\n_{roast_text}_"
        else:
            return f"Heh, listen up, {username if username else 'dummy'}!\n\n_{roast_text}_"
    
    # Fallback for unknown errors
    return _get_error_messages(lang, 'unknown')

def get_usage_response(lang: str = DEFAULT_LANGUAGE, command: str = "roast") -> str:
    """
    Returns the usage instructions for !roast or !gitroast.
    """
    if command == 'roast':
        if lang == 'id':
            return "Mau aku roast? Cukup ketik `!roast`. Siap-siap mental ya~"
        else:
            return "You want me to roast you? Just type `!roast`. Prepare yourself~"
    
    if command == 'gitroast':
        if lang == 'id':
            return "Kasih aku username GitHub buat di-roast. Contoh: `!gitroast afdaan`"
        else:
            return "Give me a GitHub username to roast. Example: `!gitroast afdaan`"
    
    return "Something is wrong."


def _get_error_messages(lang: str = DEFAULT_LANGUAGE, error: str = "unknown", username: Optional[str] = None) -> str:
    """Internal function to get error messages."""
    messages = {
        'id': {
            'api_fail': "Lagi gak mood nge-roast. Servernya lagi ngambek, coba lagi nanti.",
            'not_found': f"Gak nemu user GitHub namanya '{username}'. Salah ketik kali, dasar ceroboh.",
            'no_activity': f"Aku coba nge-roast {username}, tapi dia gak punya aktivitas publik. Beneran ada orangnya gak sih?",
            'generic': "Eh... что?! Ada yang error nih... 😳\n\nB-bukan salahku! Sistemnya lagi bermasalah... дурак teknologi! 💫",
            'unknown': "Eh... что?! Error misterius detected... 😳\n\nKamu aman... untuk sekarang. дурак sistem! 💫"
        },
        'en': {
            'api_fail': "I'm not in the mood to roast. The server is throwing a tantrum, try again later.",
            'not_found': f"Couldn't find a GitHub user named '{username}'. Did you type it wrong, you careless fool?",
            'no_activity': f"I tried to roast {username}, but they have no public activity. Are they even real?",
            'generic': "Eh... что?! Something went wrong... 😳\n\nI-It's not my fault! The system is having issues... дурак technology! 💫",
            'unknown': "Eh... что?! A mysterious error occurred... 😳\n\nYou're safe... for now. дурак system! 💫"
        }
    }
    return messages.get(lang, messages[DEFAULT_LANGUAGE]).get(error, messages.get(lang, messages[DEFAULT_LANGUAGE])['unknown'])
