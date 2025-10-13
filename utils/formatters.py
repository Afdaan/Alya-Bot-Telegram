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

def escape_markdown_v2_safe(text: str) -> str:
    """Ultra-safe MarkdownV2 escaping - DISABLED for HTML mode."""
    # Since we're using HTML mode, don't escape anything
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
        formatted = format_persona_response(message, max_paragraphs, use_html)
    else:
        # Simple paragraph formatting for regular responses
        formatted = format_paragraphs(message, use_html)
    
    # Clean up excessive newlines
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    formatted = formatted.strip()
    
    logger.debug(f"Final formatted message: {repr(formatted)}")
    
    # Check length and split if necessary
    if len(formatted) <= MAX_MESSAGE_LENGTH:
        return formatted if formatted else fallback
    
    # Split into smaller parts
    parts = _split_long_message(formatted, use_html)
    return parts[0] if len(parts) == 1 else parts


def _contains_roleplay_elements(message: str) -> bool:
    """Check if message contains roleplay formatting elements."""
    roleplay_patterns = [
        r'\*[^*]+\*',      # *action*
        r'__[^_]+__',      # __roleplay__
        r'^>',             # > blockquote
        r'```[^`]+```',    # ```code```
        r'`[^`]+`'         # `inline code`
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
    use_html: bool = True
) -> str:
    """Format Alya persona response for Telegram with natural roleplay formatting.

    Args:
        message: The raw message string (may contain persona markup)
        max_paragraphs: Maximum number of paragraphs to include
        use_html: If True, use HTML mode, else MarkdownV2
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
    
    formatted_paragraphs = []
    
    for para in paragraphs:
        formatted_para = _format_single_paragraph(para, use_html)
        if formatted_para:
            formatted_paragraphs.append(formatted_para)
    
    # Limit emoji per response (max 15 total)
    final_text = '\n\n'.join(formatted_paragraphs)
    final_text = _limit_emoji_in_text(final_text, max_total=15)
    
    return final_text


def _format_single_paragraph(para: str, use_html: bool) -> str:
    """Format a single paragraph based on its content pattern."""
    para = para.strip()
    if not para:
        return ""
    
    # Clean up literal "italic" or "bold" markers that Gemini sometimes outputs
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


def _is_blockquote(text: str) -> bool:
    """Check if text should be formatted as blockquote (dialog)."""
    return text.startswith('>') or (text.startswith('"') and text.endswith('"'))


def _is_action_text(text: str) -> bool:
    """Check if text is an action (should be bold)."""
    return text.startswith('*') and text.endswith('*') and len(text) > 2


def _is_roleplay_text(text: str) -> bool:
    """Check if text is roleplay description (should be italic)."""
    return text.startswith('__') and text.endswith('__') and len(text) > 4


def _is_code_block(text: str) -> bool:
    """Check if text is code or Russian expression."""
    return (text.startswith('```') and text.endswith('```')) or \
           (text.startswith('`') and text.endswith('`'))


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
    content = text[1:-1].strip()  # Remove surrounding *
    
    if use_html:
        return f"<b>{escape_html(content)}</b>"
    else:
        # Don't double-escape for MarkdownV2
        return f"*{content}*"


def _format_roleplay(text: str, use_html: bool) -> str:
    """Format roleplay description (italic)."""
    content = text[2:-2].strip()  # Remove surrounding __
    
    if use_html:
        return f"<i>{escape_html(content)}</i>"
    else:
        # Don't double-escape for MarkdownV2
        return f"__{content}__"


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
    """Format normal conversation text."""
    if use_html:
        return escape_html(text)
    else:
        return text  # Don't escape for MarkdownV2 mode anymore


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