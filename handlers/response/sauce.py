"""
Response generator for SauceNAO command.

This module is responsible for creating the user-facing messages and UI
for the SauceNAO reverse image search feature, supporting multiple languages.
"""

from typing import Dict, List, Any, Tuple, Optional
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_texts(lang: str) -> Dict[str, str]:
    """
    Returns all SauceNAO related texts in the specified language.
    """
    texts = {
        "id": {
            "searching": "🔍 Alya lagi nyari sausnya, sabar ya...",
            "usage": "Hmph! Kalau mau cari saus, balas ke gambar dengan perintah `!sauce`. Jangan cuma kirim perintahnya doang, dasar!",
            "no_results": "Hmph! Aku tidak menemukan saus yang cocok untuk gambar ini. Mungkin coba gambar lain? 😳",
            "error_api": "A-aku gagal mencari saus... API-nya lagi bermasalah. Coba lagi nanti ya. 😥",
            "error_rate_limit": "Duh, kita kena limit! Kebanyakan request ke SauceNAO. Coba lagi beberapa saat lagi.",
            "error_unknown": "Waduh, ada error aneh pas nyari saus. Tim teknis (kalau ada) sudah dikasih tau!",
            "results_header": "<b>✨ Ditemukan {count} saus untuk gambar ini!</b>",
            "similarity": "Kemiripan",
            "author": "Pembuat",
            "source": "Sumber",
            "characters": "Karakter",
            "material": "Material",
            "low_similarity_warning": "⚠️ Beberapa hasil dengan kemiripan rendah disembunyikan.",
            "footer": "<i>~Hmph! B-bukan berarti aku mencarinya untukmu atau apa...~</i>",
            "view_on": "Lihat di {site}",
        },
        "en": {
            "searching": "🔍 Alya is searching for the sauce, please wait...",
            "usage": "Hmph! To find the sauce, reply to an image with `!sauce`. Don't just send the command alone, baka!",
            "no_results": "Hmph! I couldn't find any matching sauce for this image. Maybe try another one? 😳",
            "error_api": "I-I failed to find the sauce... The API is having issues. Please try again later. 😥",
            "error_rate_limit": "Oops, we've hit the rate limit! Too many requests to SauceNAO. Please try again in a bit.",
            "error_unknown": "Eh... что?! Ada error aneh saat nyari sauce... 😳\n\nB-bukan salahku! Sistemnya yang bermasalah... дурак teknologi! 💫\n\nCoba kirim gambar lain ya?",
            "results_header": "<b>✨ Found {count} sauces for this image!</b>",
            "similarity": "Similarity",
            "author": "Author",
            "source": "Source",
            "characters": "Characters",
            "material": "Material",
            "low_similarity_warning": "⚠️ Some results with low similarity were hidden.",
            "footer": "<i>~Hmph! I-it's not like I searched for this for you or anything...~</i>",
            "view_on": "View on {site}",
        }
    }
    return texts.get(lang, texts["id"])

def format_sauce_results(
    search_results: Dict[str, Any],
    lang: str
) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Formats the processed SauceNAO results into a message for Telegram.

    Args:
        search_results: The processed data from SauceNAOSearcher.
        lang: The language for the response ('id' or 'en').

    Returns:
        A tuple containing the message text and an InlineKeyboardMarkup.
    """
    texts = get_texts(lang)
    results = search_results.get("results", [])

    if not results:
        return texts["no_results"], None

    # Build response message
    header_text = texts["results_header"].format(count=len(results))
    
    result_parts = []
    for result in results:
        result_parts.append(_format_single_result(result, texts))

    # Add low similarity warning if applicable
    if search_results.get("has_low_similarity_results"):
        result_parts.append(f'\n{texts["low_similarity_warning"]}')

    # Combine all parts
    message_body = "\n\n".join(result_parts)
    final_message = f"{header_text}\n\n{message_body}\n\n{texts['footer']}"

    # Build keyboard
    keyboard = _build_results_keyboard(results, texts)

    return final_message, keyboard

def _format_single_result(result: Dict[str, Any], texts: Dict[str, str]) -> str:
    """Formats a single SauceNAO result item into a string."""
    header = result.get("header", {})
    data = result.get("data", {})
    similarity = float(header.get("similarity", 0))

    info = [f"<b>{texts['similarity']}:</b> {similarity:.2f}%"]

    # Title and source
    title = data.get("title") or data.get("source")
    if title:
        info.append(f"<b>{texts['source']}:</b> {_html_escape(title)}")

    # Author/creator
    author = data.get("member_name") or data.get("creator")
    if isinstance(author, list):
        author = ", ".join(map(str, author))
    if author:
        info.append(f"<b>{texts['author']}:</b> {_html_escape(author)}")

    # Characters
    characters = data.get("characters")
    if characters:
        info.append(f"<b>{texts['characters']}:</b> {_html_escape(characters)}")

    # Material (e.g., from artbook)
    material = data.get("material")
    if material:
        info.append(f"<b>{texts['material']}:</b> {_html_escape(material)}")

    return "\n".join(info)

def _build_results_keyboard(
    results: List[Dict[str, Any]],
    texts: Dict[str, str]
) -> Optional[InlineKeyboardMarkup]:
    """Builds an InlineKeyboardMarkup with links to sources."""
    buttons = []
    added_urls = set()

    for result in results:
        ext_urls = result.get("data", {}).get("ext_urls", [])
        if not ext_urls:
            continue

        # Prioritize known good sources
        source_priority = ["Pixiv", "Twitter", "Danbooru", "Gelbooru", "Yande.re", "AniDB"]
        
        # Sort URLs by priority
        sorted_urls = sorted(
            ext_urls,
            key=lambda u: next(
                (i for i, p in enumerate(source_priority) if p.lower() in u.lower()),
                len(source_priority)
            )
        )

        row = []
        for url in sorted_urls:
            if len(row) >= 2:  # Max 2 buttons per row
                break
            if url in added_urls:
                continue

            site_name = _get_site_name(url)
            if site_name:
                row.append(InlineKeyboardButton(
                    texts["view_on"].format(site=site_name),
                    url=url
                ))
                added_urls.add(url)
        
        if row:
            buttons.append(row)
    
    return InlineKeyboardMarkup(buttons) if buttons else None

def _get_site_name(url: str) -> Optional[str]:
    """Extracts a clean site name from a URL."""
    try:
        # Prioritize specific known domains
        known_sites = {
            "pixiv.net": "Pixiv",
            "twitter.com": "Twitter",
            "danbooru.donmai.us": "Danbooru",
            "gelbooru.com": "Gelbooru",
            "yande.re": "Yande.re",
            "anidb.net": "AniDB",
            "artstation.com": "ArtStation",
            "deviantart.com": "DeviantArt",
        }
        for domain, name in known_sites.items():
            if domain in url:
                return name
        
        # Fallback for other sites
        match = re.search(r'//(?:www\.)?([^/]+)', url)
        if match:
            # Clean up the domain name
            domain = match.group(1)
            parts = domain.split('.')
            if len(parts) > 1:
                return parts[-2].capitalize()
            return parts[0].capitalize()
    except Exception:
        return "Source"
    return "Source"

def _html_escape(text: Any) -> str:
    """A simple HTML escape function."""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
