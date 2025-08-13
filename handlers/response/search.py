"""
Response formatters for search command results.
Clean separation of display logic from command handling.
"""
import html
import random
from typing import List, Optional, Tuple
from config.settings import DEFAULT_LANGUAGE
from utils.search_engine import SearchResult, get_google_search_url


def search_usage_response(lang: str = DEFAULT_LANGUAGE) -> str:
    """
    Generates a response explaining how to use the search command.

    Args:
        lang: The language for the response ('id' or 'en').

    Returns:
        The usage instructions message.
    """
    text = {
        "id": (
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
            "<i>~A-aku akan membantu mencarikan informasi untukmu... "
            "bukan karena aku peduli atau apa...~</i> 💫"
        ),
        "en": (
            "Hmph! You need to provide a keyword to search for!\n\n"
            "<b>Format:</b>\n"
            "• <code>/search keyword</code> - General search\n"
            "• <code>/search -p person's name</code> - Search for a profile/person\n"
            "• <code>/search -p @username</code> - Search for a username on social media\n"
            "• <code>/search -n news topic</code> - Search for the latest news\n"
            "• <code>/search -i image description</code> - Search for an image\n\n"
            "<b>Examples:</b>\n"
            "<code>/search Roshidere anime</code>\n"
            "<code>/search -p Sayaka Kobayashi</code>\n"
            "<code>/search -n current events</code>\n\n"
            "<i>~I-I'll help you find the information... "
            "not because I care or anything...~</i> 💫"
        ),
    }
    return text.get(lang, text[DEFAULT_LANGUAGE])


def search_error_response(lang: str = DEFAULT_LANGUAGE, error_message: str = "") -> str:
    """
    Generates a response for a search error.

    Args:
        lang: The language for the response ('id' or 'en').
        error_message: Optional debug error message.

    Returns:
        The formatted error message.
    """
    responses = {
        "id": [
            "Maaf, aku tidak bisa menyelesaikan pencarian... s-sistem Google-nya bermasalah... что? 😳",
            "A-aku tidak berhasil mencarikan hasilnya... Google API-nya tidak merespon dengan benar...",
            "Hmph! Google API-nya tidak mau bekerja sama denganku! Maaf ya, coba lagi nanti...",
            "E-error! Pencarian tidak bisa diselesaikan... API key-nya mungkin sedang bermasalah..."
        ],
        "en": [
            "Sorry, I couldn't complete the search... t-the Google system is having issues... что? 😳",
            "I-I couldn't fetch the results... The Google API isn't responding correctly...",
            "Hmph! The Google API won't cooperate with me! Sorry, try again later...",
            "E-error! The search could not be completed... The API key might be having issues..."
        ]
    }
    footer = {
        "id": "<i>~Silakan coba lagi nanti ya~</i> 💫",
        "en": "<i>~Please try again later~</i> 💫"
    }
    
    chosen_response = random.choice(responses.get(lang, responses[DEFAULT_LANGUAGE]))
    debug_info = ""
    if error_message and len(error_message) < 50:
        debug_info = f"\n\n<i>Debug info: {html.escape(error_message)}</i>"
        
    return f"{chosen_response}{debug_info}\n\n{footer.get(lang, footer[DEFAULT_LANGUAGE])}"


def _get_alya_reaction(search_type: Optional[str], has_results: bool, lang: str) -> str:
    """
    Gets a mood-based reaction from Alya for the search results.

    Args:
        search_type: The type of search performed (e.g., 'profile', 'news').
        has_results: Whether there were any results.
        lang: The language for the response.

    Returns:
        A reaction string.
    """
    if not has_results:
        no_results = {
            "id": [
                "Hmph! Aku tidak menemukan apa-apa. Coba kata kunci yang lebih spesifik!",
                "M-maaf, aku sudah mencoba mencari tapi tidak menemukan hasil apapun...",
                "Aku tidak menemukan apapun! Kata kuncinya terlalu aneh kali ya? 😳",
                "B-bukannya aku tidak berusaha, tapi memang tidak ada hasil sama sekali!"
            ],
            "en": [
                "Hmph! I didn't find anything. Try a more specific keyword!",
                "S-sorry, I tried searching but couldn't find any results...",
                "I found nothing! Is the keyword too weird? 😳",
                "I-it's not that I didn't try, but there were really no results at all!"
            ]
        }
        return random.choice(no_results.get(lang, no_results[DEFAULT_LANGUAGE]))

    reactions = {
        "id": {
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
        },
        "en": {
            "profile": [
                "H-here are the profiles I found! Hope it helps... not that I wanted to help you or anything...",
                "Umm... here are some profiles you might be looking for...",
                "Hmph! You stalker! But here are the profiles I found~",
            ],
            "news": [
                "Here's the latest news I managed to find! Don't forget to read it critically!",
                "I've found the latest news for you! Hope it's informative~",
                "T-this is the news related to your search... n-not that I'm keeping you updated or anything..."
            ],
            "image": [
                "H-here are the images you were looking for... d-don't do anything weird with them!",
                "Hmph! Here are the images I found. Don't use them incorrectly!",
                "I-I've found the pictures... I-I hope they are what you need..."
            ],
            "general": [
                "H-here are the search results I found... hope they help!",
                "Hmph! Search complete! I hope this is what you were looking for~",
                "I-it's not that I'm happy to help you, b-but here are the search results..."
            ]
        }
    }
    
    lang_reactions = reactions.get(lang, reactions[DEFAULT_LANGUAGE])
    search_key = search_type if search_type in lang_reactions else "general"
    return random.choice(lang_reactions[search_key])


