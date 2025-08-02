def reset_response(friendship_level: str = "stranger", language: str = None) -> str:
    """Generate a reset response for the bot based on relationship level and language.
    
    Args:
        friendship_level: Relationship level (close_friend, friend, acquaintance, or stranger)
        language: User language preference ('en' or 'id')
        
    Returns:
        Formatted reset response
    """
    if language == "en":
        if friendship_level == "close_friend":
            return "Alright, I've reset our conversation~ But of course I still remember who you are! ✨"
        elif friendship_level == "friend":
            return "Hmph! So you want to start over? Fine, I've reset our conversation! 😳"
        else:
            return "Our conversation has been reset. I-I hope we can talk better this time... n-not that I care or anything! 💫"
    else:  # Indonesian
        if friendship_level == "close_friend":
            return "Baiklah, aku sudah melupakan percakapan kita sebelumnya~ Tapi tentu saja aku masih ingat siapa kamu! ✨"
        elif friendship_level == "friend":
            return "Hmph! Jadi kamu ingin memulai dari awal? Baiklah, aku sudah reset percakapan kita! 😳"
        else:
            return "Percakapan kita sudah direset. A-aku harap kita bisa bicara lebih baik kali ini... b-bukan berarti aku peduli atau apa! 💫"
