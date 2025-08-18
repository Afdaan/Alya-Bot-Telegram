"""
Neutral response formatters for Alya Bot.

Handles HTML/Markdown escaping and message structure with deterministic output and proper error handling.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
import html
import re
from pathlib import Path
import yaml
from functools import lru_cache

from config.settings import (
    MAX_MESSAGE_LENGTH,
    DEFAULT_LANGUAGE
)

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """Escape HTML for Telegram, allowing only safe tags."""
    if not text:
        return ""
    escaped = html.escape(text)
    allowed_tags = ["b", "i", "u", "s", "code", "pre"]
    for tag in allowed_tags:
        escaped = re.sub(f"&lt;{tag}&gt;", f"<{tag}>", escaped, flags=re.IGNORECASE)
        escaped = re.sub(f"&lt;/{tag}&gt;", f"</{tag}>", escaped, flags=re.IGNORECASE)
    escaped = re.sub(r"&lt;a href=['\"]([^'\"]*)['\"]&gt;", r"<a href='\1'>", escaped)
    escaped = re.sub(r"&lt;/a&gt;", r"</a>", escaped)
    return escaped

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2 formatting."""
    if not text:
        return ""
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', 
        '#', '+', '-', '=', '|', '{', '}', '.', '!', '%'
    ]
    text = text.replace('\\', '\\\\')
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def escape_markdown_v2_safe(text: str) -> str:
    """Escape special characters for MarkdownV2, safer version."""
    if not text:
        return ""
    text = str(text)
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', 
        '#', '+', '-', '=', '|', '{', '}', '.', '!', ','
    ]
    text = text.replace('\\', '\\\\')
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_paragraphs(text: str, markdown: bool = True) -> str:
    """Format text into readable paragraphs for Telegram."""
    if not isinstance(text, str):
        logger.error("format_paragraphs: input must be str, got %s", type(text))
        return ""
    if not text:
        return ""
    paragraphs = re.split(r'(?:\n\s*\n|(?<=[^\n])\n(?=[^\n]))', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    formatted = '\n\n'.join(paragraphs)
    if markdown:
        formatted = escape_markdown_v2(formatted)
    else:
        formatted = clean_html_entities(formatted)
    return formatted

def clean_html_entities(text: str) -> str:
    """Clean up HTML entities and tags for Telegram HTML mode."""
    if not text:
        return ""
    text = re.sub(r'<([bius])\\">', r'<\1>', text)
    text = re.sub(r'</([bius])\\">', r'</\1>', text)
    text = re.sub(r'<([bius])\\>', r'<\1>', text)
    text = re.sub(r'</([bius])\\>', r'</\1>', text)
    text = re.sub(r'<i\\', '<i', text)
    text = re.sub(r'</i\\', '</i', text)
    text = re.sub(r'<([a-z]+)[^>]*>', lambda m: f"<{m.group(1)}>", text)
    text = re.sub(r'</([a-z]+)[^>]*>', lambda m: f"</{m.group(1)}>", text)
    return text

def format_markdown_response(
    text: str, 
    username: Optional[str] = None,
    telegram_username: Optional[str] = None,
    mentioned_username: Optional[str] = None,
    mentioned_text: Optional[str] = None
) -> str:
    """Format response for MarkdownV2, with username substitutions."""
    if not text:
        return ""
    substitutions = {
        '{username}': username,
        '{telegram_username}': telegram_username,
        '{mentioned_username}': mentioned_username,
        '{mentioned_text}': mentioned_text
    }
    for placeholder, value in substitutions.items():
        if value:
            escaped_value = escape_markdown_v2(str(value))
            text = text.replace(placeholder, escaped_value)
    return format_response(text)

def _sanitize_response(response: str, username: str) -> str:
    """Clean up model output, remove speaker prefixes and excessive punctuation."""
    if not response:
        return ""
    prefixes_to_remove = [
        "User:", f"{username}:", "Alya:", "Bot:", "Assistant:", "Human:", "AI:"
    ]
    response_stripped = response.strip()
    for prefix in prefixes_to_remove:
        if response_stripped.startswith(prefix):
            response = response_stripped[len(prefix):].strip()
            break
    response = re.sub(r'[.]{4,}', '...', response)
    response = re.sub(r'[!]{3,}', '!!', response)
    response = re.sub(r'[?]{3,}', '??', response)
    response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
    return response.strip()

def _get_fallback_message(lang: str = DEFAULT_LANGUAGE) -> str:
    """Return fallback message based on language."""
    fallback_map = {
        "id": "Maaf, aku tidak bisa merespons sekarang...",
        "en": "Sorry, I can't respond right now..."
    }
    return fallback_map.get(lang, fallback_map[DEFAULT_LANGUAGE])

def format_response(
    message: str,
    user_id: Optional[int] = None,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    lang: str = None,
    nlp_engine: Optional[Any] = None,
    relationship_level: int = 1,
    max_paragraphs: Optional[int] = 4,
    **kwargs
) -> Union[str, List[str]]:
    """
    Neutral formatting for Telegram output. Only splits paragraphs and escapes HTML, no persona/emoji logic.
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    logger.debug(f"Original message before processing: {repr(message)}")
    message = _sanitize_response(message, username)
    logger.debug(f"Message after sanitization: {repr(message)}")
    fallback = _get_fallback_message(lang)
    if not message or not message.strip():
        logger.warning("Message is empty after sanitization, returning fallback")
        return fallback
    if "{username}" in message:
        message = message.replace("{username}", escape_html(username))
    if target_name and "{target}" in message:
        message = message.replace("{target}", escape_html(target_name))
    # Only split paragraphs, no emoji or persona formatting
    raw_paragraphs = re.split(r'\n\s*\n', message)
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
    if max_paragraphs and max_paragraphs > 0:
        paragraphs = paragraphs[:max_paragraphs]
    final = '\n\n'.join(paragraphs)
    final = clean_html_entities(final)
    final = re.sub(r'\n{3,}', '\n\n', final)
    final = final.strip()
    logger.debug(f"Final formatted message: {repr(final)}")
    if len(final) <= MAX_MESSAGE_LENGTH:
        return final if final else fallback
    # If too long, split on paragraph boundaries
    parts = []
    current = ""
    for para in paragraphs:
        if not para:
            continue
        if len(current) + len(para) + 2 > MAX_MESSAGE_LENGTH:
            if current:
                parts.append(current.strip())
            current = para
        else:
            current = current + '\n\n' + para if current else para
    if current:
        parts.append(current.strip())
    parts = [p for p in parts if p]
    if not parts:
        return fallback
    return parts[0] if len(parts) == 1 else parts

def format_error_response(error_message: str, username: str = "user", lang: str = DEFAULT_LANGUAGE, persona_name: str = "waifu") -> str:
    """Format error response, neutral version."""
    try:
        if "{username}" in error_message:
            error_message = error_message.replace(
                "{username}", 
                escape_html(username)
            )
        return clean_html_entities(error_message)
    except Exception as e:
        logger.error(f"Error formatting error response: {e}")
        return _get_fallback_message(lang)

@lru_cache(maxsize=2)
def _load_translation_map() -> dict:
    """Load translation mapping from YAML file."""
    path = Path(__file__).parent.parent / "config" / "persona" / "translate.yml"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        logger.error(f"Failed to load translation YAML: {e}")
        return {}

def translate_response(text: str, lang: str = "id") -> str:
    """Translate Alya's response to the target language using YAML mapping."""
    if not text or lang == "id":
        return text
    translations = _load_translation_map()
    lang_map = translations.get(lang, {})
    for src, tgt in lang_map.items():
        if src in text:
            text = text.replace(src, tgt)
    return text

def get_translate_prompt(text: str, lang: str = "id") -> str:
    """Get simple translation prompt for LLM based on user language."""
    templates = _load_translation_map().get("translate_templates", {})
    prompt = templates.get(lang)
    if not prompt:
        return text
    return prompt.replace("{text}", text)

def format_persona_response(
    message: str,
    max_paragraphs: int = 4,
    markdown: bool = True
) -> str:
    """Format Alya persona response for Telegram with persona-aware MarkdownV2/HTML.

    Args:
        message: The raw message string (may contain persona markup)
        max_paragraphs: Maximum number of paragraphs to include
        markdown: If True, use MarkdownV2, else HTML
    Returns:
        Formatted string ready for Telegram
    """
    import re
    # Split paragraphs by double newlines
    paragraphs = re.split(r'\n\s*\n', message.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    if max_paragraphs > 0:
        paragraphs = paragraphs[:max_paragraphs]
    formatted_paragraphs = []
    for para in paragraphs:
        # Block dialog: starts with ' or ", treat as blockquote
        if para.startswith('"') or para.startswith("'"):
            text = para.strip('"').strip("'")
            if markdown:
                # Only escape for blockquote: do NOT escape - and .
                text = re.sub(r'([*_`~\[\](){}#+=|!])', r'\\\1', text)
                # Blockquote in MarkdownV2: must start with > and a space
                text = f'> {text}'
            else:
                text = f'<blockquote>{escape_html(text)}</blockquote>'
            formatted_paragraphs.append(text)
            continue
        # Mood actions: starts/ends with * (bold)
        if re.match(r'^\*[^*].*[^*]\*$', para):
            text = para[1:-1].strip()
            if markdown:
                # Escape all except * inside bold
                text = re.sub(r'([_`~\[\](){}#+=|!])', r'\\\1', text)
                text = f'*{text}*'
            else:
                text = f'<b>{escape_html(text)}</b>'
            formatted_paragraphs.append(text)
            continue
        # Roleplay: starts/ends with __ (italic)
        if re.match(r'^__[^_].*[^_]__$', para):
            text = para[2:-2].strip()
            if markdown:
                # Escape all except _ inside italic
                text = re.sub(r'([*`~\[\](){}#+=|!])', r'\\\1', text)
                text = f'__{text}__'
            else:
                text = f'<i>{escape_html(text)}</i>'
            formatted_paragraphs.append(text)
            continue
        # Otherwise: treat as normal conversation
        if markdown:
            text = escape_markdown_v2_safe(para)
        else:
            text = escape_html(para)
        formatted_paragraphs.append(text)
    # Limit emoji per response (max 4 per paragraph, max 15 total)
    emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+', flags=re.UNICODE)
    total_emoji = 0
    limited_paragraphs = []
    for para in formatted_paragraphs:
        emojis = emoji_pattern.findall(para)
        if emojis:
            # Limit to 4 emoji per paragraph
            if len(emojis) > 4:
                keep = emojis[:4]
                # Remove extra emojis
                def limit_emoji(m):
                    nonlocal keep
                    if keep:
                        keep.pop(0)
                        return m.group(0)
                    return ''
                para = emoji_pattern.sub(limit_emoji, para)
            # Count for total
            total_emoji += min(len(emojis), 4)
            if total_emoji > 15:
                # Remove all emojis if over total limit
                para = emoji_pattern.sub('', para)
        limited_paragraphs.append(para)
    # Join with double newline for MarkdownV2, <br><br> for HTML
    if markdown:
        return '\n\n'.join(limited_paragraphs)
    else:
        return '<br><br>'.join(limited_paragraphs)