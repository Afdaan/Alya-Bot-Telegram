"""
Response formatters for Alya Bot that handle HTML escaping and message structure.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
import html
import re
import emoji
import difflib

from config.settings import (
    FORMAT_ROLEPLAY, FORMAT_EMOTION, FORMAT_RUSSIAN, 
    MAX_EMOJI_PER_RESPONSE, RUSSIAN_EXPRESSIONS
)
from core.persona import PersonaManager

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """Escape HTML special characters in text, except inside allowed tags."""
    if not text:
        return ""
    # Only escape outside <b>, <i>, <u>, <s>, <a href="">, <code>, <pre>
    # Simple approach: escape everything, then unescape inside allowed tags
    allowed_tags = ["b", "i", "u", "s", "code", "pre"]
    # Escape all first
    text = html.escape(text)
    # Unescape allowed tags
    for tag in allowed_tags:
        text = re.sub(
            f"&lt;{tag}&gt;", f"<{tag}>", text, flags=re.IGNORECASE
        )
        text = re.sub(
            f"&lt;/{tag}&gt;", f"</{tag}>", text, flags=re.IGNORECASE
        )
    # Allow <a href="">...</a>
    text = re.sub(r"&lt;a href=['\"](.*?)['\"]&gt;", r"<a href='\1'>", text)
    text = re.sub(r"&lt;/a&gt;", r"</a>", text)
    return text

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram's MarkdownV2 format.
    
    Args:
        text: Raw text to escape
        
    Returns:
        Text with special characters escaped for MarkdownV2
    """
    if not text:
        return ""
        
    # Special characters that need to be escaped in MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '%']
    
    # Escape each special character with a backslash
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text

