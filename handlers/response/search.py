"""
Response formatters for search command results.
Clean separation of display logic from command handling.
"""
import html
import random
from typing import List, Dict, Any, Optional, Tuple

from utils.search_engine import SearchResult, get_google_search_url

def search_usage_response(language: str = None) -> str:
    """Generate search usage response based on language."""
    
    if language == "en":
        return (
            "Hmph! You need to provide keywords to search for!\n\n"
            "<b>Format:</b>\n"
            "• <code>/search keywords</code> - General search\n"
            "• <code>/search -p person name</code> - Search profiles/people\n"
            "• <code>/search -p @username</code> - Search username on social media\n"
            "• <code>/search -n news topic</code> - Search latest news\n"
            "• <code>/search -i image description</code> - Search images\n\n"
            "<b>Examples:</b>\n"
            "• <code>/search machine learning</code>\n"
            "• <code>/search -p Elon Musk</code>\n"
            "• <code>/search -n Indonesia news</code>\n"
            "• <code>/search -i cute anime girl</code>\n\n"
            "<i>Don't think Alya likes helping you search! It's just... Alya's duty as student council vice president! 😤</i>"
        )
    else:  # Indonesian
        return (
            "Hmph! Kamu harus memberikan kata kunci yang ingin dicari!\n\n"
            "<b>Format:</b>\n"
            "• <code>/search kata kunci</code> - Pencarian umum\n"
            "• <code>/search -p nama orang</code> - Cari profil/orang\n"
            "• <code>/search -p @username</code> - Cari username di sosial media\n"
            "• <code>/search -n topik berita</code> - Cari berita terbaru\n"
            "• <code>/search -i deskripsi gambar</code> - Cari gambar\n\n"
            "<b>Contoh:</b>\n"
            "• <code>/search machine learning</code>\n"
            "• <code>/search -p Elon Musk</code>\n" 
            "• <code>/search -n berita Indonesia</code>\n"
            "• <code>/search -i anime girl lucu</code>\n\n"
            "<i>Jangan kira Alya suka bantu kamu cari-cari! Ini cuma... tugas Alya sebagai wakil ketua OSIS! 😤</i>"
        )

def search_error_response(error_message: str = "", language: str = None) -> str:
    if language == "en":
        error_responses = [
            "Sorry, I couldn't complete the search... t-the Google system is having problems... что? 😳",
            "I-I couldn't find the results... Google API isn't responding properly...",
            "Hmph! Google API won't cooperate with me! Sorry, please try again later...",
            "E-error! Search couldn't be completed... the API key might be having problems..."
        ]
        try_again_text = "~Please try again later~"
    else:  # Indonesian
        error_responses = [
            "Maaf, aku tidak bisa menyelesaikan pencarian... s-sistem Google-nya bermasalah... что? 😳",
            "A-aku tidak berhasil mencarikan hasilnya... Google API-nya tidak merespon dengan benar...",
            "Hmph! Google API-nya tidak mau bekerja sama denganku! Maaf ya, coba lagi nanti...",
            "E-error! Pencarian tidak bisa diselesaikan... API key-nya mungkin sedang bermasalah..."
        ]
        try_again_text = "~Silakan coba lagi nanti ya~"
    
    response = random.choice(error_responses)
    if error_message and len(error_message) < 50:
        debug_info = f"\n\n<i>Debug info: {html.escape(error_message)}</i>"
    else:
        debug_info = ""
    return f"{response}{debug_info}\n\n<i>{try_again_text}</i> 💫"

def _get_alya_reaction(search_type: Optional[str], has_results: bool, language: str = None) -> str:
    if not has_results:
        if language == "en":
            no_results = [
                "Hmph! I couldn't find anything. Try more specific keywords!",
                "S-sorry, I tried searching but couldn't find any results...",
                "I couldn't find anything! Maybe the keywords are too weird? 😳",
                "I-it's not that I didn't try hard, but there really are no results at all!"
            ]
        else:  # Indonesian
            no_results = [
                "Hmph! Aku tidak menemukan apa-apa. Coba kata kunci yang lebih spesifik!",
                "M-maaf, aku sudah mencoba mencari tapi tidak menemukan hasil apapun...",
                "Aku tidak menemukan apapun! Kata kuncinya terlalu aneh kali ya? 😳",
                "B-bukannya aku tidak berusaha, tapi memang tidak ada hasil sama sekali!"
            ]
        return random.choice(no_results)
    
    if language == "en":
        reactions = {
            "profile": [
                "T-these are the profiles I found! I hope it helps... not that I want to help you or anything...",
                "Etto... these are some profiles you might be looking for...",
                "Hmph! What a stalker! But these are the profiles I found~",
            ],
            "news": [
                "These are the latest news I found! Don't forget to read them critically!",
                "Latest news found for you! Hope it's informative~",
                "T-these are news related to your search... n-not that I'm updating news for you or anything..."
            ],
            "image": [
                "T-these are the images you're looking for... d-don't use them for weird things!",
                "Hmph! These are the images I found. Don't misuse them!",
                "I-I've found the images for you... I-I hope they match what you need..."
            ],
            "general": [
                "T-these are the search results I found... I hope they help!",
                "Hmph! Search completed! I hope this is what you're looking for~",
                "I-it's not that I enjoy helping you, b-but here are the search results..."
            ]
        }
    else:  # Indonesian
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

def _get_username_tips(query: str, clean_query: str, language: str = None) -> Tuple[List[str], str]:
    google_search_terms = f"{clean_query} profile social media account"
    google_url = get_google_search_url(google_search_terms)
    tips = []
    
    if '@' in query:
        if language == "en":
            tips.append(f"• Try without @ symbol (<code>/search -p {html.escape(clean_query)}</code>)")
        else:  # Indonesian
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
        
        if language == "en":
            tips.append(f"• Try adding platform name: {', '.join(platform_examples)}")
        else:  # Indonesian
            tips.append(f"• Coba tambahkan nama platform: {', '.join(platform_examples)}")
    
    # Add Google search link
    google_link_text = "Search directly on Google" if language == "en" else "Cari langsung di Google"
    tips.append(f"• <a href=\"{html.escape(google_url)}\">{google_link_text}</a>")
    return tips, google_url

def format_search_results(
    query: str, 
    results: List[SearchResult], 
    search_type: Optional[str] = None,
    show_username_tip: bool = False,
    language: str = None
) -> str:
    clean_query = query.lstrip('@')
    escaped_query = html.escape(query)
    
    # Choose header text based on language
    if language == "en":
        if search_type == "profile":
            header_text = "Profile search results for"
        elif search_type == "news":
            header_text = "News search results for"
        elif search_type == "image":
            header_text = "Image search results for"
        else:
            header_text = "Search results for"
    else:  # Indonesian
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
        message.append(_get_alya_reaction(search_type, False, language))
        if search_type == "profile":
            tips, google_url = _get_username_tips(query, clean_query, language)
            if tips:
                tips_header = "Profile search tips:" if language == "en" else "Tips pencarian profil:"
                message.append(f"<b>{tips_header}</b>")
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
        tips, google_url = _get_username_tips(query, clean_query, language)
        if tips:
            tip_header = "Other tips:" if language == "en" else "Tip lainnya:"
            message.append(f"<b>{tip_header}</b>")
            message.append(tips[-1])
    footer = _get_alya_reaction(search_type, True, language)
    message.append(f"<i>~{footer}~</i>")
    return "\n\n".join(message)