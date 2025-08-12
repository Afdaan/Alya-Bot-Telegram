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

from config.settings import (
    FORMAT_ROLEPLAY, 
    FORMAT_EMOTION,
    MAX_EMOJI_PER_RESPONSE
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

def _get_fallback_message(lang: str = "id") -> str:
    """Return fallback message based on language."""
    fallback_map = {
        "id": "Maaf, aku tidak bisa merespons sekarang... 😳",
        "en": "Sorry, I can't respond right now... 😳"
    }
    return fallback_map.get(lang, fallback_map["id"])

def _get_mood_emojis() -> Dict[str, List[str]]:
    """Return mapping of mood to emoji list."""
    return {
        "neutral": [
            "✨", "💭", "🌸", "💫", "🤍", "🫧", "🌱", "🦋", 
            "🍀", "🕊️", "🌿", "🌾", "🪴", "🌼", "🧘", "🫶"
        ],
        "happy": [
            "😊", "💕", "✨", "🌟", "😄", "🥰", "😆", "🎉", 
            "😺", "💖", "🥳", "🎈", "🦄", "🍰", "🍀", "🥂", 
            "🤗", "😍", "😹", "🎶", "🫶"
        ],
        "sad": [
            "😔", "💔", "🥺", "💧", "😭", "😢", "🌧️", "🫥", 
            "😿", "😞", "🥲", "🫤", "🥀", "🕯️", "🫠", "😓", 
            "😩", "🫣"
        ],
        "surprised": [
            "😳", "⁉️", "🙀", "❗", "😮", "😲", "🤯", "😱", 
            "👀", "😯", "😦", "😧", "😵", "🫢", "🫨", "🫣"
        ],
        "angry": [
            "😤", "💢", "😠", "🔥", "😡", "👿", "😾", "🤬", 
            "🗯️", "🥵", "🥊", "🧨", "💣", "😾", "🥶"
        ],
        "embarrassed": [
            "😳", "😅", "💦", "🙈", "😬", "😶‍🌫️", "🫣", "🫦", 
            "🫥", "😶", "🫠"
        ],
        "excited": [
            "💫", "✨", "🌟", "😳", "🤩", "🎊", "🥳", "😻", 
            "🦄", "🎉", "🎈", "🫶", "😆", "😍", "😺", "🥰"
        ],
        "genuinely_caring": [
            "🥰", "💕", "💖", "✨", "🤗", "🌷", "🫂", "💝", 
            "🧸", "🫶", "🤍", "🌸", "🦋", "🧑‍🤝‍🧑", "🫰", "🫱", "🫲"
        ],
        "defensive_flustered": [
            "😳", "💥", "🔥", "❗", "😤", "😒", "😡", "😾", 
            "😬", "😑", "😏", "😼", "😹", "🫥", "🫠", "🫤", 
            "🫣", "🫦"
        ],
        "academic_confident": [
            "📝", "🎓", "📚", "🧐", "📖", "🔬", "💡", "🧠", 
            "📊", "🧑‍💻", "🧑‍🔬", "🧑‍🏫", "🧬", "🧪", "🧭", 
            "🧮", "🧰", "🧱", "🧲", "🧑‍🎓"
        ],
        "comfortable_tsundere": [
            "😒", "💢", "❄️", "🙄", "😤", "😑", "😏", "😼", 
            "😹", "🫥", "🫠", "🫤", "🫣", "🫦", "😾", "😡", "🤬"
        ],
        "default": [
            "✨", "💫", "🌸", "🦋", "🤍", "🫧", "🍀", "🕊️", 
            "🌿", "🌾", "🪴", "🌼", "🧘", "🫶"
        ]
    }

def _split_into_readable_paragraphs(text: str) -> List[str]:
    """Split long text into readable paragraphs."""
    if not text or not text.strip():
        return []
    text = re.sub(r'\s+', ' ', text.strip())
    if len(text) <= 200:
        return [text]
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) == 1 and len(text) > 400:
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        if len(sentences) > 3:
            grouped_paragraphs = []
            current_group = []
            for sentence in sentences:
                current_group.append(sentence.strip())
                if len(current_group) >= 3 or sentence.strip().endswith(('!', '?')):
                    grouped_paragraphs.append(' '.join(current_group))
                    current_group = []
            if current_group:
                grouped_paragraphs.append(' '.join(current_group))
            paragraphs = grouped_paragraphs
    cleaned_paragraphs = []
    for paragraph in paragraphs:
        cleaned = ' '.join(paragraph.split())
        if cleaned and len(cleaned.strip()) > 10:
            cleaned_paragraphs.append(cleaned)
    return cleaned_paragraphs

