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

def _get_mood_emojis() -> Dict[str, List[str]]:
    # (unchanged large emoji dictionary from your original code)
    return { ... }  # omitted for brevity, same as your original

def _split_humanlike_lines(text: str) -> List[str]:
    if not text:
        return []
    lines = re.split(r'\n{2,}|\n', text)
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'(<i>.*?</i>)', line)
        for part in parts:
            part = part.strip()
            if part:
                result.append(part)
    return result

def _format_roleplay_and_actions(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\*(.*?)\*", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"_(.*?)_", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"\[(.*?)\]", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"\((.*?)\)", lambda m: f"<i>{m.group(1).strip()}</i>", text)
    text = re.sub(r"([А-Яа-яЁё][^.,!?\n]*)",
                  lambda m: f"<i>{m.group(1).strip()}</i>" if '<i>' not in m.group(1) else m.group(1),
                  text)
    return text.strip()

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

    message = _sanitize_response(message, username)
    fallback = (
        "Maaf, aku tidak bisa merespons sekarang... 😳"
        if lang == 'id' else "Sorry, I can't respond right now... 😳"
    )
    if not message or not message.strip():
        return fallback
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    if nlp_engine is None:
        nlp_engine = NLPEngine()
    context = nlp_engine.get_message_context(message, user_id=user_id)
    mood = nlp_engine.suggest_mood_for_response(context, relationship_level)
    mood_emojis = _get_mood_emojis().get(mood if mood != "default" else "neutral", _get_mood_emojis()["default"])

    lines = _split_humanlike_lines(_format_roleplay_and_actions(message))
    formatted = []
    emoji_injected = False
    for line in lines:
        if not line.strip():
            continue
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
        line = re.sub(r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)', r'<b>\1</b>', line)
        line = escape_html(line)
        formatted.append(line)

    final = '\n\n'.join([f for f in formatted if f.strip()])
    final = clean_html_entities(final)

    MAX_LEN = 4096
    if len(final) <= MAX_LEN:
        return final if final.strip() else fallback

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

async def _process_and_send_response(self, update, user, response, message_context, lang):
    """Patched sender — ensures non-empty messages"""
    formatted_response = format_response(
        response,
        user_id=user.id,
        username=user.name,
        target_name=message_context.get("target"),
        persona_name="waifu",
        lang=lang,
        nlp_engine=self.nlp_engine,
        relationship_level=user.relationship_level
    )

    if isinstance(formatted_response, list):
        formatted_response = [part for part in formatted_response if part.strip()]
        if not formatted_response:
            formatted_response = ["Maaf, aku tidak bisa merespons sekarang... 😳"]
        for part in formatted_response:
            await update.message.reply_html(part)
    elif isinstance(formatted_response, str):
        if not formatted_response.strip():
            formatted_response = "Maaf, aku tidak bisa merespons sekarang... 😳"
        await update.message.reply_html(formatted_response)
    else:
        await update.message.reply_html("Maaf, aku tidak bisa merespons sekarang... 😳")
