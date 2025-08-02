def start_response(username: str = "user", language: str = None) -> str:
    """Generate a start response for the bot."""
    
    if language == "en":
        return f"Hi, {username}-kun!\n\nAlya is here ready to chat with you, help with tasks, or just listen to your stories~ Don't be shy, ask Alya anything! ✨\n\nIf you're confused, type /help to see all of Alya's features."
    else:  # Indonesian
        return f"Hai, {username}-kun!\n\nAlya di sini siap nemenin kamu ngobrol, bantuin tugas, atau sekadar curhat~ Jangan malu-malu, tanya aja apa pun ke Alya ya! ✨\n\nKalau bingung, ketik /help buat lihat semua fitur Alya."