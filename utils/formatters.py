"""
Response formatters for Alya Bot: HTML/Markdown escaping and persona-driven message formatting.
"""

import html
import logging
import random
from typing import List, Optional, Tuple

from config.settings import (
    FORMAT_ROLEPLAY,
    FORMAT_EMOTION,
    MAX_EMOJI_PER_RESPONSE,
)
from core.persona import PersonaManager

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """Escape HTML special characters in text."""
    return html.escape(text or "")


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram's MarkdownV2 format."""
    if not text:
        return ""
    special_chars = [
        "_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|",
        "{", "}", ".", "!", "%",
    ]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def escape_markdown_v2_safe(text: str) -> str:
    """Ultra-safe escaping of MarkdownV2 special characters."""
    if not text:
        return ""
    text = str(text).replace("\\", "\\\\")
    special_chars = [
        "_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|",
        "{", "}", ".", "!", ",",
    ]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_markdown_response(
    text: str,
    username: Optional[str] = None,
    telegram_username: Optional[str] = None,
    mentioned_username: Optional[str] = None,
    mentioned_text: Optional[str] = None,
) -> str:
    """Format bot response with MarkdownV2 escaping and variable substitution."""
    if not text:
        return ""
    substitutions = {
        "{username}": username,
        "{telegram_username}": telegram_username,
        "{mentioned_username}": mentioned_username,
        "{mentioned_text}": mentioned_text,
    }
    for placeholder, value in substitutions.items():
        if value:
            text = text.replace(placeholder, escape_markdown_v2(str(value)))
    return format_response(text)
    return escape_markdown_v2(text)

def detect_roleplay(text: str) -> Tuple[str, Optional[str]]:
    """Detect and extract roleplay actions from text.
    
    This function identifies roleplay elements like *actions* or character descriptions
    and separates them from the main message.
    
    Args:
        text: Text to analyze for roleplay elements
        
    Returns:
        Tuple of (clean_text, roleplay_action)
    """
    if not text:
        return "", None
    roleplay_indicators = ["*", "[", "(", "Alya menatap", "Alya terlihat", "Alya tersenyum", 
                          "Alya menghela", "Alya menggaruk", "Alya membuang", "Alya berbisik"]
    
    lines = text.split("\n")
    roleplay_actions = []
    regular_lines = []
    
    for line in lines:
        is_roleplay = False
        if any(indicator in line for indicator in roleplay_indicators):
            if (line.startswith("*") and line.endswith("*")) or \
               (line.startswith("[") and line.endswith("]")) or \
               (line.startswith("(") and line.endswith(")")):
                roleplay_actions.append(line.strip("*[]() \t"))
                is_roleplay = True
            elif line.startswith("Alya ") and ("," in line or "." in line):
                roleplay_actions.append(line.strip())
                is_roleplay = True
        
        if not is_roleplay:
            regular_lines.append(line)
    
    if roleplay_actions:
        roleplay = "; ".join(roleplay_actions)
        roleplay = roleplay.rstrip(".,")
        roleplay = roleplay.replace("Alya, Alya", "Alya")
        clean_text = "\n".join(regular_lines).strip()
        return clean_text, roleplay
    
    return text, None


def extract_emoji_sentiment(text: str) -> Tuple[str, List[str]]:
    """Extract emojis from text and identify their sentiment."""
    import emoji
    emojis = [char for char in text if emoji.is_emoji(char)]
    if MAX_EMOJI_PER_RESPONSE > 0:
        emojis = emojis[:MAX_EMOJI_PER_RESPONSE]
    return text, emojis


def _sanitize_response(response: str, username: str) -> str:
    """Sanitize response to remove echo, self-reference, and duplicate paragraphs."""
    import difflib
    if response is None:
        return "Sorry, Alya cannot provide analysis for this content."
    
    lines = response.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        for prefix in [f"User:", f"{username}:", "Alya:", "Bot:", "Assistant:"]:
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
        cleaned_lines.append(line)
    
    response = "\n".join(cleaned_lines)
    
    if len(lines) > 1 and lines[0].strip().lower() in response.lower():
        response = "\n".join(lines[1:])
    
    paragraphs = [p.strip() for p in response.split("\n\n") if p.strip()]
    unique_paragraphs = []
    for p in paragraphs:
        if not any(_are_paragraphs_similar(p, up) for up in unique_paragraphs):
            unique_paragraphs.append(p)
    
    response = "\n\n".join(unique_paragraphs)
    
    return response


def _are_paragraphs_similar(p1: str, p2: str) -> bool:
    """Check if two paragraphs are very similar (for deduplication)."""
    import difflib
    if not p1 or not p2:
        return False
    ratio = difflib.SequenceMatcher(None, p1.lower(), p2.lower()).ratio()
    return ratio > 0.8


