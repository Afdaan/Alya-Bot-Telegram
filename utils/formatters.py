"""
Enterprise-grade response formatters for Alya Bot.

Handles HTML escaping, message structure, and persona-driven formatting
with deterministic output and proper error handling.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
import html
import re
import emoji
import difflib
from pathlib import Path

from config.settings import (
    FORMAT_ROLEPLAY, 
    FORMAT_EMOTION,
    MAX_EMOJI_PER_RESPONSE
)
from core.persona import PersonaManager

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
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
    if not text:
        return text, []
    emojis = [char for char in text if emoji.is_emoji(char)]
    if MAX_EMOJI_PER_RESPONSE > 0 and len(emojis) > MAX_EMOJI_PER_RESPONSE:
        emojis = emojis[:MAX_EMOJI_PER_RESPONSE]
    return text, emojis

def _sanitize_response(response: str, username: str) -> str:
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
    response = response.strip()
    return response

def _get_mood_emojis() -> Dict[str, List[str]]:
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

def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    lang: str = "id",
    roleplay_action: Optional[str] = None,
    **kwargs
) -> str:
    """
    Format a bot response for Telegram. Only formats and escapes the response, does not generate
    or select roleplay/mood/expressive text. All such content must be provided by Gemini (LLM).
    Args:
        message: Main message content (should already include roleplay/mood if needed)
        emotion: Detected emotion label (for emoji injection only)
        mood: Persona mood (for emoji injection only)
        intensity: Emotion intensity (0-1)
        username: User's display name
        target_name: Optional target name for response
        persona_name: Persona config to use (for future use)
        lang: Language code (default 'id')
        roleplay_action: Optional explicit roleplay action to display (overrides detection)
    Returns:
        Formatted HTML string for Telegram
    """
    # Sanitize message first
    message = _sanitize_response(message, username)
    # Replace username/target placeholders
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")
    # Extract roleplay (if any) from message, but do NOT generate/select it here
    message, detected_roleplay = detect_roleplay(message)
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
    # Roleplay formatting: ONLY format if already present (from LLM), do NOT generate/select
    roleplay = roleplay_action or detected_roleplay
    if roleplay:
        roleplay = f"<i>{escape_html(roleplay)}</i>"
    # Emoji logic: dynamic, mood-based, natural placement
    def contains_mood_emoji(text: str, mood_emojis: List[str]) -> bool:
        return any(e in text for e in mood_emojis)
    mood_emoji_mapping = _get_mood_emojis()
    current_mood = mood if mood != "default" else "neutral"
    mood_emojis = mood_emoji_mapping.get(current_mood, mood_emoji_mapping["default"])
    emoji_count = min(MAX_EMOJI_PER_RESPONSE, 4)
    main_content = re.sub(r'\\*(.*?)\\*', r'<i>\\1</i>', main_message)
    main_content = re.sub(r'([A-ZaZ]+-kun|[A-Za-z]+-sama|[A-ZaZ]+-san|[A-ZaZ]+-chan)', r'<b>\\1</b>', main_content)
    main_content = escape_html(main_content)
    # Only inject emoji if not already present
    if not contains_mood_emoji(main_content, mood_emojis):
        positions = ["start", "end"]
        if len(main_content.split()) > 4:
            positions.append("middle")
        max_positions = min(emoji_count, len(positions))
        chosen_positions = random.sample(positions, k=max_positions)
        if emoji_count > len(positions):
            extra_positions = random.choices(positions, k=emoji_count - len(positions))
            for pos in extra_positions:
                if pos not in chosen_positions:
                    chosen_positions.append(pos)
        used_positions = set()
        for idx, pos in enumerate(chosen_positions):
            emoji_ = mood_emojis[idx % len(mood_emojis)]
            if pos == "start" and "start" not in used_positions and not main_content.startswith(emoji_):
                main_content = f"{emoji_} {main_content}"
                used_positions.add("start")
            elif pos == "end" and "end" not in used_positions and not main_content.endswith(emoji_):
                main_content = f"{main_content} {emoji_}"
                used_positions.add("end")
            elif pos == "middle" and "middle" not in used_positions:
                words = main_content.split()
                if len(words) > 2:
                    mid = len(words) // 2
                    words.insert(mid, emoji_)
                    main_content = " ".join(words)
                    used_positions.add("middle")
    # Format optionals
    formatted_optionals = []
    if optional_messages:
        opt_msg = optional_messages[0]
        opt_msg = re.sub(r'\\*(.*?)\\*', r'<i>\\1</i>', opt_msg)
        opt_msg = escape_html(opt_msg)
        formatted_optionals.append(opt_msg)
    # NO mood display, NO YAML, NO persona expressions: all handled by Gemini/LLM
    result = []
    if roleplay:
        result.append(roleplay)
    result.append(main_content)
    if formatted_optionals:
        result.extend(formatted_optionals)
    final = '\n\n'.join([r for r in result if r and r.strip()])
    return clean_html_entities(final)

def format_error_response(error_message: str, username: str = "user") -> str:
    try:
        if "{username}" in error_message:
            error_message = error_message.replace(
                "{username}", 
                f"<b>{escape_html(username)}</b>"
            )
        persona_manager = PersonaManager()
        persona = persona_manager.get_persona()
        roleplay = "terlihat bingung dan khawatir"
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
        return f"Maaf, ada kesalahan {escape_html(username)}-kun... 😳"