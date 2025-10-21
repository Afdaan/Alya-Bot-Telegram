"""
Formatter for analysis/informative responses from !ask command.

This is separate from persona formatters because analysis responses should be
rendered as plain informative content, not persona-driven conversation bubbles.
"""

from __future__ import annotations

import html
import logging
import re
from typing import List, Optional, Union

from config.settings import MAX_MESSAGE_LENGTH, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


def escape_html_for_analysis(text: str) -> str:
    """Escape HTML for Telegram, preserving safe formatting tags."""
    if not text:
        return ""

    # Preserve existing safe tags temporarily
    protected: List[tuple[str, str]] = []
    safe_tags = ["b", "i", "u", "s", "code", "pre", "a", "strong", "em"]
    
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


def _clean_response(text: str) -> str:
    """Clean up response text from meta headers and excessive formatting."""
    if not text:
        return ""
    
    # Remove invisible Unicode control characters
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]', '', text)
    
    # Remove HTML document wrapper tags (not supported by Telegram)
    # Strip <html>, <body>, <head>, <!DOCTYPE> etc.
    text = re.sub(r'(?i)<\s*!DOCTYPE[^>]*>', '', text)
    text = re.sub(r'(?i)<\s*/?\s*html[^>]*>', '', text)
    text = re.sub(r'(?i)<\s*/?\s*head[^>]*>', '', text)
    text = re.sub(r'(?i)<\s*/?\s*body[^>]*>', '', text)
    text = re.sub(r'(?i)<\s*/?\s*meta[^>]*>', '', text)
    text = re.sub(r'(?i)<\s*/?\s*title[^>]*>.*?<\s*/\s*title\s*>', '', text, flags=re.DOTALL)
    
    lines = text.splitlines()
    out: List[str] = []
    
    for ln in lines:
        s = ln.strip()
        
        # Remove meta headers like "Response:", "Analysis:", etc.
        if re.fullmatch(r"(?i)(response|analysis|answer|result)\s*:\s*", s):
            continue
        
        # Remove excessive punctuation
        s = re.sub(r"[.]{4,}", "...", s)
        s = re.sub(r"[!]{3,}", "!!", s)
        s = re.sub(r"[?]{3,}", "??", s)
        
        if s:  # Only add non-empty lines
            out.append(ln)  # Keep original indentation
    
    # Join and reduce excessive newlines
    result = "\n".join(out)
    result = re.sub(r"\n\s*\n\s*\n+", "\n\n", result)
    
    return result.strip()


def _format_markdown_to_html(text: str) -> str:
    """Convert common markdown patterns to Telegram HTML."""
    if not text:
        return ""
    
    # Code blocks: ```language\ncode``` -> <pre>code</pre>
    # Strip language identifier (html, python, etc.) from code blocks
    def format_code_block(match):
        content = match.group(1).strip()
        # Remove language identifier from first line if present
        lines = content.split('\n', 1)
        if lines and re.match(r'^[a-z]+$', lines[0].strip(), re.IGNORECASE):
            # First line is a language identifier, remove it
            content = lines[1] if len(lines) > 1 else ""
        return f"<pre>{escape_html_for_analysis(content.strip())}</pre>"
    
    text = re.sub(
        r"```([^`]+?)```",
        format_code_block,
        text,
        flags=re.DOTALL
    )
    
    # Inline code: `code` -> <code>code</code>
    text = re.sub(
        r"`([^`]+?)`",
        lambda m: f"<code>{escape_html_for_analysis(m.group(1))}</code>",
        text
    )
    
    # Bold: **text** -> <b>text</b>
    text = re.sub(
        r"\*\*([^*]+?)\*\*",
        lambda m: f"<b>{escape_html_for_analysis(m.group(1))}</b>",
        text
    )
    
    # Bold: __text__ -> <b>text</b>
    text = re.sub(
        r"__([^_]+?)__",
        lambda m: f"<b>{escape_html_for_analysis(m.group(1))}</b>",
        text
    )
    
    # Italic: *text* -> <i>text</i> (only single asterisks, not already processed)
    text = re.sub(
        r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)",
        lambda m: f"<i>{escape_html_for_analysis(m.group(1))}</i>",
        text
    )
    
    # Italic: _text_ -> <i>text</i> (only single underscores)
    text = re.sub(
        r"(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)",
        lambda m: f"<i>{escape_html_for_analysis(m.group(1))}</i>",
        text
    )
    
    return text


def _split_long_analysis(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """Split long analysis text into chunks at paragraph boundaries."""
    if len(text) <= max_length:
        return [text]
    
    paragraphs = re.split(r"\n\s*\n", text)
    parts: List[str] = []
    current = ""
    
    for para in paragraphs:
        if not para.strip():
            continue
        
        test_len = len(current) + len(para) + 2  # +2 for \n\n
        
        if test_len > max_length and current:
            parts.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    
    if current:
        parts.append(current.strip())
    
    # If still too long, split by sentences
    if any(len(p) > max_length for p in parts):
        final_parts: List[str] = []
        for part in parts:
            if len(part) <= max_length:
                final_parts.append(part)
            else:
                # Split by sentences
                sentences = re.split(r"([.!?]\s+)", part)
                current_chunk = ""
                
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    separator = sentences[i + 1] if i + 1 < len(sentences) else ""
                    
                    if len(current_chunk) + len(sentence) + len(separator) > max_length and current_chunk:
                        final_parts.append(current_chunk.strip())
                        current_chunk = sentence + separator
                    else:
                        current_chunk += sentence + separator
                
                if current_chunk:
                    final_parts.append(current_chunk.strip())
        
        return final_parts
    
    return parts


def format_analysis_response(
    text: str,
    lang: str = DEFAULT_LANGUAGE,
    username: Optional[str] = None,
) -> Union[str, List[str]]:
    """
    Format analysis/informative response from !ask command.
    
    This formatter is designed for plain informative content (articles, explanations,
    code documentation) and does NOT apply persona formatting like blockquotes or
    conversation bubbles.
    
    Args:
        text: The raw analysis text from Gemini
        lang: Language code (for potential future use)
        username: Optional username for placeholder replacement
    
    Returns:
        Formatted HTML string or list of strings if split needed
    """
    if not text or not text.strip():
        fallback = {
            "id": "Maaf, aku tidak mendapatkan hasil analisis.",
            "en": "Sorry, I couldn't get the analysis result.",
        }
        return fallback.get(lang, fallback[DEFAULT_LANGUAGE])
    
    # Clean the response
    text = _clean_response(text)
    
    # Replace username placeholder if provided
    if username and "{username}" in text:
        text = text.replace("{username}", username)
    
    # Convert markdown-style formatting to HTML
    text = _format_markdown_to_html(text)
    
    # Escape remaining HTML (outside of already processed tags)
    # We need to be careful here to not double-escape
    # The _format_markdown_to_html already escaped content inside tags
    
    # Final cleanup: reduce excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    
    # Check if splitting is needed
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text
    
    # Split into multiple messages if too long
    parts = _split_long_analysis(text)
    
    return parts[0] if len(parts) == 1 else parts


def get_analysis_fallback(lang: str = DEFAULT_LANGUAGE) -> str:
    """Get fallback message when analysis fails."""
    fallback = {
        "id": "Maaf, terjadi kesalahan saat menganalisis. Coba lagi nanti.",
        "en": "Sorry, an error occurred during analysis. Please try again later.",
    }
    return fallback.get(lang, fallback[DEFAULT_LANGUAGE])
