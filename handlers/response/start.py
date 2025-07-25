def start_response(username: str = "user") -> str:
    """Generate a start response for the bot."""
    return (
        f"<b>Hai, {username}-kun!</b>\n\n"
        "Alya di sini siap nemenin kamu ngobrol, bantuin tugas, atau sekadar curhat~ "
        "Jangan malu-malu, tanya aja apa pun ke Alya ya! ✨\n\n"
        "<i>Kalau bingung, ketik /help buat lihat semua fitur Alya.</i>"
    )