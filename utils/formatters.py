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
    """Sanitize response to remove echo and self-reference while preserving complete content."""
    if not response.strip():
        return ""
    
    # Remove conversation prefixes but preserve content
    lines = response.splitlines()
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        for prefix in [f"User:", f"{username}:", "Alya:", "Bot:", "Assistant:", "Human:", "AI:"]:
            if line_stripped.startswith(prefix):
                line_stripped = line_stripped[len(prefix):].strip()
                break
        if line_stripped:  # Only add non-empty lines
            cleaned_lines.append(line_stripped)
    
    # Join back with spaces to preserve flow
    response = " ".join(cleaned_lines)
    
    # Clean up excessive punctuation and spacing
    response = re.sub(r'[.]{3,}', '...', response)
    response = re.sub(r'[!]{2,}', '!', response)
    response = re.sub(r'[?]{2,}', '?', response)
    response = re.sub(r'\s+', ' ', response)
    
    return response.strip()

def _are_paragraphs_similar(p1: str, p2: str) -> bool:
    """Check if two paragraphs are very similar (for deduplication)."""
    if not p1 or not p2:
        return False
    ratio = difflib.SequenceMatcher(None, p1.lower(), p2.lower()).ratio()
    return ratio > 0.8

def _split_into_readable_paragraphs(text: str) -> List[str]:
    """Split text into meaningful, readable paragraphs with proper structure.
    
    Args:
        text: Raw text to split
        
    Returns:
        List of well-formatted paragraphs
    """
    if not text or not text.strip():
        return []
    
    # Clean up excessive whitespace first
    text = re.sub(r'\s+', ' ', text.strip())
    
    # For shorter responses, keep as single paragraph to avoid cutting off content
    if len(text) <= 200:
        return [text]
    
    # First, split by natural paragraph breaks (double newlines)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # If no natural breaks, try to split by sentence endings for very long text only
    if len(paragraphs) == 1 and len(text) > 400:
        # Look for sentence endings followed by capital letters (new thoughts)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        if len(sentences) > 3:
            # Group sentences into logical paragraphs (max 4 sentences per paragraph)
            grouped_paragraphs = []
            current_group = []
            for sentence in sentences:
                current_group.append(sentence.strip())
                if len(current_group) >= 4 or sentence.strip().endswith(('!', '?')):
                    grouped_paragraphs.append(' '.join(current_group))
                    current_group = []
            if current_group:
                grouped_paragraphs.append(' '.join(current_group))
            paragraphs = grouped_paragraphs
    
    # Clean up each paragraph and filter very short fragments
    cleaned_paragraphs = []
    for paragraph in paragraphs:
        # Remove excessive whitespace and line breaks within paragraphs
        cleaned = ' '.join(paragraph.split())
        if cleaned and len(cleaned.strip()) > 5:  # Less aggressive filtering
            cleaned_paragraphs.append(cleaned)
    
    return cleaned_paragraphs

def _is_content_redundant(main_content: str, other_content: str) -> bool:
    """Check if content is redundant compared to main content.
    
    Args:
        main_content: Primary content to compare against
        other_content: Secondary content to check for redundancy
        
    Returns:
        True if content is redundant and should be filtered out
    """
    if not main_content or not other_content:
        return True
        
    # Normalize both texts for comparison
    main_normalized = ' '.join(main_content.lower().split())
    other_normalized = ' '.join(other_content.lower().split())
    
    # Check similarity ratio - much less aggressive
    similarity = difflib.SequenceMatcher(None, main_normalized, other_normalized).ratio()
    
    # Content is redundant only if very similar (95%+) to avoid cutting off genuine content
    if similarity > 0.95:
        return True
        
    # Check for exact duplicates or very short repetitive content
    if len(other_normalized) < 20:  # Very short content
        words_in_other = set(other_normalized.split())
        words_in_main = set(main_normalized.split())
        overlap = len(words_in_other.intersection(words_in_main)) / len(words_in_other) if words_in_other else 0
        if overlap > 0.9:  # Almost all words already in main content
            return True
    
    return False

