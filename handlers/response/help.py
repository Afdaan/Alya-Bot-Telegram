from core.language_manager import language_manager

def help_response(username: str = "user", language: str = None) -> str:
    """Generate a help response for the bot."""
    
    # Base templates for each language
    if not language or language == "id":
        template = """<b>{help_title}</b>

{help_description}

<b>🎓 Layanan Chat:</b>
• Chat natural dengan Alya untuk diskusi dan konsultasi
• <code>!ai</code> - Tanya jawab dengan Alya di group

<b>📚 Fitur Bot:</b>
• <code>/help</code> - Panduan lengkap fitur bot
• <code>/stats</code> - Progress relationship dengan Alya
• <code>/reset</code> - Mulai percakapan dari awal
• <code>/lang [id|en]</code> - Ubah bahasa bot

<b>🔧 Utilitas Sekolah:</b>
• <code>!sauce [image]</code> - Pencarian sumber artwork

<b>🎭 Fitur Menyenangkan:</b>
• <code>!roast [target]</code> - Kritik pedas ala Alya
• <code>!gitroast [username]</code> - Roasting profil GitHub

Alya akan berusaha sebaik mungkin membantu {username}-kun! 💫

<i>Ah, dan Alya akan mengingat semua percakapan kita... jadi jangan bilang hal yang aneh-aneh ya! 😤</i>"""
    else:  # English
        template = """<b>{help_title}</b>

{help_description}

<b>🎓 Chat Services:</b>
• Natural chat with Alya for discussions and consultations
• <code>!ai</code> - Q&A with Alya in groups

<b>📚 Bot Features:</b>
• <code>/help</code> - Complete feature guide
• <code>/stats</code> - Relationship progress with Alya
• <code>/reset</code> - Start conversation from scratch
• <code>/lang [id|en]</code> - Change bot language

<b>🔧 School Utilities:</b>
• <code>!sauce [image]</code> - Artwork source search

<b>🎭 Fun Features:</b>
• <code>!roast [target]</code> - Sharp criticism Alya-style
• <code>!gitroast [username]</code> - GitHub profile roasting

Alya will do her best to help {username}-kun! 💫

<i>Ah, and Alya will remember all our conversations... so don't say weird things! 😤</i>"""
    
    help_title = language_manager.get_text("commands.help_title", language)
    help_description = language_manager.get_text("commands.help_description", language, username=username)
    
    return template.format(
        help_title=help_title,
        help_description=help_description,
        username=username
    )