def _format_roleplay_and_actions(text: str) -> str:
    """Format roleplay actions more naturally."""
    if not text:
        return ""
    
    # Convert roleplay markers to italic, but keep them more natural
    text = re.sub(r"\*(.*?)\*", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"_(.*?)_", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"\[(.*?)\]", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    
    # Handle Russian text more naturally
    text = re.sub(r"([А-Яа-яЁё][А-Яа-яЁё\s]*[А-Яа-яЁё])", 
                  lambda m: f"<i>{m.group(1).strip()}</i>" if '<i>' not in m.group(1) else m.group(1), 
                  text)
    
    return text.strip()

def _split_humanlike_lines(text: str) -> List[str]:
    """Split text into natural conversation flow."""
    if not text:
        return []
    
    # Split by double newlines first (natural paragraph breaks)
    paragraphs = re.split(r'\n\s*\n', text.strip())
    result = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Keep dialogue and narration together more naturally
        # Only split if there's a clear action -> dialogue transition
        if '<i>' in paragraph and '"' in paragraph:
            # Mixed action and dialogue - keep together for flow
            result.append(paragraph)
        else:
            # Pure dialogue or pure action
            result.append(paragraph)
    
    return result

def _get_contextual_emoji(text: str, mood: str, relationship_level: int) -> str:
    """Get contextually appropriate emoji based on content and mood."""
    text_lower = text.lower()
    
    # Emotional context detection
    if any(word in text_lower for word in ['khawatir', 'cemas', 'takut', 'was-was']):
        return random.choice(['😰', '🥺', '😟', '💔', '😔'])
    elif any(word in text_lower for word in ['maaf', 'sorry', 'minta maaf']):
        return random.choice(['😔', '🥺', '😢', '💔'])
    elif any(word in text_lower for word in ['senang', 'gembira', 'bahagia', 'suka']):
        return random.choice(['😊', '🥰', '😄', '💕', '✨'])
    elif any(word in text_lower for word in ['marah', 'kesal', 'jengkel']):
        return random.choice(['😤', '💢', '😠', '🔥'])
    elif any(word in text_lower for word in ['malu', 'embarrass', 'blush']):
        return random.choice(['😳', '😅', '🙈', '💦'])
    elif any(word in text_lower for word in ['kaget', 'surprised', 'shock']):
        return random.choice(['😳', '😲', '🙀', '😱'])
    
    # Relationship-based defaults
    if relationship_level >= 3:
        return random.choice(['💕', '🥰', '😊', '✨', '🌸'])
    else:
        return random.choice(['😊', '🌸', '✨', '🦋'])

def format_response(
    message: str,
    user_id: Optional[int] = None,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    lang: str = "id",
    nlp_engine: Optional[NLPEngine] = None,
    relationship_level: int = 1,
    **kwargs
) -> Union[str, List[str]]:
    """Format a bot response with natural, human-like flow, persona-driven mood, and language fallback."""
    message = _sanitize_response(message, username)
    fallback = _get_fallback_message(lang)
    if not message or not message.strip():
        return fallback

    # Handle username placeholders
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    # Persona & mood context
    if nlp_engine is None:
        nlp_engine = NLPEngine()
    context = nlp_engine.get_message_context(message, user_id=user_id)
    mood = nlp_engine.suggest_mood_for_response(context, relationship_level)
    # Get emoji pool from NLP engine (contextual, not hardcoded)
    emoji_pool = nlp_engine.suggest_emojis(message, mood, count=min(MAX_EMOJI_PER_RESPONSE, 3))
    # Russian expressions (for tsundere/emosi)
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name=persona_name, lang=lang)
    russian_expressions = persona.get("russian_expressions", ["дурак", "что", "глупый", "бaka"])

    # Format roleplay elements
    formatted_text = _format_roleplay_and_actions(message)
    # Split into paragraphs/lines
    lines = _split_humanlike_lines(formatted_text)

    processed_lines = []
    emoji_count = 0
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        # Escape HTML
        line = escape_html(line)
        # Bold honorifics
        line = re.sub(r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)', r'<b>\1</b>', line)
        # Inject Russian exp randomly if mood tsundere/angry/embarrassed
        if mood in ("defensive_flustered", "comfortable_tsundere", "angry", "embarrassed") and random.random() < 0.25:
            rus = random.choice(russian_expressions)
            line = f"{line} <i>{rus}</i>"
        # Add emoji at natural spots (end of para, or after roleplay)
        if emoji_count < len(emoji_pool) and (line.endswith(('.', '!', '?')) or idx == len(lines)-1):
            emoji_to_add = emoji_pool[emoji_count]
            line = f"{line} {emoji_to_add}"
            emoji_count += 1
        processed_lines.append(line)

    # Gabung dengan spasi natural
    final = '\n\n'.join([l for l in processed_lines if l.strip()])
    final = clean_html_entities(final)

    # Handle splitting if too long
    MAX_LEN = 4096
    if len(final) <= MAX_LEN:
        return final if final.strip() else fallback
    # Split naturally at paragraph boundaries
    parts = []
    current = ""
    for line in final.split('\n\n'):
        if not line.strip():
            continue
        if len(current) + len(line) + 2 > MAX_LEN:
            if current.strip():
                parts.append(current.strip())
            current = line
        else:
            current = current + '\n\n' + line if current else line
    if current.strip():
        parts.append(current.strip())
    parts = [p for p in parts if p.strip()]
    if not parts:
        return fallback
    return parts[0] if len(parts) == 1 else parts

def format_error_response(error_message: str, username: str = "user", lang: str = "id") -> str:
    """Format error response with persona and apology, following language preference."""
    try:
        if "{username}" in error_message:
            error_message = error_message.replace(
                "{username}", 
                f"<b>{escape_html(username)}</b>"
            )
        persona_manager = PersonaManager()
        persona = persona_manager.get_persona(lang=lang)
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