def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu",
    roleplay_action: Optional[str] = None,
    russian_expression: Optional[str] = None
) -> str:
    """Format a bot response with persona, mood, expressive emoji, and persona-driven roleplay/action.
    
    Creates a well-structured response with proper paragraph breaks and visual hierarchy.
    """
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)

    # Sanitize message first
    message = _sanitize_response(message, username)

    # Replace username/target placeholders with bold formatting
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")

    # Extract roleplay and intelligently split content into readable chunks
    message, existing_roleplay = detect_roleplay(message)
    
    # Split into meaningful paragraphs for better readability
    paragraphs = _split_into_readable_paragraphs(message)
    main_message = paragraphs[0] if paragraphs else message
    optional_messages = paragraphs[1:] if len(paragraphs) > 1 else []

    # Remove duplicate or very similar content - less aggressive filtering
    filtered_optionals = []
    for opt_msg in optional_messages:
        if not _is_content_redundant(main_message, opt_msg):
            filtered_optionals.append(opt_msg)
    # Allow more additional content to keep responses complete
    optional_messages = filtered_optionals[:3]  # Increased from 2 to 3

    # Enhanced roleplay formatting with better context
    roleplay = existing_roleplay
    if not roleplay and FORMAT_ROLEPLAY:
        expressions = persona.get("emotions", {}).get(mood if mood != "default" else "neutral", {}).get("expressions", [])
        if expressions:
            roleplay = random.choice(expressions)
            if "{username}" in roleplay:
                roleplay = roleplay.replace("{username}", username)
    if roleplay:
        roleplay = f"<i>{escape_html(roleplay)}</i>"

    def contains_mood_emoji(text: str, mood_emojis: List[str]) -> bool:
        """Check if any mood emoji already present in text."""
        return any(e in text for e in mood_emojis)

    # Dynamic emoji mapping by mood (moved to class level to avoid recreating every call)
    MOOD_EMOJI_MAPPING = {
        "neutral": ["✨", "💭", "🌸", "💫", "🤍", "🫧", "🌱", "🦋", "🍀", "🕊️", "🌿", "🌾", "🪴", "🌼", "🧘", "🫶"],
        "happy": ["😊", "💕", "✨", "🌟", "😄", "🥰", "😆", "🎉", "😺", "💖", "🥳", "🎈", "🦄", "🍰", "🍀", "🥂", "🤗", "😍", "😹", "🎶", "🫶"],
        "sad": ["😔", "💔", "🥺", "💧", "😭", "😢", "🌧️", "🫥", "😿", "😞", "🥲", "🫤", "🥀", "🕯️", "🫠", "😓", "😩", "🫣"],
        "surprised": ["😳", "⁉️", "🙀", "❗", "😮", "😲", "🤯", "😱", "👀", "😯", "😦", "😧", "😵", "🫢", "🫨", "🫣"],
        "angry": ["😤", "💢", "😠", "🔥", "😡", "👿", "😾", "🤬", "🗯️", "🥵", "🥊", "🧨", "💣", "😾", "🥶"],
        "embarrassed": ["😳", "😅", "💦", "🙈", "😬", "😶‍🌫️", "🫣", "🫦", "🫥", "😶"],
        "excited": ["💫", "✨", "🌟", "😳", "🤩", "🎊", "🥳", "😻", "🦄", "🎉", "🎈", "🫶", "😆", "😍", "😺", "🥰"],
        "genuinely_caring": ["🥰", "💕", "💖", "✨", "🤗", "🌷", "🫂", "💝", "🧸", "🫶", "🤍", "🌸", "🦋"],
        "defensive_flustered": ["😳", "💥", "🔥", "❗", "😤", "😒", "😡", "😾", "😬", "😑", "😏", "😼", "😹", "🫥", "🫠", "🫤", "🫣", "🫦"],
        "academic_confident": ["📝", "🎓", "📚", "🧐", "📖", "🔬", "💡", "🧠", "📊"],
        "comfortable_tsundere": ["😒", "💢", "❄️", "🙄", "😤", "😑", "😏", "😼", "😹", "🫥", "🫠", "🫤", "🫣", "🫦", "😾", "😡", "🤬"],
        "default": ["✨", "💫", "🌸", "🦋", "🤍", "🫧", "🍀", "🕊️", "🌿", "🌾", "🪴", "🌼", "🧘", "🫶"]
    }
    current_mood = mood if mood != "default" else "neutral"
    mood_emojis = MOOD_EMOJI_MAPPING.get(current_mood, MOOD_EMOJI_MAPPING["default"])
    emoji_count = min(MAX_EMOJI_PER_RESPONSE, 4)

    # Enhanced content formatting with better structure
    main_content = _format_text_content(main_message)

    # Smart emoji injection for enhanced emotional expression
    if not contains_mood_emoji(main_content, mood_emojis):
        main_content = _inject_mood_emojis(main_content, mood_emojis, emoji_count)

    # Format additional paragraphs with consistent styling
    formatted_optionals = []
    for opt_msg in optional_messages:
        formatted_opt = _format_text_content(opt_msg)
        # Add subtle emoji to secondary paragraphs (less prominent)
        if len(mood_emojis) > 1 and not contains_mood_emoji(formatted_opt, mood_emojis):
            secondary_emoji = mood_emojis[1]  # Use second emoji from mood set
            if not formatted_opt.endswith(secondary_emoji):
                formatted_opt = f"{formatted_opt} {secondary_emoji}"
        formatted_optionals.append(formatted_opt)

    # Enhanced mood display with better context
    mood_display = None
    if mood != "default" and FORMAT_EMOTION:
        mood_display = _get_mood_display(mood)

    # Build final response with proper visual hierarchy
    result_components = []
    
    # 1. Roleplay action (if present) - sets emotional context
    if roleplay:
        result_components.append(roleplay)
    
    # 2. Main content - primary message
    result_components.append(main_content)
    
    # 3. Additional paragraphs - secondary information
    if formatted_optionals:
        result_components.extend(formatted_optionals)
    
    # 4. Mood indicator (if present) - emotional state closure
    if mood_display:
        result_components.append(mood_display)

    # Join with double newlines for clear paragraph separation
    final_response = '\n\n'.join([component for component in result_components if component and component.strip()])
    
    # Final cleanup and validation
    return clean_html_entities(final_response)

