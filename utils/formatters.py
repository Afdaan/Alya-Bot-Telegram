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
    lines = response.splitlines()
    cleaned_lines = []
    prefixes_to_remove = [
        "User:", f"{username}:", "Alya:", "Bot:", "Assistant:", "Human:", "AI:"
    ]
    for line in lines:
        line_stripped = line.strip()
        for prefix in prefixes_to_remove:
            if line_stripped.startswith(prefix):
                line = line_stripped[len(prefix):].strip()
                break
        if line.strip():
            cleaned_lines.append(line)
    response = "\n".join(cleaned_lines)
    if len(lines) > 1 and lines[0].strip().lower() in response.lower():
        response = "\n".join(lines[1:])
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
    
    # Process roleplay markers in order of priority
    # 1. Handle *action* (asterisks)
    def format_asterisk_action(match):
        content = match.group(1).strip()
        return f"<i>{escape_html(content)}</i>"
    
    text = re.sub(r'\*([^*]+?)\*', format_asterisk_action, text)
    
    # 2. Handle [action] (square brackets) - but avoid already processed content
    def format_bracket_action(match):
        content = match.group(1).strip()
        # Don't process if it's already in italic tags
        if '<i>' in content or '</i>' in content:
            return match.group(0)
        return f"<i>{escape_html(content)}</i>"
    
    text = re.sub(r'\[([^\]]+?)\]', format_bracket_action, text)
    
    # 3. Handle _action_ (underscores) - but be careful not to break existing formatting
    def format_underscore_action(match):
        content = match.group(1).strip()
        # Don't process if it's already in italic tags or contains HTML
        if '<i>' in content or '</i>' in content or '<' in content:
            return match.group(0)
        return f"<i>{escape_html(content)}</i>"
    
    # Only process underscores that aren't part of URLs or other markup
    text = re.sub(r'(?<![\w<])_([^_\n]+?)_(?![\w>])', format_underscore_action, text)
    
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
    **kwargs
) -> Union[str, List[str]]:
    """
    Format Alya's response for Telegram output.
    Formats and escapes LLM output, bolds honorifics, and splits for readability.
    All roleplay, mood, emoji, and Russian expressions are handled by LLM/NLP, not here.
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    
    # Sanitize the response first
    message = _sanitize_response(message, username)
    fallback = _get_fallback_message(lang)
    
    if not message or not message.strip():
        return fallback
    
    # Handle username substitution
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")
    
    # Format all roleplay/action markers to <i>...</i>
    formatted_text = _format_roleplay_and_actions(message, lang=lang)
    
    # Bold honorifics (e.g., -kun, -sama, -san, -chan)
    formatted_text = re.sub(r'([A-Za-z]+-(?:kun|sama|san|chan))', r'<b>\1</b>', formatted_text)
    
    # Split into paragraphs for Telegram readability (double newline or blank line)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', formatted_text) if p.strip()]
    
    # Clean up and join paragraphs with double newline
    final = '\n\n'.join(paragraphs)
    final = clean_html_entities(final)
    
    # Remove excessive blank lines
    final = re.sub(r'\n{3,}', '\n\n', final)
    
    # Final strip
    final = final.strip()
    
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