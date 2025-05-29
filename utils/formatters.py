"""
Response formatters for Alya Bot that handle HTML escaping and message structure.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
import html
import re
import emoji

from config.settings import (
    FORMAT_ROLEPLAY, FORMAT_EMOTION, FORMAT_RUSSIAN, 
    MAX_EMOJI_PER_RESPONSE, RUSSIAN_EXPRESSIONS
)
from core.persona import PersonaManager

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """Escape HTML special characters in text.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for HTML parsing
    """
    return html.escape(text)

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
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
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

def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu"
) -> str:
    """Format a bot response with persona, mood, and expressive emoji."""
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)

    # Replace username/target placeholders
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    # Extract roleplay and split paragraphs
    message, existing_roleplay = detect_roleplay(message)
    paragraphs = [p.strip() for p in message.split('\n\n') if p.strip()]
    main_message = paragraphs[0] if paragraphs else message
    optional_messages = paragraphs[1:2] if len(paragraphs) > 1 else []  # Limit to 1 optional

    # Emoji magic - limit to MAX_EMOJI_PER_RESPONSE per settings.py
    mood_emoji_mapping = {
        "neutral": ["✨", "💭", "🌸", "💫"],
        "happy": ["😊", "💕", "✨", "🌟"],
        "sad": ["😔", "💔", "🥺", "💧"],
        "surprised": ["😳", "⁉️", "🙀", "❗"],
        "angry": ["😤", "💢", "😠", "🔥"],
        "dere_caring": ["💕", "🥰", "💖", "✨"],
        "tsundere_cold": ["😒", "💢", "❄️", "🙄"],
        "tsundere_defensive": ["😳", "💥", "🔥", "❗"],
        "academic_serious": ["📝", "🎓", "📚", "🧐"],
        "apologetic_sincere": ["🙇‍♀️", "😔", "🙏", "💔"],
        "happy_genuine": ["🥰", "💓", "✨", "🌟"],
        "surprised_genuine": ["😳", "⁉️", "💫", "❗"],
        "default": ["✨", "💫"]
    }
    current_mood = mood if mood != "default" else "neutral"
    mood_emojis = mood_emoji_mapping.get(current_mood, mood_emoji_mapping["default"])
    emoji_count = min(MAX_EMOJI_PER_RESPONSE, max(1, random.randint(1, 2)))
    emoji_positions = ["start", "end"][:emoji_count]

    # Roleplay formatting (only once, not per paragraph)
    roleplay = existing_roleplay
    if not roleplay and FORMAT_ROLEPLAY:
        expressions = persona.get("emotions", {}).get(mood if mood != "default" else "neutral", {}).get("expressions", [])
        if expressions:
            roleplay = random.choice(expressions)
            if "{username}" in roleplay:
                roleplay = roleplay.replace("{username}", username)
    if roleplay:
        roleplay = f"<i>{escape_html(roleplay)}</i>"

    # Main message formatting
    main_content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', main_message)
    main_content = re.sub(r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)', r'<b>\1</b>', main_content)
    main_content = escape_html(main_content) if "<i>" not in main_content and "<b>" not in main_content else main_content

    # Add emojis only at start/end, respecting MAX_EMOJI_PER_RESPONSE
    for position in emoji_positions:
        emoji = random.choice(mood_emojis)
        if position == "start":
            main_content = f"{emoji} {main_content}"
        elif position == "end":
            main_content = f"{main_content} {emoji}"

    # Only 1 optional paragraph, no emoji
    formatted_optionals = []
    for opt_msg in optional_messages:
        opt_msg = re.sub(r'\*(.*?)\*', r'<i>\1</i>', opt_msg)
        opt_msg = escape_html(opt_msg) if "<i>" not in opt_msg and "<b>" not in opt_msg else opt_msg
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
        mood_emoji = random.choice(mood_emoji_mapping.get(mood, ["✨"]))
        mood_display = f"{mood_emoji} <i>{escape_html(chosen)}</i>"

    result = []
    if roleplay:
        result.append(roleplay)
    result.append(main_content)
    if formatted_optionals:
        result.extend(formatted_optionals)
    if mood_display:
        result.append(mood_display)

    return "\n\n".join(result)

def format_error_response(error_message: str, username: str = "user") -> str:
    """Format an error response with appropriate tone.
    
    Args:
        error_message: Error message to format
        username: User's name for personalization
        
    Returns:
        Formatted HTML error response
    """
    # Replace username placeholder with bold formatting
    if "{username}" in error_message:
        error_message = error_message.replace("{username}", f"<b>{escape_html(username)}</b>")
        
    # Initialize persona manager to get persona-appropriate error expressions
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona()
    
    # Get roleplay from persona if possible
    roleplay = "terlihat bingung dan khawatir"  # Default fallback
    
    # Try to get an apologetic expression from persona
    apologetic_mood = persona.get("emotions", {}).get("apologetic_sincere", {})
    expressions = apologetic_mood.get("expressions", [])
    if expressions:
        roleplay = random.choice(expressions)
        if "{username}" in roleplay:
            roleplay = roleplay.replace("{username}", username)
    
    # Format according to the specified pattern
    result = [
        f"<i>{escape_html(roleplay)}</i>",
        f"{escape_html(error_message)} 😳"
    ]
    
    return "\n\n".join(result)
