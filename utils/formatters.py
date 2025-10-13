"""
Neutral response formatters for Alya Bot.

Handles HTML/Markdown escaping and message structure with deterministic output and proper error handling.
"""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from functools import lru_cache
import logging
import re
import html
import yaml

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

    # Removed YAML-based phrase translation to rely on model output language
    
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


def _strip_stray_asterisks(text: str) -> str:
    """Remove stray leading/trailing multi-asterisks that are not part of a pair.

    Examples:
    - "** *text*" -> "*text*"
    - "*text* **" -> "*text*"
    - "** **Text" -> "Text"
    This prevents artifacts from model outputs like leading "** ".
    """
    if not text:
        return text
    # Remove one or more groups of asterisks followed by spaces at the beginning
    text = re.sub(r'^(?:\*+\s+)+', '', text)
    # Remove specific double pattern like "** **" at the start
    text = re.sub(r'^(?:\*{1,3}\s+\*{1,3}\s+)', '', text)
    # Remove leading sequences like '** ' or '*** ' (fallback)
    text = re.sub(r'^\*{2,}\s+', '', text)
    # Remove trailing sequences like ' **' or ' ***'
    text = re.sub(r'\s+\*{2,}$', '', text)
    return text

def _strip_stray_underscores(text: str) -> str:
    """Remove stray leading/trailing underscores that are not forming valid wrappers.

    Examples:
    - "__ _text_" -> "_text_"
    - "__  Text" -> "Text"
    - "Text __" -> "Text"
    """
    if not text:
        return text
    # Remove one or more groups of underscores followed by spaces at the start
    text = re.sub(r'^(?:_+\s+)+', '', text)
    # Remove single trailing groups like ' __' at the end
    text = re.sub(r'\s+_+$', '', text)
    return text

def _render_inline_wrapped(text: str, use_html: bool) -> str:
    """Render inline wrapped segments to italic.

    - Double underscores: __text__ -> <i>text</i>
    - Single underscores (not part of double): _text_ -> <i>text</i>
    """
    if not text:
        return text

    def repl_double(m: re.Match) -> str:
        content = m.group(1).strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

    def repl_single(m: re.Match) -> str:
        content = m.group(1).strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

    # Replace double underscores first
    text = re.sub(r'__([^_]+?)__', repl_double, text)
    # Replace single underscores that are not part of a double underscore sequence
    text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', repl_single, text)
    return text

def _format_single_paragraph(para: str, use_html: bool, lang: str = DEFAULT_LANGUAGE) -> str:
    """Format a single paragraph based on its content pattern.

    Handles common LLM artifacts like leading 'italic ' or noisy
    asterisk markers around labels such as Emosi/Emotion.

    Args:
        para: Raw paragraph text
        use_html: Whether to format using Telegram HTML
        lang: Preferred user language (unused for translation; kept for signature stability)
    """
    para = para.strip()
    if not para:
        return ""

    # Clean stray multi-asterisk and underscore artifacts before further parsing
    para = _strip_stray_asterisks(para)
    para = _strip_stray_underscores(para)

    # Treat heading-like first lines as-is (no YAML translation/suppression)
    if _looks_like_heading(para):
        return escape_html(para) if use_html else para

    # If entire paragraph is single-star wrapped, treat as italic roleplay
    if _is_full_star_wrapped(para):
        content = para.strip()[1:-1].strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

    # If entire paragraph is single-underscore wrapped, render as italic
    if _is_full_single_underscore_wrapped(para):
        content = para.strip()[1:-1].strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"

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
        if label in ('roleplay', 'italic'):
            return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"
        if label == 'mood':
            return escape_html(content) if use_html else content

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
            # Remove all asterisks then render underscore-wrapped segments as italic
            cleaned = para.replace('*', '').strip()
            cleaned = _render_inline_wrapped(cleaned, use_html)
            return cleaned
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
    if re.match(r'^```[\s\S]+```\s*$', t):
        return True
    # Single-line full inline code
    if re.fullmatch(r'`[^`]+`', t):
        return True
    return False


