"""
Response formatters for search command results.
Clean separation of display logic from command handling.
"""
import html
import random
from typing import List, Dict, Any, Optional, Tuple

from utils.search_engine import SearchResult, get_google_search_url

def search_usage_response() -> str:
    return (
        "Hmph! Kamu harus memberikan kata kunci yang ingin dicari!\n\n"
        "<b>Format:</b>\n"
        "• <code>/search kata kunci</code> - Pencarian umum\n"
        "• <code>/search -p nama orang</code> - Cari profil/orang\n"
        "• <code>/search -p @username</code> - Cari username di sosial media\n"
        "• <code>/search -n topik berita</code> - Cari berita terbaru\n"
        "• <code>/search -i deskripsi gambar</code> - Cari gambar\n\n"
        "<b>Contoh:</b>\n"
        "<code>/search Roshidere anime</code>\n"
        "<code>/search -p Sayaka Kobayashi</code>\n"
        "<code>/search -n peristiwa terkini</code>\n\n"
        "<i>~A-aku akan membantu mencarikan informasi untukmu... bukan karena aku peduli atau apa...~</i> 💫"
    )

def search_error_response(error_message: str = "") -> str:
    error_responses = [
        "Maaf, aku tidak bisa menyelesaikan pencarian... s-sistem Google-nya bermasalah... что? 😳",
        "A-aku tidak berhasil mencarikan hasilnya... Google API-nya tidak merespon dengan benar...",
        "Hmph! Google API-nya tidak mau bekerja sama denganku! Maaf ya, coba lagi nanti...",
        "E-error! Pencarian tidak bisa diselesaikan... API key-nya mungkin sedang bermasalah..."
    ]
    response = random.choice(error_responses)
    if error_message and len(error_message) < 50:
        debug_info = f"\n\n<i>Debug info: {html.escape(error_message)}</i>"
    else:
        debug_info = ""
    return f"{response}{debug_info}\n\n<i>~Silakan coba lagi nanti ya~</i> 💫"

def _get_alya_reaction(search_type: Optional[str], has_results: bool) -> str:
    if not has_results:
        no_results = [
            "Hmph! Aku tidak menemukan apa-apa. Coba kata kunci yang lebih spesifik!",
            "M-maaf, aku sudah mencoba mencari tapi tidak menemukan hasil apapun...",
            "Aku tidak menemukan apapun! Kata kuncinya terlalu aneh kali ya? 😳",
            "B-bukannya aku tidak berusaha, tapi memang tidak ada hasil sama sekali!"
        ]
        return random.choice(no_results)
    reactions = {
        "profile": [
            "I-ini profil yang kutemukan! Semoga membantu... bukan berarti aku mau membantumu atau apa...",
            "Etto... ini beberapa profil yang mungkin kamu cari...",
            "Hmph! Dasar stalker! Tapi ini beberapa profil yang kutemukan~",
        ],
        "news": [
            "Ini berita terbaru yang berhasil kutemukan! Jangan lupa membacanya dengan kritis ya!",
            "Berita terbaru sudah kutemukan untukmu! Semoga informatif~",
            "I-ini berita yang berkaitan dengan pencarianmu... b-bukannya aku update berita untukmu atau apa..."
        ],
        "image": [
            "I-ini gambar yang kamu cari... j-jangan yang aneh-aneh ya!",
            "Hmph! Ini gambar-gambar yang kutemukan. Jangan sampai salah pakai!",
            "A-aku sudah mencarikan gambarnya... S-semoga sesuai dengan yang kamu butuhkan..."
        ],
        "general": [
            "I-ini hasil pencarian yang kutemukan... mudah-mudahan membantu!",
            "Hmph! Pencarian selesai! Aku harap ini yang kamu cari~",
            "B-bukan berarti aku senang membantumu, t-tapi ini hasil pencariannya..."
        ]
    }
    search_key = search_type if search_type in reactions else "general"
    return random.choice(reactions[search_key])

def _get_username_tips(query: str, clean_query: str) -> Tuple[List[str], str]:
    google_search_terms = f"{clean_query} profile social media account"
    google_url = get_google_search_url(google_search_terms)
    tips = []
    if '@' in query:
        tips.append(f"• Coba tanpa simbol @ (<code>/search -p {html.escape(clean_query)}</code>)")
    if len(clean_query) >= 3:
        popular_platforms = [
            ("Twitter", "twitter"), 
            ("GitHub", "github"),
            ("Instagram", "instagram"),
            ("LinkedIn", "linkedin")
        ]
        platform_examples = []
        for name, platform in random.sample(popular_platforms, min(2, len(popular_platforms))):
            platform_examples.append(
                f"<code>/search -p {html.escape(clean_query)} {platform}</code>"
            )
        tips.append(f"• Coba tambahkan platform spesifik: {' atau '.join(platform_examples)}")
    tips.append(f"• <a href=\"{html.escape(google_url)}\">Cari langsung di Google</a>")
    return tips, google_url

def format_search_results(
    query: str, 
    results: List[SearchResult], 
    search_type: Optional[str] = None,
    show_username_tip: bool = False
) -> str:
    clean_query = query.lstrip('@')
    escaped_query = html.escape(query)
    if search_type == "profile":
        header_text = "Hasil pencarian profil untuk"
    elif search_type == "news":
        header_text = "Hasil pencarian berita untuk"
    elif search_type == "image":
        header_text = "Hasil pencarian gambar untuk"
    else:
        header_text = "Hasil pencarian untuk"
    message = [f"<b>{header_text}:</b> <i>{escaped_query}</i>"]
    if not results:
        message.append(_get_alya_reaction(search_type, False))
        if search_type == "profile":
            tips, google_url = _get_username_tips(query, clean_query)
            if tips:
                message.append("<b>Tips pencarian profil:</b>")
                message.append("\n".join(tips))
        return "\n\n".join(message)
    formatted_results = []
    for i, result in enumerate(results, 1):
        title = html.escape(result.title)
        snippet = html.escape(result.snippet or "")
        url = html.escape(result.link)
        displayed_link = html.escape(result.displayed_link or "")
        if (result.result_type == "profile" or search_type == "profile"):
            result_text = (
                f"{i}. <b><a href=\"{url}\">{title}</a></b> "
                f"<i>({displayed_link})</i>\n"
                f"{snippet}"
            )
        elif (result.result_type == "news" or search_type == "news"):
            result_text = (
                f"{i}. <b><a href=\"{url}\">{title}</a></b>\n"
                f"<i>{displayed_link}</i>\n"
                f"{snippet}"
            )
        elif (result.result_type == "image" or search_type == "image"):
            thumbnail_html = ""
            if result.thumbnail:
                thumbnail_html = f'<a href="{url}">🖼️</a> '
            result_text = (
                f"{i}. {thumbnail_html}<b><a href=\"{url}\">{title}</a></b>\n"
                f"{snippet}"
            )
        else:
            result_text = (
                f"{i}. <b><a href=\"{url}\">{title}</a></b>\n"
                f"{snippet}"
            )
        formatted_results.append(result_text)
    message.extend(formatted_results)
    if search_type == "profile" and show_username_tip:
        tips, google_url = _get_username_tips(query, clean_query)
        if tips:
            message.append("<b>Tip lainnya:</b>")
            message.append(tips[-1])
    footer = _get_alya_reaction(search_type, True)
    message.append(f"<i>~{footer}~</i>")
    return "\n\n".join(message)