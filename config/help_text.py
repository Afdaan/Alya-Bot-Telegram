"""Help text configuration for Alya Bot."""

HELP_TEXT = {
    "id": {
        "header": "Bantuan Alya Bot 🌸",
        "chat": {
            "title": "🗣️ Chat Commands",
            "content": [
                "• Langsung chat (personal): Tulis pesan apa saja",
                "• Dalam grup: Awali dengan `!ai` atau mention (@AlyaBot)",
            ]
        },
        "utility": {
            "title": "🔎 Utility Commands",
            "content": [
                "• `/search [query]` - Mencari informasi di web",
                "• `/search -d [query]` - Mencari detail",
                "• `!trace` - Analisis gambar (reply ke gambar)",
                "• `!sauce` - Cari sumber gambar (reply ke gambar)",
                "• `!ocr` - Ekstrak teks dari gambar",
            ]
        },
        "fun": {
            "title": "🎭 Fun Commands", 
            "content": [
                "• `/roast @user` - Roast user",
                "• `/gitroast user/repo` - Roast GitHub repo",
                "• `/persona` - Ganti kepribadian Alya",
            ]
        },
        "settings": {
            "title": "⚙️ Settings",
            "content": [
                "• `/memory` - Lihat informasi memori",
                "• `/reset` - Reset konteks percakapan",
                "• `/lang` - Ganti bahasa (id/en)",
            ]
        },
        "features": {
            "title": "💫 Fitur Baru",
            "content": [
                "• RAG Memory System - Alya bisa ingat percakapan sebelumnya",
                "• Russian Expressions - Ngomong pake kata Rusia kalo lagi emosi",
                "• Better Persona - Kepribadian yang lebih natural",
            ]
        },
        "footer": "Semua perintah yang dimulai dengan `!` bisa juga digunakan dengan `/`.\n\nCoba ajak aku bicara sekarang!"
    }
}