def _format_text_content(text: str) -> str:
    """Apply consistent text formatting with italics and bold emphasis.
    
    Args:
        text: Raw text content
        
    Returns:
        Formatted text with HTML tags
    """
    # Convert markdown-style formatting to HTML
    formatted = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    
    # Bold Japanese honorifics for better visual appeal
    formatted = re.sub(r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)', r'<b>\1</b>', formatted)
    
    # Escape HTML for safety
    formatted = escape_html(formatted)
    
    return formatted

def _inject_mood_emojis(content: str, mood_emojis: List[str], emoji_count: int) -> str:
    """Intelligently inject mood-appropriate emojis into content.
    
    Args:
        content: Text content to enhance
        mood_emojis: List of mood-appropriate emojis
        emoji_count: Maximum number of emojis to inject
        
    Returns:
        Content with strategically placed emojis
    """
    words = content.split()
    if len(words) < 2:
        # Short content - just add emoji at end
        return f"{content} {mood_emojis[0]}"
    
    # Determine strategic positions for emoji placement
    positions = []
    
    # Always consider start and end positions
    positions.extend(["start", "end"])
    
    # Add middle position for longer content
    if len(words) > 6:
        positions.append("middle")
    
    # Add quarter positions for very long content
    if len(words) > 12:
        positions.extend(["quarter", "three_quarter"])
    
    # Select positions to use (avoid over-emoji-ing)
    max_positions = min(emoji_count, len(positions), 3)  # Cap at 3 emojis max
    selected_positions = random.sample(positions, k=max_positions)
    
    # Apply emojis at selected positions
    used_positions = set()
    for idx, position in enumerate(selected_positions):
        emoji_char = mood_emojis[idx % len(mood_emojis)]
        
        if position == "start" and "start" not in used_positions:
            if not content.startswith(emoji_char):
                content = f"{emoji_char} {content}"
                used_positions.add("start")
        elif position == "end" and "end" not in used_positions:
            if not content.endswith(emoji_char):
                content = f"{content} {emoji_char}"
                used_positions.add("end")
        elif position == "middle" and "middle" not in used_positions and len(words) > 4:
            words = content.split()
            mid_pos = len(words) // 2
            words.insert(mid_pos, emoji_char)
            content = " ".join(words)
            used_positions.add("middle")
        elif position == "quarter" and "quarter" not in used_positions and len(words) > 8:
            words = content.split()
            quarter_pos = len(words) // 4
            words.insert(quarter_pos, emoji_char)
            content = " ".join(words)
            used_positions.add("quarter")
        elif position == "three_quarter" and "three_quarter" not in used_positions and len(words) > 8:
            words = content.split()
            three_quarter_pos = (len(words) * 3) // 4
            words.insert(three_quarter_pos, emoji_char)
            content = " ".join(words)
            used_positions.add("three_quarter")
    
    return content

def _get_mood_display(mood: str) -> Optional[str]:
    """Get mood display text from emotion_display.yml.
    
    Args:
        mood: Current mood identifier
        
    Returns:
        Formatted mood display string or None
    """
    try:
        import yaml
        from pathlib import Path
        yaml_path = Path(__file__).parent.parent / "config" / "persona" / "emotion_display.yml"
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            mood_yaml = yaml.safe_load(f)
        
        mood_options = mood_yaml.get("moods", {}).get(mood, [])
        if not mood_options:
            mood_options = mood_yaml.get("moods", {}).get("default", [])
        
        if mood_options:
            chosen_display = random.choice(mood_options)
            return f"<i>{escape_html(chosen_display)}</i>"
        else:
            # Fallback to formatted mood name
            fallback = mood.replace("_", " ").title()
            return f"<i>{escape_html(fallback)}</i>"
            
    except Exception as e:
        logger.warning(f"Failed to load emotion_display.yml: {e}")
        # Fallback to formatted mood name
        fallback = mood.replace("_", " ").title()
        return f"<i>{escape_html(fallback)}</i>"

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