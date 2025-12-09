"""
Response formatters for the reset command.
"""
from config.settings import DEFAULT_LANGUAGE

def get_reset_response(lang: str = DEFAULT_LANGUAGE, success: bool = False) -> str:
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
                "✅ <b>Reset Berhasil!</b>\n\n"
                "Riwayat percakapan sudah direset~ "
                "Sekarang kita bisa mulai fresh lagi! 💫\n\n"
                "Hai lagi! Kenalan lagi yuk~ 😊"
            ),
            "en": (
                "✅ <b>Reset Successful!</b>\n\n"
                "Conversation history has been reset~ "
                "Now we can start fresh again! 💫\n\n"
                "Hello again! Let's get to know each other again~ 😊"
            ),
        }
    else:
        text = {
            "id": (
                "❌ <b>Reset Gagal</b>\n\n"
                "Ada masalah saat reset riwayat percakapan. "
                "Coba lagi nanti ya~ 😅"
            ),
            "en": (
                "❌ <b>Reset Failed</b>\n\n"
                "There was a problem resetting conversation history. "
                "Please try again later~ 😅"
            ),
        }
    return text.get(lang, text[DEFAULT_LANGUAGE])

def get_reset_confirmation_response(lang: str = DEFAULT_LANGUAGE) -> str:
    """
    Generates a confirmation message for the reset command with buttons.

    Args:
        lang: The language for the response ('id' or 'en').

    Returns:
        The confirmation message.
    """
    text = {
        "id": (
            "💭 <b>Konfirmasi Reset</b>\n\n"
            "Kamu yakin mau reset semua riwayat percakapan kita? "
            "Semua kenangan dan konteks percakapan akan hilang lho~ 😳\n\n"
            "Pilih salah satu tombol di bawah:"
        ),
        "en": (
            "💭 <b>Reset Confirmation</b>\n\n"
            "Are you sure you want to reset all our conversation history? "
            "All memories and conversation context will be lost~ 😳\n\n"
            "Choose one of the buttons below:"
        )
    }
    return text.get(lang, text[DEFAULT_LANGUAGE])

def get_reset_cancel_response(lang: str = DEFAULT_LANGUAGE) -> str:
    """
    Generates a cancellation message for the reset command.

    Args:
        lang: The language for the response ('id' or 'en').

    Returns:
        The cancellation message.
    """
    text = {
        "id": (
            "😌 <b>Reset Dibatalkan</b>\n\n"
            "Oke, riwayat percakapan kita tetap aman~ "
            "Alya masih ingat semua obrolan kita kok! ✨"
        ),
        "en": (
            "😌 <b>Reset Cancelled</b>\n\n"
            "Okay, our conversation history is safe~ "
            "Alya still remembers all our chats! ✨"
        )
    }
    return text.get(lang, text[DEFAULT_LANGUAGE])