def get_dynamic_emojis(mood: str, message: str) -> List[str]:
    """Generate dynamic emojis based on mood and message context.
    
    Args:
        mood: Current emotional state/mood
        message: The actual message text to analyze for context
        
    Returns:
        List of contextually appropriate emojis
    """
    try:
        from core.nlp import NLPEngine
        nlp = NLPEngine()
        
        return nlp.suggest_emojis(message, mood)
    except ImportError:
        logger.debug("NLP engine unavailable for emoji selection, using basic selection")
        return _select_basic_emojis(mood)
    except Exception as e:
        logger.warning(f"Error generating dynamic emojis: {e}")
        return ["✨", "💫"]


def _select_basic_emojis(mood: str) -> List[str]:
    """Fallback method to select basic emojis when NLP isn't available.
    
    Args:
        mood: Current emotional state
        
    Returns:
        List of simple mood-appropriate emojis
    """
    positive_emojis = ["✨", "💫", "💕", "🌸", "🌟", "💖"]
    educational_emojis = ["📚", "💭", "🧠", "🎓", "📝"]
    surprised_emojis = ["😳", "⁉️", "💥", "❗", "❓"]
    negative_emojis = ["😤", "💔", "😔", "😒", "🙄"]
    
    if "academic" in mood or "serious" in mood:
        return random.sample(educational_emojis, min(2, len(educational_emojis)))
    elif "happy" in mood or "dere" in mood or "caring" in mood:
        return random.sample(positive_emojis, min(2, len(positive_emojis)))
    elif "surprised" in mood:
        return random.sample(surprised_emojis, min(2, len(surprised_emojis)))
    elif "sad" in mood or "angry" in mood or "cold" in mood:
        return random.sample(negative_emojis, min(2, len(negative_emojis)))
    else:
        all_emojis = positive_emojis + educational_emojis
        return random.sample(all_emojis, min(2, len(all_emojis)))


def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
) -> str:
    """Format a bot response with persona, mood, and expressive emoji."""
    import re
    
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)
    
    message = _sanitize_response(message, username)
    
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")
    
    message, existing_roleplay = detect_roleplay(message)
    
    paragraphs = []
    for p in message.split("\n\n"):
        if p.strip():
            paragraphs.append(p.strip())
    
    main_message = paragraphs[0] if paragraphs else message
    optional_messages = paragraphs[1:] if len(paragraphs) > 1 else []
    
    current_mood = mood if mood != "default" else emotion
    mood_emojis = get_dynamic_emojis(current_mood, message)
    
    emoji_count = min(2, MAX_EMOJI_PER_RESPONSE)
    emoji_positions = ["start", "end"][:emoji_count]
    
    roleplay = existing_roleplay
    if not roleplay and FORMAT_ROLEPLAY and "expressions" in persona.get("emotions", {}).get(
        current_mood if current_mood != "default" else "neutral", {}
    ):
        expressions = persona.get("emotions", {}).get(
            current_mood if current_mood != "default" else "neutral", {}
        ).get("expressions", [])
        if expressions:
            roleplay = random.choice(expressions)
            if "{username}" in roleplay:
                roleplay = roleplay.replace("{username}", username)
    if roleplay:
        roleplay = f"<i>{escape_html(roleplay)}</i>"
    
    main_content = re.sub(r"\*(.*?)\*", r"<i>\1</i>", main_message)
    main_content = re.sub(
        r"([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)",
        r"<b>\1</b>",
        main_content,
    )
    
    if "<i>" not in main_content and "<b>" not in main_content:
        main_content = escape_html(main_content)
    
    for position in emoji_positions:
        emoji_char = random.choice(mood_emojis)
        if position == "start":
            main_content = f"{emoji_char} {main_content}"
        elif position == "end":
            main_content = f"{main_content} {emoji_char}"
    
    formatted_optionals = []
    for opt_msg in optional_messages:
        opt_roleplay = None
        opt_text = opt_msg
        opt_clean, extracted_roleplay = detect_roleplay(opt_msg)
        if extracted_roleplay:
            opt_roleplay = extracted_roleplay
            opt_text = opt_clean
        
        if opt_roleplay:
            formatted_optionals.append(f"<i>{escape_html(opt_roleplay)}</i>")
        
        if opt_text:
            opt_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", opt_text)
            opt_text = re.sub(
                r"([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)",
                r"<b>\1</b>",
                opt_text,
            )
            if "<i>" not in opt_text and "<b>" not in opt_text:
                opt_text = escape_html(opt_text)
            formatted_optionals.append(opt_text)
    
    mood_display = None
    if mood != "default" and FORMAT_EMOTION:
        try:
            from core.nlp import NLPEngine
            nlp = NLPEngine()
            chosen = nlp.get_emotion_description(mood) or mood.replace("_", " ")
            mood_emoji = random.choice(mood_emojis)
            mood_display = f"{mood_emoji} <i>{escape_html(chosen)}</i>"
        except Exception as e:
            logger.warning(f"Failed to get emotion description: {e}")
            mood_display = None
    
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
    """Format an error response with appropriate tone."""
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
        f"<i>{escape_html(roleplay)}</i>",
        f"{escape_html(error_message)} 😳",
    ]
    return "\n\n".join(result)
