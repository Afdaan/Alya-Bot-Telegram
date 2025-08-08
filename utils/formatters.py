"""
Enterprise-grade response formatters for Alya Bot.

Handles HTML escaping, message structure, and persona-driven formatting
with deterministic output and proper error handling.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Tuple, Set
import html
import re
import emoji
import difflib
from pathlib import Path

from config.settings import (
    FORMAT_ROLEPLAY, 
    FORMAT_EMOTION,  
    MAX_EMOJI_PER_RESPONSE, 
)
from core.persona import PersonaManager

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """
    Escape HTML special characters while preserving allowed Telegram formatting tags.
    
    Args:
        text: Raw text to escape
        
    Returns:
        HTML-escaped text with Telegram formatting preserved
    """
    if not text:
        return ""
    
    # Escape all HTML first
    escaped = html.escape(text)
    
    # Preserve allowed Telegram HTML tags
    allowed_tags = ["b", "i", "u", "s", "code", "pre"]
    
    for tag in allowed_tags:
        # Restore opening tags
        escaped = re.sub(
            f"&lt;{tag}&gt;", 
            f"<{tag}>", 
            escaped, 
            flags=re.IGNORECASE
        )
        # Restore closing tags
        escaped = re.sub(
            f"&lt;/{tag}&gt;", 
            f"</{tag}>", 
            escaped, 
            flags=re.IGNORECASE
        )
    
    # Restore anchor tags with href
    escaped = re.sub(
        r"&lt;a href=['\"]([^'\"]*)['\"]&gt;", 
        r"<a href='\1'>", 
        escaped
    )
    escaped = re.sub(r"&lt;/a&gt;", r"</a>", escaped)
    
    return escaped

def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram's MarkdownV2 format.
    
    Args:
        text: Raw text to escape
        
    Returns:
        Text with special characters escaped for MarkdownV2
    """
    if not text:
        return ""
    
    # Telegram MarkdownV2 special characters
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', 
        '#', '+', '-', '=', '|', '{', '}', '.', '!', '%'
    ]
    
    # Escape backslash first to prevent double escaping
    text = text.replace('\\', '\\\\')
    
    # Escape each special character
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text


