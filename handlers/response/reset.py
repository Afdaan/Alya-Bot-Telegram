"""
Response formatters for the reset command.
"""

def get_reset_response(lang: str = "id", success: bool = False) -> str:
    """
    Generates a response for the reset command.

    Args:
        lang: The language for the response ('id' or 'en').
        success: Whether the reset was successful.

    Returns:
        The response message.
    """
    if success:
        text = {
            "id": (
                "Riwayat percakapanmu telah diatur ulang. "
                "A-aku tidak akan mengingat apa pun tentang percakapan kita sebelumnya... "
                "B-bukan berarti aku peduli sih... 😳"
            ),
            "en": (
                "Your conversation history has been reset. "
                "I-I won't remember anything about our previous conversations... "
                "N-not that I cared anyway... 😳"
            ),
        }
    else:
        text = {
            "id": (
                "Gagal mengatur ulang riwayat percakapan. "
                "Sistem memoriku sedang tidak mau bekerja sama... Coba lagi nanti ya."
            ),
            "en": (
                "Failed to reset conversation history. "
                "My memory system isn't cooperating... Please try again later."
            ),
        }
    return text.get(lang, text["id"])

def get_reset_confirmation_response(lang: str = "id") -> str:
    """
    Generates a confirmation message for the reset command.

    Args:
        lang: The language for the response ('id' or 'en').

    Returns:
        The confirmation message.
    """
    text = {
        "id": (
            "Hah? Kamu yakin mau mengatur ulang riwayat percakapan kita? "
            "Semua yang pernah kita bicarakan akan hilang selamanya... "
            "Kalau kamu yakin, kirim <code>/reset confirm</code>. "
            "B-bukan berarti aku akan merindukan percakapan kita atau apa..."
        ),
        "en": (
            "Huh? Are you sure you want to reset our conversation history? "
            "Everything we've ever talked about will be gone forever... "
            "If you're sure, send <code>/reset confirm</code>. "
            "I-it's not like I'll miss our conversations or anything..."
        ),
    }
    return text.get(lang, text["id"])
