"""
Neutral response formatters for Alya Bot.

Handles HTML/Markdown escaping and message structure with deterministic output and
proper error handling. Keep formatting simple: conversation paragraphs are rendered
as Telegram HTML blockquotes (green bubble), roleplay is italic, and actions are bold.
"""

from __future__ import annotations

import html
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Union

import yaml

from config.settings import (
    DEFAULT_LANGUAGE,
    MAX_MESSAGE_LENGTH,
    MAX_EMOJI_PER_RESPONSE,
)

logger = logging.getLogger(__name__)


# ---------- Basic escaping ----------

def escape_html(text: str) -> str:
    """Escape HTML for Telegram, preserving safe formatting tags."""
    if not text:
        return ""

    # Preserve existing safe tags temporarily
    protected: List[tuple[str, str]] = []
    safe_tags = ["b", "i", "u", "s", "code", "pre", "blockquote", "a"]
    for tag in safe_tags:
        pattern = rf"<{tag}(?:\s[^>]*)?>.*?</{tag}>"
        for i, match in enumerate(re.findall(pattern, text, re.IGNORECASE | re.DOTALL)):
            placeholder = f"__SAFE_TAG_{tag}_{i}__"
            protected.append((placeholder, match))
            text = text.replace(match, placeholder, 1)

    escaped = html.escape(text)
    for placeholder, original in protected:
        escaped = escaped.replace(placeholder, original)
    return escaped


def escape_markdown_v2(text: str) -> str:
    """No-op for HTML mode; return original text."""
    return text or ""


# ---------- Utilities ----------

def format_paragraphs(text: str, use_html: bool = True) -> str:
    """Format text into readable paragraphs for Telegram."""
    if not isinstance(text, str):
        logger.error("format_paragraphs: input must be str, got %s", type(text))
        return ""
    if not text:
        return ""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    formatted = "\n\n".join(paragraphs)
    return escape_html(formatted) if use_html else escape_markdown_v2(formatted)


def clean_html_entities(text: str) -> str:
    """Clean malformed HTML entities/tags for Telegram HTML mode."""
    if not text:
        return ""
    # Remove attributes from tags to keep only tag name
    text = re.sub(r"<([a-z]+)[^>]*>", lambda m: f"<{m.group(1)}>", text)
    text = re.sub(r"</([a-z]+)[^>]*>", lambda m: f"</{m.group(1)}>", text)
    return text


def format_markdown_response(
    text: str,
    username: Optional[str] = None,
    telegram_username: Optional[str] = None,
    mentioned_username: Optional[str] = None,
    mentioned_text: Optional[str] = None,
) -> str:
    """Format response for MarkdownV2, with placeholder substitutions."""
    if not text:
        return ""
    subs = {
        "{username}": username,
        "{telegram_username}": telegram_username,
        "{mentioned_username}": mentioned_username,
        "{mentioned_text}": mentioned_text,
    }
    for ph, val in subs.items():
        if val:
            text = text.replace(ph, str(val))
    return format_response(text, use_html=True)


# ---------- Sanitizing ----------