def escape_markdown_v2_safe(text: str) -> str:
    """
    Ultra-safe escaping for Telegram's MarkdownV2 format.
    
    This implementation provides comprehensive escaping based on Telegram's
    official API documentation to prevent parse errors.
    
    Args:
        text: Text to escape
        
    Returns:
        Fully escaped text safe for MarkdownV2 parsing
    """
    if not text:
        return ""
    
    text = str(text)
    
    # Complete list from Telegram API docs
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', 
        '#', '+', '-', '=', '|', '{', '}', '.', '!', ','
    ]
    
    # Escape backslash first
    text = text.replace('\\', '\\\\')
    
    # Escape all special characters
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def format_paragraphs(text: str, markdown: bool = True) -> str:
    """
    Format multi-paragraph text for Telegram with proper spacing and escaping.

    Args:
        text: The original multi-paragraph string
        markdown: Whether to escape for MarkdownV2 (True) or HTML (False)

    Returns:
        Formatted string with clear paragraph separation and safe for Telegram
    """
    if not text:
        return ""
    
    # Split paragraphs by double newlines or single newlines between text
    paragraphs = re.split(r'(?:\n\s*\n|(?<=[^\n])\n(?=[^\n]))', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    formatted = '\n\n'.join(paragraphs)
    
    if markdown:
        formatted = escape_markdown_v2(formatted)
    else:
        formatted = clean_html_entities(formatted)
    
    return formatted


def clean_html_entities(text: str) -> str:
    """
    Clean up invalid HTML tags and entities for Telegram HTML parse_mode.
    
    Args:
        text: Text with potentially malformed HTML
        
    Returns:
        Text with cleaned HTML entities and tags
    """
    if not text:
        return ""
    
    # Fix malformed tags with quotes
    text = re.sub(r'<([bius])\\">', r'<\1>', text)
    text = re.sub(r'</([bius])\\">', r'</\1>', text)
    
    # Remove stray backslashes in tags
    text = re.sub(r'<([bius])\\>', r'<\1>', text)
    text = re.sub(r'</([bius])\\>', r'</\1>', text)
    
    # Fix specific malformed patterns
    text = re.sub(r'<i\\', '<i', text)
    text = re.sub(r'</i\\', '</i', text)
    
    # Clean up tags with invalid characters
    text = re.sub(r'<([a-z]+)[^>]*>', lambda m: f"<{m.group(1)}>", text)
    text = re.sub(r'</([a-z]+)[^>]*>', lambda m: f"</{m.group(1)}>", text)
    
    return text

def format_markdown_response(
    text: str, 
    username: Optional[str] = None,
    telegram_username: Optional[str] = None,
    mentioned_username: Optional[str] = None,
    mentioned_text: Optional[str] = None,
    lang: str = "id"
) -> str:
    """
    Format bot response with proper spacing and styling for MarkdownV2.
    
    Args:
        text: Response text to format
        username: User's display name
        telegram_username: User's Telegram username
        mentioned_username: Username that was mentioned
        mentioned_text: Text that was mentioned
        lang: User's preferred language code (e.g., 'id', 'en')
        
    Returns:
        Formatted response safe for MarkdownV2 parsing
    """
    if not text:
        return ""

    # Handle variable substitutions
    substitutions = {
        '{username}': username,
        '{telegram_username}': telegram_username,
        '{mentioned_username}': mentioned_username,
        '{mentioned_text}': mentioned_text
    }
    
    # Replace variables with escaped values
    for placeholder, value in substitutions.items():
        if value:
            escaped_value = escape_markdown_v2(str(value))
            text = text.replace(placeholder, escaped_value)

    # Use main response formatter
    return format_response(text, lang=lang)


def detect_roleplay(text: str) -> Tuple[str, Optional[str]]:
    """
    Detect and extract roleplay actions from text.
    
    Recognizes common roleplay patterns: [action], *action*, (action)
    
    Args:
        text: The input text to analyze
        
    Returns:
        Tuple of (text_without_roleplay, extracted_roleplay_action)
    """
    if not text:
        return text, None
    
    # Roleplay patterns in order of preference
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
    
    return text, None


def extract_emoji_sentiment(text: str) -> Tuple[str, List[str]]:
    """
    Extract emojis from text and return them separately.
    
    Args:
        text: The input text containing emojis
        
    Returns:
        Tuple of (original_text, list_of_extracted_emojis)
    """
    if not text:
        return text, []
    
    # Find all emojis in the text
    emojis = [char for char in text if emoji.is_emoji(char)]
    
    # Limit emoji count if configured
    if MAX_EMOJI_PER_RESPONSE > 0 and len(emojis) > MAX_EMOJI_PER_RESPONSE:
        emojis = emojis[:MAX_EMOJI_PER_RESPONSE]
    
    return text, emojis

def _sanitize_response(response: str, username: str) -> str:
    """
    Sanitize response to remove echo, self-reference, and duplicate content.
    
    Args:
        response: Raw response text to clean
        username: Username to filter out from echo patterns
        
    Returns:
        Cleaned response with duplicates and echoes removed
    """
    if not response:
        return ""
    
    # Remove common prefixes from line starts
    lines = response.splitlines()
    cleaned_lines = []
    
    prefixes_to_remove = [
        "User:", 
        f"{username}:", 
        "Alya:", 
        "Bot:", 
        "Assistant:",
        "Human:",
        "AI:"
    ]
    
    for line in lines:
        line_stripped = line.strip()
        for prefix in prefixes_to_remove:
            if line_stripped.startswith(prefix):
                line = line_stripped[len(prefix):].strip()
                break
        if line.strip():  # Only keep non-empty lines
            cleaned_lines.append(line)
    
    response = "\n".join(cleaned_lines)

    # Remove echo if user input appears at start
    if len(lines) > 1 and lines[0].strip().lower() in response.lower():
        response = "\n".join(lines[1:])

    # Clean up excessive punctuation and whitespace - less aggressive
    response = re.sub(r'[.]{4,}', '...', response)  # Allow up to 3 dots
    response = re.sub(r'[!]{3,}', '!!', response)   # Allow up to 2 exclamations
    response = re.sub(r'[?]{3,}', '??', response)   # Allow up to 2 questions
    
    # Preserve paragraph structure better
    response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)  # Max 2 newlines
    response = response.strip()
    
    return response


def _split_content_intelligently(content: str) -> Tuple[str, List[str]]:
    """
    Intelligently split content into main message and optional additional parts.
    
    Args:
        content: Content to split
        
    Returns:
        Tuple of (main_content, additional_parts)
    """
    if not content or len(content) <= 150:
        return content, []
    
    # Look for natural breaks first
    if '\n\n' in content:
        parts = [p.strip() for p in content.split('\n\n') if p.strip()]
        return parts[0], parts[1:2]  # Main + max 1 additional
    
    # For very long single paragraphs, try sentence-based splitting
    if len(content) > 500:
        # Split on sentence boundaries with emotional cues
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\(])', content)
        if len(sentences) > 2:
            # Find natural break point (around 150-200 chars)
            main_sentences = []
            char_count = 0
            
            for sentence in sentences:
                if char_count + len(sentence) < 200 or not main_sentences:
                    main_sentences.append(sentence)
                    char_count += len(sentence)
                else:
                    break
            
            main_content = ' '.join(main_sentences).strip()
            remaining = ' '.join(sentences[len(main_sentences):]).strip()
            
            return main_content, [remaining] if remaining else []
    
    return content, []