def escape_markdown_v2_safe(text: str) -> str:
    """Ultra-safe escaping of MarkdownV2 special characters.
    
    This implementation guarantees fully escaped text for Telegram's MarkdownV2 format.
    
    Args:
        text: Text to escape
        
    Returns:
        Text with all special characters properly escaped
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # List all characters that need escaping in MarkdownV2
    # This is the complete list from Telegram API documentation
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', 
                    '-', '=', '|', '{', '}', '.', '!', ',']
    
    # Escape backslash first to avoid double escaping
    text = text.replace('\\', '\\\\')
    
    # Escape all other special characters
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def format_paragraphs(text: str, markdown: bool = True) -> str:
    """Format multi-paragraph text for Telegram by adding spacing and escaping if needed.

    Args:
        text: The original multi-paragraph string.
        markdown: Whether to escape for MarkdownV2 (default True). If False, treat as HTML.

    Returns:
        Formatted string with clear paragraph separation and safe for Telegram.
    """
    # Pisahkan paragraf dengan 2 newline atau 1 newline diapit teks
    paragraphs = re.split(r'(?:\n\s*\n|(?<=[^\n])\n(?=[^\n]))', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    formatted = '\n\n'.join(paragraphs)
    if markdown:
        formatted = escape_markdown_v2(formatted)
    else:
        formatted = clean_html_entities(formatted)
    return formatted

def clean_html_entities(text: str) -> str:
    """Clean up invalid HTML tags/entities for Telegram HTML parse_mode."""
    # Remove unsupported/typo tags like <i\">, <b\">, etc.
    text = re.sub(r'<([bius])\\">', r'<\1>', text)
    text = re.sub(r'</([bius])\\">', r'</\1>', text)
    # Remove any stray backslashes in tags
    text = re.sub(r'<([bius])\\>', r'<\1>', text)
    text = re.sub(r'</([bius])\\>', r'</\1>', text)
    # Remove unsupported tags/entities
    text = re.sub(r'<i\\', '<i', text)
    text = re.sub(r'</i\\', '</i', text)
    # Remove any tag with invalid chars
    text = re.sub(r'<([a-z]+)[^>]*>', lambda m: f"<{m.group(1)}>", text)
    text = re.sub(r'</([a-z]+)[^>]*>', lambda m: f"</{m.group(1)}>", text)
    return text

def format_markdown_response(text: str, username: Optional[str] = None,
                           telegram_username: Optional[str] = None,
                           mentioned_username: Optional[str] = None,
                           mentioned_text: Optional[str] = None) -> str:
    """Format bot response with proper spacing and styling."""
    if not text:
        return ""

    # Handle substitutions
    substitutions = {
        '{username}': username,
        '{telegram_username}': telegram_username,
        '{mentioned_username}': mentioned_username,
        '{mentioned_text}': mentioned_text
    }
    
    # Replace variables
    for placeholder, value in substitutions.items():
        if value:
            escaped_value = escape_markdown_v2(str(value))
            text = text.replace(placeholder, escaped_value)

    # Use Alya response formatter
    return format_response(text)

def detect_roleplay(text: str) -> Tuple[str, Optional[str]]:
    """Detect and extract roleplay actions from text.
    
    Args:
        text: The input text
        
    Returns:
        Tuple of (cleaned_text, roleplay_text or None)
    """
    # Check for standard roleplay patterns: [action], *action*, (action)
    roleplay_patterns = [
        r'^\s*\[(.*?)\]\s*',  # [action] at start
        r'^\s*\*(.*?)\*\s*',  # *action* at start
        r'^\s*\((.*?)\)\s*',  # (action) at start
    ]
    
    for pattern in roleplay_patterns:
        match = re.search(pattern, text)
        if match:
            action = match.group(1).strip()
            cleaned = re.sub(pattern, '', text).strip()
            return cleaned, action
    
    # No explicit roleplay found
    return text, None

def extract_emoji_sentiment(text: str) -> Tuple[str, List[str]]:
    """Extract emojis from text and identify their sentiment.
    
    Args:
        text: The input text
        
    Returns:
        Tuple of (text_without_emojis, list_of_emojis)
    """
    # Find all emojis in text
    emojis = []
    characters_to_check = list(text)
    for char in characters_to_check:
        if emoji.is_emoji(char):
            emojis.append(char)
    
    # Limit number of emojis if needed
    if MAX_EMOJI_PER_RESPONSE > 0 and len(emojis) > MAX_EMOJI_PER_RESPONSE:
        emojis = emojis[:MAX_EMOJI_PER_RESPONSE]
    
    return text, emojis

def _sanitize_response(response: str, username: str) -> str:
    """Sanitize response to remove echo, self-reference, and duplicate paragraphs."""
    # Remove "User:", "{username}:", "Alya:", "Bot:", "Assistant:" at start of any line
    lines = response.splitlines()
    cleaned_lines = []
    for line in lines:
        for prefix in [f"User:", f"{username}:", "Alya:", "Bot:", "Assistant:"]:
            if line.strip().startswith(prefix):
                line = line.strip()[len(prefix):].strip()
        cleaned_lines.append(line)
    response = "\n".join(cleaned_lines)

    # Remove echo of user input at the start (if present)
    # (Assume echo is first line and next line is the real answer)
    if len(lines) > 1 and lines[0].strip().lower() in response.lower():
        response = "\n".join(lines[1:])

    # Remove duplicate paragraphs (very similar blocks)
    paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
    unique_paragraphs = []
    for p in paragraphs:
        if not any(_are_paragraphs_similar(p, up) for up in unique_paragraphs):
            unique_paragraphs.append(p)
    response = "\n\n".join(unique_paragraphs)

    # Clean up excessive whitespace
    response = "\n".join([line.strip() for line in response.split("\n") if line.strip()])
    return response

def _are_paragraphs_similar(p1: str, p2: str) -> bool:
    """Check if two paragraphs are very similar (for deduplication)."""
    if not p1 or not p2:
        return False
    ratio = difflib.SequenceMatcher(None, p1.lower(), p2.lower()).ratio()
    return ratio > 0.8

def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu"
) -> str:
    """Format a bot response with persona, mood, and expressive emoji. Output is valid HTML."""
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)

    # Sanitize message first
    message = _sanitize_response(message, username)

    # Replace username/target placeholders
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    # Extract roleplay and split paragraphs
    message, existing_roleplay = detect_roleplay(message)
    paragraphs = [p.strip() for p in message.split('\n\n') if p.strip()]
    main_message = paragraphs[0] if paragraphs else message
    optional_messages = paragraphs[1:] if len(paragraphs) > 1 else []

    # Remove duplicate optionals
    filtered_optionals = []
    for opt_msg in optional_messages:
        ratio = difflib.SequenceMatcher(None, main_message.lower(), opt_msg.lower()).ratio()
        if ratio < 0.85:
            filtered_optionals.append(opt_msg)
    optional_messages = filtered_optionals[:1]

    # Roleplay formatting
    roleplay = existing_roleplay
    if not roleplay and FORMAT_ROLEPLAY:
        expressions = persona.get("emotions", {}).get(mood if mood != "default" else "neutral", {}).get("expressions", [])
        if expressions:
            roleplay = random.choice(expressions)
            if "{username}" in roleplay:
                roleplay = roleplay.replace("{username}", username)
    if roleplay:
        roleplay = f"<i>{escape_html(roleplay)}</i>"

    def contains_emoji(text: str) -> bool:
        return any(emoji.is_emoji(char) for char in text)

    main_content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', main_message)
    main_content = re.sub(r'([A-ZaZ]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-ZaZ]+-chan)', r'<b>\1</b>', main_content)
    main_content = escape_html(main_content)

    # Format optionals
    formatted_optionals = []
    if optional_messages:
        opt_msg = optional_messages[0]
        opt_msg = re.sub(r'\*(.*?)\*', r'<i>\1</i>', opt_msg)
        opt_msg = escape_html(opt_msg)
        formatted_optionals.append(opt_msg)

    # Mood display (optional, only if mood != default)
    mood_display = None
    if mood != "default" and FORMAT_EMOTION:
        try:
            import yaml
            from pathlib import Path
            yaml_path = Path(__file__).parent.parent / "config" / "persona" / "emotion_display.yml"
            with open(yaml_path, "r", encoding="utf-8") as f:
                mood_yaml = yaml.safe_load(f)
            mood_list = mood_yaml.get("moods", {}).get(mood, []) or mood_yaml.get("moods", {}).get("default", [])
            chosen = random.choice(mood_list) if mood_list else mood.replace("_", " ")
        except Exception as e:
            logger.warning(f"Failed to load emotion_display.yml: {e}")
            chosen = mood.replace("_", " ")
        mood_display = f"<i>{escape_html(chosen)}</i>"

    result = []
    if roleplay:
        result.append(roleplay)
    result.append(main_content)
    if formatted_optionals:
        result.extend(formatted_optionals)
    if mood_display:
        result.append(mood_display)

    final = '\n\n'.join([r for r in result if r and r.strip()])
    return clean_html_entities(final)

def format_error_response(error_message: str, username: str = "user") -> str:
    """Format an error response with appropriate tone. Output is valid HTML."""
    if "{username}" in error_message:
        error_message = error_message.replace("{username}", f"<b>{escape_html(username)}</b>")
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona()
    roleplay = "terlihat bingung dan khawatir"
    apologetic_mood = persona.get("emotions", {}).get("apologetic_sincere", {})
    expressions = apologetic_mood.get("expressions", [])
    if expressions:
        roleplay = random.choice(expressions)
        if "{username}" in roleplay:
            roleplay = roleplay.replace("{username}", username)
    result = [
        f"<i>{roleplay}</i>",
        f"{escape_html(error_message)} 😳"
    ]
    return clean_html_entities('\n\n'.join(result))