def _sanitize_response(response: str, username: str) -> str:
    """Remove speaker prefixes and reduce punctuation noise."""
    if not response:
        return ""
    prefixes = ["User:", f"{username}:", "Alya:", "Bot:", "Assistant:", "Human:", "AI:"]
    s = response.strip()
    for p in prefixes:
        if s.startswith(p):
            s = s[len(p) :].strip()
            break
    s = re.sub(r"[.]{4,}", "...", s)
    s = re.sub(r"[!]{3,}", "!!", s)
    s = re.sub(r"[?]{3,}", "??", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def _get_fallback_message(lang: str = DEFAULT_LANGUAGE) -> str:
    fallback = {
        "id": "Maaf, aku tidak bisa merespons sekarang...",
        "en": "Sorry, I can't respond right now...",
    }
    return fallback.get(lang, fallback[DEFAULT_LANGUAGE])


def _preprocess_meta_lines(text: str) -> str:
    """Remove meta headers and strip "Mood:"/"Emosi:" labels to content only.

    - Remove lines like "Alya's Response:" (case-insensitive).
    - Convert lines starting with "Mood:" or "Emosi:" to plain content (no label),
      rendered later as italic via roleplay path.
    """
    if not text:
        return ""
    lines = text.splitlines()
    out: List[str] = []
    for ln in lines:
        s = ln.strip()
        if re.fullmatch(r"(?i)alya[’']?s\s+response\s*:\s*", s):
            continue
        m = re.match(r"(?i)^(mood|emosi)\s*[:：]\s*(.+)$", s)
        if m:
            content = m.group(2).strip().strip("*").strip()
            out.append(f"__{content}__")
            continue
        out.append(ln)
    return "\n".join(out)


# ---------- Main API ----------

def format_response(
    message: str,
    user_id: Optional[int] = None,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    lang: str | None = None,
    nlp_engine: Optional[Any] = None,
    relationship_level: int = 1,
    max_paragraphs: Optional[int] = 4,
    use_html: bool = True,
    **kwargs,
) -> Union[str, List[str]]:
    """Format text for Telegram with simple persona-aware rendering."""
    if lang is None:
        lang = DEFAULT_LANGUAGE

    logger.debug("Original message: %r", message)
    message = _sanitize_response(message, username)
    message = _preprocess_meta_lines(message)
    logger.debug("Message after preprocessing: %r", message)

    fallback = _get_fallback_message(lang)
    if not message or not message.strip():
        return fallback

    if "{username}" in message:
        safe_username = escape_html(username) if use_html else escape_markdown_v2(username)
        message = message.replace("{username}", safe_username)
    if target_name and "{target}" in message:
        safe_target = escape_html(target_name) if use_html else escape_markdown_v2(target_name)
        message = message.replace("{target}", safe_target)

    formatted = format_persona_response(message, max_paragraphs, use_html, lang)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted).strip()

    if len(formatted) <= MAX_MESSAGE_LENGTH:
        return formatted or fallback

    parts = _split_long_message(formatted, use_html)
    return parts[0] if len(parts) == 1 else parts