def _are_paragraphs_similar(p1: str, p2: str, threshold: float = 0.8) -> bool:
    """
    Check if two paragraphs are similar enough to be considered duplicates.
    
    Args:
        p1: First paragraph
        p2: Second paragraph  
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        True if paragraphs are similar above threshold
    """
    if not p1 or not p2:
        return False
    
    ratio = difflib.SequenceMatcher(None, p1.lower(), p2.lower()).ratio()
    return ratio > threshold


def _get_mood_emojis() -> Dict[str, List[str]]:
    """
    Get comprehensive mood-based emoji mapping for natural expression.
    
    Returns:
        Dictionary mapping mood names to emoji lists
    """
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
    """
    Split text into meaningful, readable paragraphs with proper structure.
    
    Args:
        text: Raw text to split
        
    Returns:
        List of well-formatted paragraphs
    """
    if not text or not text.strip():
        return []
    
    # Clean up excessive whitespace first
    text = re.sub(r'\s+', ' ', text.strip())
    
    # For shorter responses, keep as single paragraph
    if len(text) <= 200:
        return [text]
    
    # Split by natural paragraph breaks
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # For very long single paragraphs, try sentence-based splitting
    if len(paragraphs) == 1 and len(text) > 400:
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        if len(sentences) > 3:
            # Group sentences into logical paragraphs
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
    
    # Clean and filter paragraphs
    cleaned_paragraphs = []
    for paragraph in paragraphs:
        cleaned = ' '.join(paragraph.split())
        if cleaned and len(cleaned.strip()) > 10:  # Filter very short fragments
            cleaned_paragraphs.append(cleaned)
    
    return cleaned_paragraphs


def _is_content_redundant(main_content: str, other_content: str, threshold: float = 0.95) -> bool:
    """
    Check if content is redundant compared to main content.
    
    Args:
        main_content: Primary content to compare against
        other_content: Secondary content to check for redundancy
        threshold: Similarity threshold for redundancy detection
        
    Returns:
        True if content is redundant and should be filtered out
    """
    if not main_content or not other_content:
        return True
    
    # Normalize for comparison
    main_normalized = ' '.join(main_content.lower().split())
    other_normalized = ' '.join(other_content.lower().split())
    
    # Calculate similarity
    similarity = difflib.SequenceMatcher(
        None, 
        main_normalized, 
        other_normalized
    ).ratio()
    
    # Content is redundant if very similar
    if similarity > threshold:
        return True
    
    # Check for short repetitive content
    if len(other_normalized) < 30:
        words_in_other = set(other_normalized.split())
        words_in_main = set(main_normalized.split())
        if words_in_other and words_in_main:
            overlap = len(words_in_other.intersection(words_in_main)) / len(words_in_other)
            if overlap > 0.9:  # High word overlap
                return True
    
    return False

def ensure_language(text: str, lang: str = "id") -> str:
    """
    Ensure the response is in the correct language. If not, fallback or translate.
    Args:
        text: The response text
        lang: Target language code (e.g., 'id', 'en')
    Returns:
        Text in the correct language
    """
    if not text:
        return ""
    if lang == "id":
        en_keywords = ["the", "and", "is", "are", "you", "your", "what", "can", "help", "how"]
        count_en = sum(1 for w in en_keywords if w in text.lower())
        if count_en > 2:
            return "Maaf, Alya lagi error bahasa... 😳 Coba ulangi atau ganti ke /lang id."
    elif lang == "en":
        id_keywords = ["kamu", "aku", "bisa", "apa", "saja", "bagaimana", "dengan", "kenapa"]
        count_id = sum(1 for w in id_keywords if w in text.lower())
        if count_id > 2:
            return "Sorry, Alya is having a language issue... Please try /lang en."
    return text

