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

def _format_roleplay_and_actions(text: str) -> str:
    """
    Wrap *...*, _..._, [ ... ], ( ... ) and Russian (Cyrillic) phrases in <i>...</i>.
    """
    if not text:
        return ""
    # Italic for *...* or _..._ or [ ... ] or ( ... )
    text = re.sub(r"\\*(.*?)\\*", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"_(.*?)_", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"\\[(.*?)\\]", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"\\((.*?)\\)", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    # Russian (Cyrillic) phrases
    text = re.sub(r"([А-Яа-яЁё][^.,!?\n]*)", lambda m: f"<i>{m.group(1).strip()}</i>" if '<i>' not in m.group(1) else m.group(1), text)
    return text.strip()

def _split_humanlike_lines(text: str) -> List[str]:
    """
    Split text into lines, each roleplay/action (italic) or narasi satu baris.
    """
    if not text:
        return []
    # Pisah berdasarkan double newline atau newline
    lines = re.split(r'\n{2,}|\n', text)
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Pisahkan <i>...</i> ke baris sendiri
        parts = re.split(r'(<i>.*?</i>)', line)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            result.append(part)
    return result

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
    """
    Format a bot response with persona, mood, and expressive emoji. Output is valid HTML.
    Uses NLPEngine to analyze Gemini output for emotion, mood, and intensity.
    Auto-splits if output >4096 chars (Telegram limit).
    NOTE: If return type is list, handler must send each part separately (jangan lempar ke format_paragraphs).
    """
    message = _sanitize_response(message, username)
    if not message:
        return "Maaf, aku tidak bisa merespons sekarang... 😳" if lang == 'id' else "Sorry, I can't respond right now... 😳"
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    if nlp_engine is None:
        nlp_engine = NLPEngine()
    context = nlp_engine.get_message_context(message, user_id=user_id)
    mood = nlp_engine.suggest_mood_for_response(context, relationship_level)
    mood_emojis = _get_mood_emojis().get(mood if mood != "default" else "neutral", _get_mood_emojis()["default"])

    # Format: roleplay/action italic, narasi satu baris, emoji inject di narasi pertama
    lines = _split_humanlike_lines(_format_roleplay_and_actions(message))
    formatted = []
    emoji_injected = False
    for i, line in enumerate(lines):
        if not line:
            continue
        # Inject emoji di narasi pertama (bukan <i>...)</i>)
        if not emoji_injected and not line.startswith('<i>') and not any(e in line for e in mood_emojis):
            words = line.split()
            if len(words) > 2:
                pos = random.randint(1, len(words)-1)
                emoji_ = random.choice(mood_emojis)
                words.insert(pos, emoji_)
                line = " ".join(words)
            else:
                line = f"{line} {random.choice(mood_emojis)}"
            emoji_injected = True
        # Bold honorifics
        line = re.sub(r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-ZaZ]+-san|[A-Za-z]+-chan)', r'<b>\1</b>', line)
        line = escape_html(line)
        formatted.append(line)
    final = '\n\n'.join(formatted)
    final = clean_html_entities(final)
    # Split jika >4096 char
    MAX_LEN = 4096
    if len(final) <= MAX_LEN:
        return final
    parts = []
    current = ""
    for line in final.split('\n\n'):
        if len(current) + len(line) + 2 > MAX_LEN:
            if current:
                parts.append(current.strip())
            current = line
        else:
            if current:
                current += '\n\n' + line
            else:
                current = line
    if current:
        parts.append(current.strip())
    return parts

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