def format_persona_response(
    message: str,
    max_paragraphs: int = 4,
    use_html: bool = True,
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """Render persona response paragraphs with simple rules.

    - Paragraphs starting with '*' (action) -> bold
    - Paragraphs wrapped with __...__ (roleplay) -> italic
    - Quoted or '>' lines -> blockquote
    - Others -> blockquote (green bubble)
    """
    if not message:
        return ""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", message.strip()) if p.strip()]
    if max_paragraphs and max_paragraphs > 0:
        paragraphs = paragraphs[: max_paragraphs]

    out: List[str] = []
    for para in paragraphs:
        rendered = _format_single_paragraph(para, use_html, lang)
        if rendered:
            out.append(rendered)

    final_text = "\n\n".join(out)
    final_text = _limit_emoji_in_text(final_text, max_total=MAX_EMOJI_PER_RESPONSE)
    final_text = translate_response(final_text, lang)
    return final_text


# ---------- Detection ----------

def _contains_roleplay_elements(message: str) -> bool:
    patterns = [
        r"\*[^*]+\*",  # *action*
        r"__[^_]+__",  # __roleplay__
        r"^>",  # blockquote style
        r"```[\s\S]+?```",  # fenced code
        r"`[^`]+`",  # inline code
        r"(?i)^[\s*_]*\b(action|roleplay|italic)\b\s*[:\-—]?",  # labels (no mood)
    ]
    for pat in patterns:
        if re.search(pat, message, re.MULTILINE):
            return True
    return False


# ---------- Core formatting helpers ----------

def _split_long_message(message: str, use_html: bool) -> List[str]:
    paragraphs = re.split(r"\n\s*\n", message)
    parts: List[str] = []
    current = ""
    for para in paragraphs:
        if not para.strip():
            continue
        test_len = len(current) + len(para) + 2
        if test_len > MAX_MESSAGE_LENGTH and current:
            parts.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current:
        parts.append(current.strip())
    return parts or [_get_fallback_message(DEFAULT_LANGUAGE)]


def format_error_response(
    error_message: str,
    username: str = "user",
    lang: str = DEFAULT_LANGUAGE,
    persona_name: str = "waifu",
) -> str:
    try:
        if "{username}" in error_message:
            error_message = error_message.replace("{username}", escape_html(username))
        return clean_html_entities(error_message)
    except Exception as e:
        logger.error("Error formatting error response: %s", e)
        return _get_fallback_message(lang)


# ---------- Optional translation map ----------

@lru_cache(maxsize=2)
def _load_translation_map() -> dict:
    path = Path(__file__).parent.parent / "config" / "persona" / "translate.yml"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to load translation YAML: %s", e)
        return {}


def translate_response(text: str, lang: str = "id") -> str:
    if not text:
        return text
    translations = _load_translation_map()
    lm = translations.get(lang, {})
    for src, tgt in lm.items():
        if src and tgt and src in text:
            text = text.replace(src, tgt)
    return text


def get_translate_prompt(text: str, lang: str = "id") -> str:
    templates = _load_translation_map().get("translate_templates", {})
    prompt = templates.get(lang)
    return text if not prompt else prompt.replace("{text}", text)


# ---------- Paragraph helpers ----------

def _strip_stray_asterisks(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"^\*{2,}\s+", "", text)  # leading **  -> remove
    text = re.sub(r"\s+\*{2,}$", "", text)  # trailing ** -> remove
    return text


def _is_roleplay_text(text: str) -> bool:
    return text.startswith("__") and "__" in text[2:]


def _is_blockquote(text: str) -> bool:
    t = text.strip()
    return t.startswith(">") or (t.startswith('"') and t.endswith('"'))


def _is_code_block(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if t.startswith("```") and t.endswith("```"):
        return True
    if t.startswith("`") and t.endswith("`") and "```" not in t:
        return True
    return False


def _format_blockquote(text: str, use_html: bool) -> str:
    if text.startswith(">"):
        content = text[1:].strip()
    else:
        content = text.strip('"').strip("'")
    return f"<blockquote>{escape_html(content)}</blockquote>" if use_html else f"> {content}"


def _format_action(text: str, use_html: bool) -> str:
    # Normalize: remove leading asterisks/spaces
    t = re.sub(r"^\*+\s*", "", text.lstrip())
    # If closing '*' exists, split content and remainder
    end = t.find("*")
    if end != -1:
        content = t[:end].strip()
        remainder = t[end + 1 :].strip()
    else:
        content = t.strip("*").strip()
        remainder = ""
    if use_html:
        out = f"<b>{escape_html(content)}</b>"
        if remainder:
            out += f" {escape_html(remainder)}"
        return out
    return f"*{content}*{(' ' + remainder) if remainder else ''}"


def _format_roleplay(text: str, use_html: bool) -> str:
    t = re.sub(r"^\s*__\s*__", "__", text)  # fix broken prefix "__ __"
    end = t.find("__", 2)
    if end == -1:
        content = t.strip("_").strip()
        return f"<i>{escape_html(content)}</i>" if use_html else f"__{content}__"
    content = t[2:end].strip()
    remainder = t[end + 2 :].strip()
    if use_html:
        out = f"<i>{escape_html(content)}</i>"
        if remainder:
            out += f" {escape_html(remainder)}"
        return out
    return f"__{content}__{(' ' + remainder) if remainder else ''}"


def _format_code_block(text: str, use_html: bool) -> str:
    if text.startswith("```") and text.endswith("```"):
        content = text[3:-3].strip()
        return f"<pre>{escape_html(content)}</pre>" if use_html else f"```\n{content}\n```"
    content = text[1:-1].strip()
    return f"<code>{escape_html(content)}</code>" if use_html else f"`{content}`"


def _format_normal_text(text: str, use_html: bool) -> str:
    return f"<blockquote>{escape_html(text)}</blockquote>" if use_html else f"> {text}"


def _format_single_paragraph(para: str, use_html: bool, lang: str = DEFAULT_LANGUAGE) -> str:
    para = (para or "").strip()
    if not para:
        return ""
    para = _strip_stray_asterisks(para)

    # Headers like "** *Text" or lines starting with '*' -> action/bold
    if para.lstrip().startswith("*"):
        return _format_action(para, use_html)

    # Labeled action
    m_action = re.match(r"(?i)^\s*action\s*[:\-—]?\s*(.+)$", para)
    if m_action:
        return _format_action(m_action.group(1).strip(), use_html)

    # Roleplay paragraphs using __...__
    if _is_roleplay_text(para):
        return _format_roleplay(para, use_html)

    # Code
    if _is_code_block(para):
        return _format_code_block(para, use_html)

    # Dialog/blockquote
    if _is_blockquote(para):
        return _format_blockquote(para, use_html)

    # Default: green bubble
    return _format_normal_text(para, use_html)


# ---------- Emoji limiter ----------

def _limit_emoji_in_text(text: str, max_total: int = 15) -> str:
    pattern = re.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF]+",
        flags=re.UNICODE,
    )
    emojis = pattern.findall(text)
    if len(emojis) <= max_total:
        return text

    count = 0
    def _keep(match: re.Match) -> str:
        nonlocal count
        if count < max_total:
            count += 1
            return match.group(0)
        return ""

    return pattern.sub(_keep, text)