def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    roleplay_action: Optional[str] = None,
    russian_expression: Optional[str] = None,
    lang: str = "id",
    **kwargs
) -> str:
    """
    Format a bot response with persona, mood, and expressive elements.
    Args:
        message: Raw response text to format
        emotion: Detected emotion (neutral, happy, sad, etc.)
        mood: Persona mood state (default, tsundere, waifu, etc.)
        intensity: Emotion intensity (0.0-1.0)
        username: User's display name
        target_name: Optional target name for responses
        persona_name: Persona configuration to use
        roleplay_action: Optional roleplay action (deprecated, auto-detected)
        russian_expression: Optional Russian expression (deprecated, auto-generated)
        lang: User's preferred language code (e.g., 'id', 'en')
        **kwargs: Additional parameters for backward compatibility
    Returns:
        Formatted HTML response safe for Telegram, in user's preferred language
    """
    try:
        persona_manager = PersonaManager()
        persona = persona_manager.get_persona(persona_name)
    except Exception as e:
        logger.warning(f"Failed to load persona {persona_name}: {e}")
        persona = {}

    message = _sanitize_response(message, username)
    if not message:
        return ensure_language("Maaf, aku tidak bisa merespons sekarang... 😳", lang)

    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    message, existing_roleplay = detect_roleplay(message)

    if roleplay_action and not existing_roleplay:
        existing_roleplay = roleplay_action
        logger.warning("roleplay_action parameter is deprecated, use embedded roleplay in message instead")

    main_message, additional_parts = _split_content_intelligently(message)
    optional_messages = additional_parts[:1] if additional_parts else []

    roleplay = existing_roleplay
    if not roleplay and FORMAT_ROLEPLAY:
        try:
            persona_lang = persona.get(lang, persona.get("id", {}))
            expressions = persona_lang.get("emotions", {}).get(
                mood if mood != "default" else "neutral",
                {}
            ).get("expressions", [])
            if not expressions and lang != "id":
                expressions = persona.get("id", {}).get("emotions", {}).get(
                    mood if mood != "default" else "neutral",
                    {}
                ).get("expressions", [])
            if expressions:
                roleplay = random.choice(expressions)
                if "{username}" in roleplay:
                    roleplay = roleplay.replace("{username}", username)
        except Exception as e:
            logger.warning(f"Failed to generate roleplay: {e}")

    if roleplay:
        roleplay = f"<i>{escape_html(roleplay)}</i>"

    main_content = main_message
    main_content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', main_content)
    main_content = re.sub(
        r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)', 
        r'<b>\1</b>', 
        main_content
    )
    main_content = escape_html(main_content)

    mood_emojis = _get_mood_emojis()
    current_mood = mood if mood != "default" else "neutral"
    available_emojis = mood_emojis.get(current_mood, mood_emojis["default"])
    def has_real_emoji(text: str) -> bool:
        real_emojis = [char for char in text if emoji.is_emoji(char)]
        actual_emojis = [e for e in real_emojis if ord(e) > 0x1F000]
        return len(actual_emojis) > 0
    has_existing_emoji = has_real_emoji(main_content)
    content_length = len(main_content.strip())
    if (not has_existing_emoji and content_length > 15 and content_length < 300 and MAX_EMOJI_PER_RESPONSE > 0):
        selected_emoji = random.choice(available_emojis)
        main_content = f"{main_content.rstrip()} {selected_emoji}"

    formatted_optionals = []
    for opt_msg in optional_messages:
        opt_msg = re.sub(r'\*(.*?)\*', r'<i>\1</i>', opt_msg)
        opt_msg = escape_html(opt_msg)
        formatted_optionals.append(opt_msg)

    mood_display = None
    if mood != "default" and FORMAT_EMOTION:
        try:
            yaml_path = Path(__file__).parent.parent / "config" / "persona" / "emotion_display.yml"
            if yaml_path.exists():
                import yaml
                with open(yaml_path, "r", encoding="utf-8") as f:
                    mood_yaml = yaml.safe_load(f)
                mood_list = mood_yaml.get("moods", {}).get(mood, [])
                if not mood_list:
                    mood_list = mood_yaml.get("moods", {}).get("default", [])
                if mood_list:
                    chosen = random.choice(mood_list)
                    mood_display = f"<i>{escape_html(chosen)}</i>"
        except Exception as e:
            logger.warning(f"Failed to load emotion display: {e}")

    result_parts = []
    if roleplay:
        result_parts.append(roleplay)
    result_parts.append(main_content)
    if formatted_optionals:
        result_parts.extend(formatted_optionals)
    if mood_display:
        result_parts.append(mood_display)

    final_response = '\n\n'.join([part for part in result_parts if part and part.strip()])
    return ensure_language(clean_html_entities(final_response), lang)

def format_error_response(error_message: str, username: str = "user", lang: str = "id") -> str:
    """
    Format an error response with appropriate apologetic tone and language.
    Args:
        error_message: Error message to format
        username: User's name for personalization
        lang: User's preferred language code (e.g., 'id', 'en')
    Returns:
        Formatted HTML error response with roleplay and emotion, in user's preferred language
    """
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
            persona_lang = persona.get(lang, persona.get("id", {}))
            apologetic_mood = persona_lang.get("emotions", {}).get("apologetic_sincere", {})
            expressions = apologetic_mood.get("expressions", [])
            if not expressions and lang != "id":
                apologetic_mood = persona.get("id", {}).get("emotions", {}).get("apologetic_sincere", {})
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
        return ensure_language(clean_html_entities(final_response), lang)
    except Exception as e:
        logger.error(f"Error formatting error response: {e}")
        return ensure_language(f"Maaf, ada kesalahan {escape_html(username)}-kun... 😳", lang)