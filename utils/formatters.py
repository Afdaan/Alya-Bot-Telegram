"""
Enterprise-grade response formatters for Alya Bot.

Handles HTML escaping, message structure, and persona-driven formatting
with deterministic output and proper error handling.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple, Union
import html
import re
import emoji
from pathlib import Path
import yaml
from functools import lru_cache

from config.settings import (
    FORMAT_ROLEPLAY,
    MAX_MESSAGE_LENGTH,
    FORMAT_EMOTION,
    MAX_EMOJI_PER_RESPONSE,
    DEFAULT_LANGUAGE
)
from core.persona import PersonaManager
from core.nlp import NLPEngine

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

def detect_roleplay(text: str) -> Tuple[str, Optional[str]]:
    """Detect and extract roleplay/action from text."""
    if not text:
        return text, None
    roleplay_patterns = [
        r'^\s*\[(.*?)\]\s*',
        r'^\s*\*(.*?)\*\s*',
        r'^\s*\((.*?)\)\s*',
    ]
    for pattern in roleplay_patterns:
        match = re.search(pattern, text)
        if match:
            action = match.group(1).strip()
            cleaned = re.sub(pattern, '', text).strip()
            return cleaned, action
    return text, None

def extract_emoji_sentiment(text: str) -> Tuple[str, List[str]]:
    """Extract emojis from text, limited by MAX_EMOJI_PER_RESPONSE."""
    if not text:
        return text, []
    emojis = [char for char in text if emoji.is_emoji(char)]
    if MAX_EMOJI_PER_RESPONSE > 0 and len(emojis) > MAX_EMOJI_PER_RESPONSE:
        emojis = emojis[:MAX_EMOJI_PER_RESPONSE]
    return text, emojis

def _sanitize_response(response: str, username: str) -> str:
    """Clean up model output, remove speaker prefixes and excessive punctuation."""
    if not response:
        return ""
    
    # Handle speaker prefixes at the beginning of response
    prefixes_to_remove = [
        "User:", f"{username}:", "Alya:", "Bot:", "Assistant:", "Human:", "AI:"
    ]
    
    # Check if response starts with any prefix and remove it
    response_stripped = response.strip()
    for prefix in prefixes_to_remove:
        if response_stripped.startswith(prefix):
            response = response_stripped[len(prefix):].strip()
            break
    
    # Clean up excessive punctuation
    response = re.sub(r'[.]{4,}', '...', response)
    response = re.sub(r'[!]{3,}', '!!', response)
    response = re.sub(r'[?]{3,}', '??', response)
    response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
    
    return response.strip()

def _get_fallback_message(lang: str = DEFAULT_LANGUAGE) -> str:
    """Return fallback message based on language."""
    fallback_map = {
        "id": "Maaf, aku tidak bisa merespons sekarang... 😳",
        "en": "Sorry, I can't respond right now... 😳"
    }
    return fallback_map.get(lang, fallback_map[DEFAULT_LANGUAGE])

def _format_roleplay_and_actions(text: str, lang: str = None) -> str:
    """Format roleplay and action markers to HTML italic tags."""
    if not text:
        return ""
    
    # First, protect existing HTML tags from being processed
    html_tags = []
    def protect_html(match):
        html_tags.append(match.group(0))
        return f"__HTML_TAG_{len(html_tags)-1}__"
    
    text = re.sub(r'<[^>]+>', protect_html, text)
    
    # Process roleplay markers with more careful regex patterns
    # 1. Handle *action* (asterisks) - must have content and not be at word boundaries
    def format_asterisk_action(match):
        content = match.group(1).strip()
        if not content:  # Skip empty matches
            return match.group(0)
        return f"<i>{escape_html(content)}</i>"
    
    # More specific pattern to avoid false positives
    text = re.sub(r'\*([^*\n]+?)\*', format_asterisk_action, text)
    
    # 2. Handle [action] (square brackets) - avoid already processed content
    def format_bracket_action(match):
        content = match.group(1).strip()
        if not content or '<i>' in content or '</i>' in content:
            return match.group(0)
        return f"<i>{escape_html(content)}</i>"
    
    text = re.sub(r'\[([^\]\n]+?)\]', format_bracket_action, text)
    
    # Don't process underscores as they might be part of text formatting
    # Let them stay as is to avoid conflicts
    
    # Restore protected HTML tags
    for i, tag in enumerate(html_tags):
        text = text.replace(f"__HTML_TAG_{i}__", tag)
    
    return text.strip()

def format_response(
    message: str,
    user_id: Optional[int] = None,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    lang: str = None,
    nlp_engine: Optional[NLPEngine] = None,
    relationship_level: int = 1,
    max_paragraphs: Optional[int] = 4,
    **kwargs
) -> Union[str, List[str]]:
    """
    Format Alya's response for Telegram output.
    Formats and escapes LLM output, bolds honorifics, and splits for readability.
    Adds emoji indicator for mood/roleplay actions, and blocks dialog with quotes for light novel style.
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
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")
    formatted_text = _format_roleplay_and_actions(message, lang=lang)
    logger.debug(f"Message after roleplay formatting: {repr(formatted_text)}")
    formatted_text = re.sub(r'([A-Za-z]+-(?:kun|sama|san|chan))', r'<b>\1</b>', formatted_text)
    # Light novel style: split only on double newline (\n\s*\n)
    raw_paragraphs = re.split(r'\n\s*\n', formatted_text)
    # Mapping action/mood to emoji
    mood_emoji = {
        'blushes': '😳',
        'muttering': '💭',
        'sighs': '😮\u200d💨',
        'frowns': '😕',
        'smiles': '😊',
        'smiles faintly': '🙂',
        'giggles': '😆',
        'laughs': '😂',
        'nods': '🙆',
        'shrugs': '🤷',
        'pouts': '😒',
        'stares': '👀',
        'winks': '😉',
        'mumbles': '🤔',
        'mutters': '💭',
        'sobs': '😭',
        'cries': '😭',
        'screams': '😱',
        'gasps': '😯',
        'whispers': '🤫',
        'shouts': '🗣️',
        'grins': '😁',
        'smirks': '😏',
        'rolls eyes': '🙄',
        'sigh': '😮\u200d💨',
        'hugs': '🤗',
        'waves': '👋',
        'bows': '🙇',
        'claps': '👏',
        'cheers': '🥳',
        'applauds': '👏',
        'thinks': '💭',
        'shrug': '🤷',
        'pats': '🫶',
        'smile': '😊',
        'faintly smiles': '🙂',
    }
    paragraphs = []
    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue
        # If the paragraph is only an action (e.g. <i>...</i>), add emoji indicator if known
        m = re.fullmatch(r'<i>(.*?)</i>', para)
        if m:
            action = m.group(1).strip().lower()
            emoji_icon = ''
            for key, val in mood_emoji.items():
                if key in action:
                    emoji_icon = val
                    break
            if emoji_icon:
                para = f"{emoji_icon} {para}"
            paragraphs.append(para)
        else:
            # Otherwise, treat as dialog/narrative: block with quotes if not already quoted
            text = para
            # Only add quotes if not already quoted and not an action
            if not (text.startswith('"') and text.endswith('"')):
                text = f'"{text}"'
            paragraphs.append(text)
    # Remove leading/trailing spaces, empty
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    # Limit to max_paragraphs if set
    if max_paragraphs and max_paragraphs > 0:
        paragraphs = paragraphs[:max_paragraphs]
    # Gabungkan dengan double newline antar paragraf
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
    """Format error response with persona and apology, following language preference."""
    try:
        if "{username}" in error_message:
            error_message = error_message.replace(
                "{username}", 
                f"<b>{escape_html(username)}</b>"
            )
        
        persona_manager = PersonaManager()
        persona = persona_manager.get_persona(persona_name=persona_name)
        roleplay = "terlihat bingung dan khawatir" if lang == "id" else "looks confused and worried"
        
        try:
            apologetic_mood = persona.get("emotions", {}).get("apologetic_sincere", {})
            expressions = apologetic_mood.get("expressions", [])
            if expressions:
                roleplay = random.choice(expressions)
                if "{username}" in roleplay:
                    roleplay = roleplay.replace("{username}", username)
        except Exception as e:
            logger.warning(f"Failed to get apologetic expressions: {e}")
        
        result_parts = [
            f"<i>{escape_html(roleplay)}</i>",
            f"{escape_html(error_message)} 😳"
        ]
        
        final_response = '\n\n'.join(result_parts)
        return clean_html_entities(final_response)
        
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
    
    # Simple phrase-based replacement, can be improved for context-aware in future
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