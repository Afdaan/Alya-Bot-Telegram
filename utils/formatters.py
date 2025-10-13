"""
Neutral response formatters for Alya Bot.

Handles HTML/Markdown escaping and message structure with deterministic output and proper error handling.
"""

import logging
from typing import Dict, List, Optional, Any, Union
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
    """Escape HTML for Telegram, preserving safe formatting tags."""
    if not text:
        return ""
    
    # Preserve existing HTML tags that are safe for Telegram
    protected_patterns = []
    safe_tags = ["b", "i", "u", "s", "code", "pre", "blockquote", "a"]
    
    for tag in safe_tags:
        # Store existing safe tags temporarily
        pattern = rf"<{tag}(?:\s[^>]*)?>.*?</{tag}>"
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for i, match in enumerate(matches):
            placeholder = f"__SAFE_TAG_{tag}_{i}__"
            protected_patterns.append((placeholder, match))
            text = text.replace(match, placeholder, 1)
    
    # Now escape the remaining text
    escaped = html.escape(text)
    
    # Restore protected patterns
    for placeholder, original in protected_patterns:
        escaped = escaped.replace(placeholder, original)
    
    return escaped

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2 formatting - DISABLED for HTML mode."""
    # Since we're using HTML mode, don't escape markdown characters
    return text if text else ""

def format_paragraphs(text: str, use_html: bool = True) -> str:
    """Format text into readable paragraphs for Telegram."""
    if not isinstance(text, str):
        logger.error("format_paragraphs: input must be str, got %s", type(text))
        return ""
    if not text:
        return ""
    
    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    formatted = '\n\n'.join(paragraphs)
    
    # Apply appropriate escaping based on parse mode
    if use_html:
        formatted = escape_html(formatted)
    else:
        formatted = escape_markdown_v2(formatted)
    
    return formatted

def clean_html_entities(text: str) -> str:
    """Clean up HTML entities and malformed tags for Telegram HTML mode."""
    if not text:
        return ""
    
    # Remove escaped quotes from HTML tags
    text = re.sub(r'<([bius])\\">', r'<\1>', text)
    text = re.sub(r'</([bius])\\">', r'</\1>', text)
    text = re.sub(r'<([bius])\\>', r'<\1>', text)
    text = re.sub(r'</([bius])\\>', r'</\1>', text)
    
    # Clean up malformed italic tags
    text = re.sub(r'<i\\', '<i', text)
    text = re.sub(r'</i\\', '</i', text)
    
    # Remove attributes from HTML tags (keep only the tag name)
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
            # Don't escape since we're using HTML mode primarily
            text = text.replace(placeholder, str(value))
    return format_response(text, use_html=True)

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
    use_html: bool = True,  # Default to HTML mode as per settings
    **kwargs
) -> Union[str, List[str]]:
    """
    Enhanced formatting for Telegram output with persona-aware roleplay formatting.
    Supports both HTML and MarkdownV2 modes with intelligent content detection.
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    
    logger.debug(f"Original message before processing: {repr(message)}")
    
    # Sanitize and clean the message
    message = _sanitize_response(message, username)
    logger.debug(f"Message after sanitization: {repr(message)}")
    
    fallback = _get_fallback_message(lang)
    if not message or not message.strip():
        logger.warning("Message is empty after sanitization, returning fallback")
        return fallback
    
    # Replace placeholders
    if "{username}" in message:
        safe_username = escape_html(username) if use_html else escape_markdown_v2(username)
        message = message.replace("{username}", safe_username)
    
    if target_name and "{target}" in message:
        safe_target = escape_html(target_name) if use_html else escape_markdown_v2(target_name)
        message = message.replace("{target}", safe_target)
    
    # Check if this looks like a persona response (contains roleplay elements)
    if _contains_roleplay_elements(message):
        formatted = format_persona_response(message, max_paragraphs, use_html, lang)
    else:
        # Simple paragraph formatting for regular responses
        formatted = format_paragraphs(message, use_html)
    
    # Clean up excessive newlines
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    formatted = formatted.strip()

    # Ensure translation is applied regardless of branch to avoid mixed-language outputs
    formatted = translate_response(formatted, lang)
    
    logger.debug(f"Final formatted message: {repr(formatted)}")
    
    # Check length and split if necessary
    if len(formatted) <= MAX_MESSAGE_LENGTH:
        return formatted if formatted else fallback
    
    # Split into smaller parts
    parts = _split_long_message(formatted, use_html)
    return parts[0] if len(parts) == 1 else parts


