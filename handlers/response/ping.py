from typing import Literal, Optional

def get_ping_response(lang: Literal['id', 'en'], latency: Optional[float] = None) -> str:
    """
    Generates a ping response for the bot in the specified language.

    Args:
        lang: The language for the response ('id' or 'en').
        latency: The latency in milliseconds.

    Returns:
        The ping message string.
    """
    if latency is not None:
        if lang == 'id':
            return f"🏓 Pong! Latensi: {latency:.2f}ms\nAlya siap sedia buat kamu kok~ 💫"
        else:
            return f"🏓 Pong! Latency: {latency:.2f}ms\nAlya is ready for you~ 💫"
    
    if lang == 'id':
        return "🏓 Pong! Alya lagi on fire nih~ 💫"
    else:
        return "🏓 Pong! Alya is on fire~ 💫"