def _format_code_block(text: str, use_html: bool) -> str:
    """Format code blocks or inline code for Telegram HTML/MarkdownV2."""
    if not text:
        return ""
    t = text.strip()
    m = re.match(r'^```([a-zA-Z0-9_+-]*)\n([\s\S]*?)\n```\s*$', t)
    if m:
        code_body = m.group(2)
        escaped = escape_html(code_body) if use_html else code_body
        return f"<pre><code>{escaped}</code></pre>" if use_html else f"```\n{code_body}\n```"
    # Fallback to inline code
    if re.fullmatch(r'`[^`]+`', t):
        inner = t[1:-1]
        escaped = escape_html(inner) if use_html else inner
        return f"<code>{escaped}</code>" if use_html else f"`{inner}`"
    # Default escape
    return escape_html(text) if use_html else text


def _format_blockquote(text: str, use_html: bool) -> str:
    """Format blockquote lines starting with '>' or quoted content."""
    if not text:
        return ""
    t = text.strip()
    if t.startswith('>'):
        # Remove leading '>' from each line cleanly
        lines = [re.sub(r'^>\s?', '', ln).rstrip() for ln in t.splitlines()]
        content = '\n'.join(lines).strip()
    else:
        # Strip surrounding double quotes if present
        content = t[1:-1] if t.startswith('"') and t.endswith('"') else t
    return f"<blockquote>{escape_html(content)}</blockquote>" if use_html else f"> {content}"


def _format_action(text: str, use_html: bool) -> str:
    """Format action-style lines like *does this* into bold for visibility."""
    if not text:
        return ""
    # Unwrap surrounding asterisks when used as action markers
    cleaned = text.strip()
    # If looks like *Action* or **Action** treat content as bold
    m = re.match(r'^\*{1,2}\s*(.+?)\s*\*{1,2}$', cleaned)
    if m:
        content = m.group(1)
    else:
        # Remove stray asterisks without pairs
        content = cleaned.strip('*').strip()
    return f"<b>{escape_html(content)}</b>" if use_html else f"*{content}*"


def _format_roleplay(text: str, use_html: bool) -> str:
    """Format roleplay description lines that use underscores markers to italic."""
    if not text:
        return ""
    cleaned = _render_inline_wrapped(text, use_html)
    # If entire thing is wrapped with __...__ or _..._ convert to italic
    m_du = re.fullmatch(r'__\s*(.+?)\s__', cleaned)
    m_si = re.fullmatch(r'_\s*(.+?)\s_', cleaned)
    if m_du or m_si:
        inner = (m_du or m_si).group(1).strip()
        return f"<i>{escape_html(inner)}</i>" if use_html else f"__{inner}__"
    return cleaned if use_html else text


def _format_normal_text(text: str, use_html: bool) -> str:
    """Format normal paragraph text with safe escaping and inline italics support."""
    if not text:
        return ""
    t = text
    if use_html:
        # Render inline underscore-wrapped segments to italic, then escape remainder
        t = _render_inline_wrapped(t, use_html=True)
        # _render_inline_wrapped already escapes inside tags; escape remainder safely
        # To avoid double-escaping tags, rely on escape_html on the whole which preserves tags
        t = escape_html(t)
        return t
    else:
        return text


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

def _is_full_star_wrapped(text: str) -> bool:
    """Return True if the entire paragraph is wrapped with single asterisks: *...*.

    This is treated as italic roleplay paragraph.
    """
    if not text:
        return False
    m = re.fullmatch(r'\*\s*([^*].*?)\s*\*', text)
    return bool(m)


def _is_full_single_underscore_wrapped(text: str) -> bool:
    """Return True if entire paragraph is wrapped with single underscores: _..._.

    Avoid matching double-underscore roleplay (__...__).
    """
    if not text:
        return False
    t = text.strip()
    # Starts with single '_' but not '__', ends with single '_' but not '__'
    if not (t.startswith('_') and t.endswith('_')):
        return False
    if len(t) >= 2 and (t.startswith('__') or t.endswith('__')):
        return False
    # Ensure there is some non-underscore content inside
    return bool(re.fullmatch(r'_\s*(?!_)(.+?)(?<!_)\s*_', t))

# Strengthen beginning cleanup for patterns like "** **Text"
def _leading_asterisk_cleanup(text: str) -> str:
    if not text:
        return text
    # Remove two groups of asterisks optionally separated by spaces at the very start
    text = re.sub(r'^(?:\*{1,3}\s*){1,2}', '', text)
    return text

# integrate into existing cleaner by wrapping it (keep existing name stable)
_old_strip_stray_asterisks = _strip_stray_asterisks

def _strip_stray_asterisks(text: str) -> str:  # type: ignore[no-redef]
    text = _leading_asterisk_cleanup(text)
    return _old_strip_stray_asterisks(text)