def format_persona_response(
    message: str,
    max_paragraphs: int = 4,
    use_html: bool = True,
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """Format Alya persona response for Telegram with natural roleplay formatting.

    Args:
        message: The raw message string (may contain persona markup)
        max_paragraphs: Maximum number of paragraphs to include
        use_html: If True, use HTML mode, else MarkdownV2
        lang: Target language preference for final rendering
    Returns:
        Formatted string ready for Telegram
    """
    if not message:
        return ""
    
    # Split paragraphs by double newlines
    paragraphs = re.split(r'\n\s*\n', message.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    if max_paragraphs > 0:
        paragraphs = paragraphs[:max_paragraphs]
    
    formatted_paragraphs: List[str] = []
    for para in paragraphs:
        formatted_para = _format_single_paragraph(para, use_html, lang)
        if formatted_para:
            formatted_paragraphs.append(formatted_para)
    
    # Limit emoji per response (max 15 total)
    final_text = '\n\n'.join(formatted_paragraphs)
    final_text = _limit_emoji_in_text(final_text, max_total=15)

    # Apply simple translation map for target language (including 'id')
    final_text = translate_response(final_text, lang)
    
    return final_text


def _contains_roleplay_elements(message: str) -> bool:
    """Check if message contains roleplay formatting elements."""
    roleplay_patterns = [
        r'\*[^*]+\*',         # *action*
        r'__[^_]+__',           # __roleplay__
        r'^>',                  # > blockquote
        r'```[^`]+```',         # ```code```
        r'`[^`]+`',             # `inline code`
        # labeled roleplay/action/italic/mood lines (optionally wrapped, optional colon/dash)
        r'(?i)^[\s*_]*\b(action|roleplay|italic|mood)\b\s*[:\-—]?'
    ]
    
    for pattern in roleplay_patterns:
        if re.search(pattern, message, re.MULTILINE):
            return True
    
    return False


def _split_long_message(message: str, use_html: bool) -> List[str]:
    """Split long message into parts respecting paragraph boundaries."""
    paragraphs = re.split(r'\n\s*\n', message)
    parts = []
    current = ""
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        # Check if adding this paragraph would exceed limit
        test_length = len(current) + len(para) + 2  # +2 for \n\n
        
        if test_length > MAX_MESSAGE_LENGTH and current:
            parts.append(current.strip())
            current = para
        else:
            if current:
                current = current + '\n\n' + para
            else:
                current = para
    
    if current:
        parts.append(current.strip())
    
    # Filter out empty parts
    parts = [p for p in parts if p.strip()]
    
    if not parts:
        return [_get_fallback_message(DEFAULT_LANGUAGE)]
    
    return parts

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
    """Translate Alya's response to the target language using YAML mapping.

    Applies simple phrase mapping from config/persona/translate.yml. If a mapping
    exists for the requested language (including 'id'), it will be applied.
    """
    if not text:
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

def _load_emotion_heading_map() -> dict:
    """Load emotion/heading translations from YAML.

    Expected file: config/persona/emotion_display.yml
    Structure is flexible; we try common keys and fall back to top-level maps.
    """
    path = Path(__file__).parent.parent / "config" / "persona" / "emotion_display.yml"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Prefer nested structures like { headings: { id: {...}, en: {...} } }
        # Otherwise accept top-level { id: {...} } or flat maps.
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        logger.error(f"Failed to load emotion_display YAML: {e}")
        return {}


def _looks_like_heading(text: str) -> bool:
    """Heuristically determine if a paragraph is a short heading/summary line.

    Rules: single line, <= 120 chars, no strong punctuation markers or markup, not empty.
    """
    if not text:
        return False
    t = text.strip()
    if "\n" in t or len(t) > 120:
        return False
    # Avoid treating code/markup/labeled lines as headings
    if any(x in t for x in ("`", "*", "__", ">", ":", "—")):
        return False
    # Heading often uses words separated by spaces, with letters
    return bool(re.search(r"[A-Za-zÀ-ÿ]", t))


def _translate_heading(text: str, lang: str) -> Optional[str]:
    """Translate heading using emotion_display.yml mapping if available.

    Returns translated text or None if no mapping found.
    """
    data = _load_emotion_heading_map()
    if not data:
        return None

    # Try common structures
    # 1) data["headings"][lang][source]
    src = text.strip()
    headings = data.get("headings") if isinstance(data, dict) else None
    if isinstance(headings, dict):
        lang_map = headings.get(lang)
        if isinstance(lang_map, dict):
            # Exact match
            if src in lang_map:
                return lang_map[src]
            # Case-insensitive match
            lower_map = {k.lower(): v for k, v in lang_map.items()}
            if src.lower() in lower_map:
                return lower_map[src.lower()]
    # 2) data[lang][source]
    if isinstance(data.get(lang), dict):
        lang_map2 = data.get(lang)
        if src in lang_map2:
            return lang_map2[src]
        lower_map2 = {k.lower(): v for k, v in lang_map2.items()}
        if src.lower() in lower_map2:
            return lower_map2[src.lower()]
    # 3) Flat map
    if src in data:
        val = data.get(src)
        if isinstance(val, str):
            return val
    return None

def _format_single_paragraph(para: str, use_html: bool, lang: str = DEFAULT_LANGUAGE) -> str:
    """Format a single paragraph based on its content pattern.

    Handles common LLM artifacts like leading 'italic ' or noisy
    asterisk markers around labels such as Emosi/Emotion.

    Args:
        para: Raw paragraph text
        use_html: Whether to format using Telegram HTML
        lang: Preferred user language for heading translation/dropping
    """
    para = para.strip()
    if not para:
        return ""

    # If this looks like a heading/summary, render as plain text and translate via YAML
    if _looks_like_heading(para):
        translated = _translate_heading(para, lang) or _translate_heading(para, "id")
        if lang == "id":
            if translated:
                return escape_html(translated) if use_html else translated
            likely_english = re.search(r"\b(and|but|why|slightly|trying|concerned|surprised|almost)\b", para, re.IGNORECASE)
            if likely_english:
                return ""
        return escape_html(translated or para) if use_html else (translated or para)

    # Handle labeled lines like "Action:", "Roleplay:", "Mood:", "Italic:"
    m_label_any = re.match(
        r'^\s*(?:\*{1,2}|__)?\s*(action|roleplay|mood|italic)\s*[:\-—]?\s*(.+?)\s*(?:\*{1,2}|__)?\s*$',
        para,
        flags=re.IGNORECASE,
    )
    if m_label_any:
        label = m_label_any.group(1).lower()
        content = m_label_any.group(2).strip()
        # Unwrap if wrapped with *...* or __...__
        m_wrap_star = re.fullmatch(r'\*([^*]+)\*', content)
        m_wrap_ul = re.fullmatch(r'__([^_]+)__', content)
        if m_wrap_star:
            content = m_wrap_star.group(1).strip()
        elif m_wrap_ul:
            content = m_wrap_ul.group(1).strip()
        if label == 'action':
            return f"<b>{escape_html(content)}</b>" if use_html else f"*{content}*"
        if label == 'roleplay' or label == 'italic':
            return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"
        if label == 'mood':
            # Render as plain heading (no blockquote), translate if mapping exists
            translated = _translate_heading(content, lang) or content
            return escape_html(translated) if use_html else translated

    # Normalize literal style directives like: italic "..." or italic ... or italic: ...
    m_italic_quoted = re.match(r'^italic\s+["\'](.+)["\']$', para, flags=re.IGNORECASE)
    if m_italic_quoted:
        content = m_italic_quoted.group(1).strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

    m_italic_plain = re.match(r'^italic\s+(.+)$', para, flags=re.IGNORECASE)
    if m_italic_plain:
        content = m_italic_plain.group(1).strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

    m_italic_colon = re.match(r'^italic\s*[:\-—]\s*(.+)$', para, flags=re.IGNORECASE)
    if m_italic_colon:
        content = m_italic_colon.group(1).strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

    # Normalize noisy emotion label lines like: *Emosi:** *Text or *Emotion:** *Text
    m_emotion = re.match(r'^\*?\s*(emosi|emotion)\s*:?\**\s*\*?\s*(.+)$', para, flags=re.IGNORECASE)
    if m_emotion:
        raw_label = m_emotion.group(1)
        content = m_emotion.group(2).strip()
        label_l = raw_label.lower()
        label_norm = 'Emosi' if label_l == 'emosi' else ('Emotion' if label_l == 'emotion' else raw_label.capitalize())
        if use_html:
            return f"<b>{escape_html(label_norm)}:</b> {escape_html(content)}"
        else:
            return f"*{label_norm}:* {content}"

    # Handle multiple independent *...* segments like: *Confused** **Slightly concerned*
    if para.startswith('*') and para.count('*') >= 3:
        if use_html:
            rendered = re.sub(
                r'\*([^*]+)\*',
                lambda m: f"<b>{escape_html(m.group(1).strip())}</b>",
                para,
            )
            rendered = rendered.replace('*', '')
            return rendered.strip()
        else:
            return para

    # Clean up literal markers fallback
    para = re.sub(r'^italic\s+["\'](.+)["\']$', r'__\1__', para, flags=re.IGNORECASE)
    para = re.sub(r'^bold\s+["\'](.+)["\']$', r'*\1*', para, flags=re.IGNORECASE)

    # Detect and format different paragraph types (order matters!)
    if _is_code_block(para):
        return _format_code_block(para, use_html)
    elif _is_roleplay_text(para):
        return _format_roleplay(para, use_html)
    elif _is_action_text(para):
        return _format_action(para, use_html)
    elif _is_blockquote(para):
        return _format_blockquote(para, use_html)
    else:
        return _format_normal_text(para, use_html)


def _is_action_text(text: str) -> bool:
    """Check if text is an action (should be bold)."""
    return text.startswith('*') and '*' in text[1:]


def _is_roleplay_text(text: str) -> bool:
    """Check if text is roleplay description (should be italic)."""
    return text.startswith('__') and '__' in text[2:]


def _is_blockquote(text: str) -> bool:
    """Check if text should be formatted as blockquote (dialog)."""
    return text.startswith('>') or (text.startswith('"') and text.endswith('"'))


def _is_code_block(text: str) -> bool:
    """Detect if a paragraph is a code snippet.

    A paragraph is considered code when it is:
    - A fenced code block wrapped with triple backticks ```...```
    - Entirely wrapped with single backticks `...` (inline snippet as its own paragraph)
    """
    if not text:
        return False
    t = text.strip()
    # Fenced block
    if t.startswith('```') and t.endswith('```'):
        return True
    # Full inline code paragraph (avoid treating fenced code as inline)
    if t.startswith('`') and t.endswith('`') and '```' not in t:
        return True
    return False


def _format_blockquote(text: str, use_html: bool) -> str:
    """Format blockquote/dialog text."""
    # Remove quote markers
    if text.startswith('>'):
        content = text[1:].strip()
    else:
        content = text.strip('"').strip("'")
    
    if use_html:
        return f"<blockquote>{escape_html(content)}</blockquote>"
    else:
        # MarkdownV2 blockquote
        return f"> {content}"


def _format_action(text: str, use_html: bool) -> str:
    """Format action text (bold)."""
    # If there are multiple *...* segments, format each to bold in HTML and strip stray '*'
    multi_segments = re.findall(r'\*([^*]+)\*', text)
    if len(multi_segments) >= 2:
        if use_html:
            rendered = re.sub(
                r'\*([^*]+)\*',
                lambda m: f"<b>{escape_html(m.group(1).strip())}</b>",
                text,
            )
            return rendered.replace('*', '').strip()
        else:
            return text

    # Support trailing content after closing '*', e.g., *Action* 😊
    end_idx = text.rfind('*')
    if end_idx <= 0:
        content = text.strip('*')
        remainder = ''
    else:
        content = text[1:end_idx].strip()
        remainder = text[end_idx+1:].strip()

    if use_html:
        formatted = f"<b>{escape_html(content)}</b>"
        if remainder:
            formatted += f" {escape_html(remainder)}"
        return formatted
    else:
        return f"*{content}*{(' ' + remainder) if remainder else ''}"


def _format_roleplay(text: str, use_html: bool) -> str:
    """Format roleplay description (italic)."""
    # Support trailing content after closing '__', e.g., __desc__ 😊
    end_idx = text.find('__', 2)
    if end_idx == -1:
        content = text.strip('_')
        remainder = ''
    else:
        content = text[2:end_idx].strip()
        remainder = text[end_idx+2:].strip()

    # Normalize accidental 'italic ' prefix inside roleplay content
    if content.lower().startswith('italic '):
        content = content[7:].strip()

    if use_html:
        formatted = f"<i>{escape_html(content)}</i>"
        if remainder:
            formatted += f" {escape_html(remainder)}"
        return formatted
    else:
        return f"__{content}__{(' ' + remainder) if remainder else ''}"


def _format_code_block(text: str, use_html: bool) -> str:
    """Format code or Russian expressions."""
    if text.startswith('```') and text.endswith('```'):
        content = text[3:-3].strip()
        if use_html:
            return f"<pre>{escape_html(content)}</pre>"
        else:
            return f"```\n{content}\n```"
    else:
        content = text[1:-1].strip()  # Remove surrounding `
        if use_html:
            return f"<code>{escape_html(content)}</code>"
        else:
            return f"`{content}`"


def _format_normal_text(text: str, use_html: bool) -> str:
    """Format normal conversation text as blockquote to use green bubble style."""
    if use_html:
        return f"<blockquote>{escape_html(text)}</blockquote>"
    else:
        return f"> {text}"  # MarkdownV2/Markdown blockquote


def _limit_emoji_in_text(text: str, max_total: int = 15) -> str:
    """Limit total emoji count in text."""
    emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF]+',
        flags=re.UNICODE
    )
    
    emojis = emoji_pattern.findall(text)
    if len(emojis) <= max_total:
        return text
    
    # Remove excess emoji
    emoji_count = 0
    def replace_emoji(match):
        nonlocal emoji_count
        if emoji_count < max_total:
            emoji_count += 1
            return match.group(0)
        return ''
    
    return emoji_pattern.sub(replace_emoji, text)