def _get_username_tips(query: str, clean_query: str, lang: str) -> Tuple[List[str], str]:
    """
    Generates tips for profile searches, especially for usernames.

    Args:
        query: The original search query.
        clean_query: The query with '@' stripped.
        lang: The language for the response.

    Returns:
        A tuple containing a list of tips and the direct Google search URL.
    """
    google_search_terms = f"{clean_query} profile social media account"
    google_url = get_google_search_url(google_search_terms)
    tips = []
    
    tip_texts = {
        "id": {
            "no_symbol": "• Coba tanpa simbol @ (<code>/search -p {0}</code>)",
            "add_platform": "• Coba tambahkan platform spesifik: {0}",
            "search_google": "• <a href=\"{0}\">Cari langsung di Google</a>"
        },
        "en": {
            "no_symbol": "• Try without the @ symbol (<code>/search -p {0}</code>)",
            "add_platform": "• Try adding a specific platform: {0}",
            "search_google": "• <a href=\"{0}\">Search directly on Google</a>"
        }
    }
    
    lang_tips = tip_texts.get(lang, tip_texts[DEFAULT_LANGUAGE])

    if '@' in query:
        tips.append(lang_tips["no_symbol"].format(html.escape(clean_query)))
        
    if len(clean_query) >= 3:
        popular_platforms = [
            ("Twitter", "twitter"), 
            ("GitHub", "github"),
            ("Instagram", "instagram"),
            ("LinkedIn", "linkedin")
        ]
        platform_examples = []
        for _, platform in random.sample(popular_platforms, min(2, len(popular_platforms))):
            platform_examples.append(
                f"<code>/search -p {html.escape(clean_query)} {platform}</code>"
            )
        tips.append(lang_tips["add_platform"].format(' or '.join(platform_examples)))
        
    tips.append(lang_tips["search_google"].format(html.escape(google_url)))
    return tips, google_url


def format_search_results(
    query: str, 
    results: List[SearchResult], 
    search_type: Optional[str] = None,
    show_username_tip: bool = False,
    lang: str = DEFAULT_LANGUAGE
) -> str:
    """
    Formats the search results into a single message.

    Args:
        query: The original search query.
        results: A list of SearchResult objects.
        search_type: The type of search performed.
        show_username_tip: Whether to show tips for username searches.
        lang: The language for the response.

    Returns:
        A formatted string ready to be sent as a message.
    """
    clean_query = query.lstrip('@')
    escaped_query = html.escape(query)
    
    headers = {
        "id": {
            "profile": "Hasil pencarian profil untuk",
            "news": "Hasil pencarian berita untuk",
            "image": "Hasil pencarian gambar untuk",
            "general": "Hasil pencarian untuk"
        },
        "en": {
            "profile": "Profile search results for",
            "news": "News search results for",
            "image": "Image search results for",
            "general": "Search results for"
        }
    }
    
    lang_headers = headers.get(lang, headers[DEFAULT_LANGUAGE])
    header_key = search_type if search_type in lang_headers else "general"
    header_text = lang_headers[header_key]
    
    message = [f"<b>{header_text}:</b> <i>{escaped_query}</i>"]
    
    if not results:
        message.append(_get_alya_reaction(search_type, False, lang))
        if search_type == "profile":
            tips, _ = _get_username_tips(query, clean_query, lang)
            if tips:
                tip_header = {"id": "<b>Tips pencarian profil:</b>", "en": "<b>Profile search tips:</b>"}
                message.append(tip_header.get(lang, tip_header["id"]))
                message.append("\n".join(tips))
        return "\n\n".join(message)

    formatted_results = []
    for i, result in enumerate(results, 1):
        title = html.escape(result.title)
        snippet = html.escape(result.snippet or "")
        url = html.escape(result.link)
        displayed_link = html.escape(result.displayed_link or "")
        
        result_text = ""
        if result.result_type == "profile" or search_type == "profile":
            result_text = (
                f"{i}. <b><a href=\"{url}\">{title}</a></b> "
                f"<i>({displayed_link})</i>\n"
                f"{snippet}"
            )
        elif result.result_type == "news" or search_type == "news":
            result_text = (
                f"{i}. <b><a href=\"{url}\">{title}</a></b>\n"
                f"<i>{displayed_link}</i>\n"
                f"{snippet}"
            )
        elif result.result_type == "image" or search_type == "image":
            thumbnail_html = f'<a href="{url}">🖼️</a> ' if result.thumbnail else ""
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
        tips, _ = _get_username_tips(query, clean_query, lang)
        if tips:
            other_tips_header = {"id": "<b>Tip lainnya:</b>", "en": "<b>Other tips:</b>"}
            message.append(other_tips_header.get(lang, other_tips_header["id"]))
            message.append(tips[-1]) # The last tip is always the Google search link
            
    footer = _get_alya_reaction(search_type, True, lang)
    message.append(f"<i>~{footer}~</i>")
    
    return "\n\n".join(message)