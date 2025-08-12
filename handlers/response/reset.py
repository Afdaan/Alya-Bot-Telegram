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
            "Hah?! Kamu serius mau reset semua percakapan kita? "
            "Semua obrolan kita yang sudah keren itu bakal hilang begitu saja... "
            "Kalau kamu yakin banget, kirim <code>/reset confirm</code>, ya. "
            "Tapi, jangan salah, aku juga nggak peduli kok... bukan berarti aku akan kangen atau apa gitu!"

        ),
        "en": (
            "Wh-what?! You really want to reset all our conversations? "
            "All our awesome chats will be gone forever... "
            "If you're absolutely sure, just send <code>/reset confirm</code>. "
            "Not that I care or anything... It's not like I’ll miss our talks or whatever!"
        ),
    }
    return text.get(lang, text["id"])
