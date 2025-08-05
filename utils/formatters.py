"""
Natural response formatters for Alya Bot - Enterprise-grade conversation formatting.
Designed to create human-like, emotionally intelligent responses.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Tuple, Set
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
    """Escape HTML special characters safely for Telegram."""
    if not text:
        return ""
    
    # Escape everything first
    escaped = html.escape(text)
    
    # Restore allowed HTML tags for Telegram
    allowed_patterns = [
        (r"&lt;b&gt;", "<b>"),
        (r"&lt;/b&gt;", "</b>"),
        (r"&lt;i&gt;", "<i>"),
        (r"&lt;/i&gt;", "</i>"),
        (r"&lt;u&gt;", "<u>"),
        (r"&lt;/u&gt;", "</u>"),
        (r"&lt;s&gt;", "<s>"),
        (r"&lt;/s&gt;", "</s>"),
        (r"&lt;code&gt;", "<code>"),
        (r"&lt;/code&gt;", "</code>"),
        (r"&lt;pre&gt;", "<pre>"),
        (r"&lt;/pre&gt;", "</pre>"),
    ]
    
    for pattern, replacement in allowed_patterns:
        escaped = re.sub(pattern, replacement, escaped, flags=re.IGNORECASE)
    
    # Handle <a href="..."> tags
    escaped = re.sub(r"&lt;a href=['\"]([^'\"]*)['\"]&gt;", r"<a href='\1'>", escaped)
    escaped = re.sub(r"&lt;/a&gt;", "</a>", escaped)
    
    return escaped

def escape_markdown_v2_safe(text: str) -> str:
    """Ultra-safe MarkdownV2 escaping for Telegram."""
    if not text:
        return ""
    
    text = str(text)
    
    # Escape backslash first
    text = text.replace('\\', '\\\\')
    
    # Complete list of MarkdownV2 special characters
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', 
                    '-', '=', '|', '{', '}', '.', '!', ',']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def escape_markdown_v2(text: str) -> str:
    """Alias for escape_markdown_v2_safe for backward compatibility."""
    return escape_markdown_v2_safe(text)

def clean_html_entities(text: str) -> str:
    """Clean malformed HTML for Telegram compatibility."""
    if not text:
        return ""
        
    # Fix broken tag quotes and backslashes
    text = re.sub(r'<([bius])\\"?>', r'<\1>', text)
    text = re.sub(r'</([bius])\\"?>', r'</\1>', text)
    
    # Remove unsupported attributes from tags
    text = re.sub(r'<([a-z]+)[^>]*?>', lambda m: f"<{m.group(1)}>", text)
    text = re.sub(r'</([a-z]+)[^>]*?>', lambda m: f"</{m.group(1)}>", text)
    
    return text

class ConversationFormatter:
    """Natural conversation formatter with contextual awareness."""
    
    # Context-aware emoji selection based on emotional state and conversation flow
    EMOTION_CONTEXT_EMOJIS = {
        "neutral": ["💭", "✨", "🌸"],
        "happy": ["😊", "💕", "🌟"],
        "excited": ["😆", "🎉", "💫"],
        "shy": ["😳", "💦", "🙈"],
        "nervous": ["😅", "🫣", "😶"],
        "tsundere": ["😤", "💢", "🙄"],
        "defensive": ["😤", "💢", "❄️"],
        "flustered": ["😡", "💥", "😾"],
        "caring": ["🥰", "💕", "🌸"],
        "gentle": ["🤗", "💖", "🫂"],
        "surprised": ["😲", "✨", "👀"],
        "shocked": ["😱", "⚡", "🤯"],
        "embarrassed": ["😳", "😅", "🙈"],
        "comfortable_tsundere": ["😒", "😏", "😼"],
        "genuinely_caring": ["🥰", "💖", "🌷"],
        "academic_confident": ["📝", "🎓", "💡"]
    }

    @staticmethod
    def preserve_conversation_flow(text: str) -> str:
        """Preserve natural conversation flow without aggressive splitting."""
        if not text.strip():
            return ""
        
        # Only split on very clear paragraph breaks (double newlines)
        natural_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # If no natural breaks, keep as single flowing text
        if len(natural_paragraphs) <= 1:
            # Clean up internal spacing but preserve flow
            cleaned = ' '.join(text.split())
            return cleaned
        
        # Join with single paragraph break for readability
        return '\n\n'.join(natural_paragraphs)

    @staticmethod
    def intelligent_emoji_placement(text: str, emotion: str, mood: str, intensity: float = 0.5) -> str:
        """Place emojis naturally based on conversation context and emotional flow."""
        if not text.strip():
            return text
            
        formatter = ConversationFormatter()
        
        # Determine best emoji set based on mood first, then emotion
        emoji_key = mood if mood != "default" else emotion
        if emoji_key not in formatter.EMOTION_CONTEXT_EMOJIS:
            emoji_key = "neutral"  # Safe fallback
        
        emojis = formatter.EMOTION_CONTEXT_EMOJIS[emoji_key]
        
        # Smart placement based on text length and structure
        words = text.split()
        word_count = len(words)
        
        # Limit emoji count based on settings
        max_emojis = min(MAX_EMOJI_PER_RESPONSE, 2) if MAX_EMOJI_PER_RESPONSE > 0 else 2
        
        if word_count <= 5:
            # Very short - one emoji at end
            return f"{text} {emojis[0]}"
        elif word_count <= 15:
            # Short - emoji at start and end if we have 2+ emojis allowed
            if max_emojis >= 2 and len(emojis) > 1:
                return f"{emojis[0]} {text} {emojis[1]}"
            else:
                return f"{text} {emojis[0]}"
        else:
            # Longer text - strategic placement at natural break points
            sentences = re.split(r'([.!?])\s+', text)
            if len(sentences) >= 3 and max_emojis >= 2:
                # Multiple sentences - place emoji after first sentence
                first_sentence = sentences[0] + (sentences[1] if len(sentences) > 1 else "")
                rest = "".join(sentences[2:]) if len(sentences) > 2 else ""
                if rest:
                    return f"{emojis[0]} {first_sentence} {emojis[1] if len(emojis) > 1 else emojis[0]} {rest}"
                else:
                    return f"{emojis[0]} {first_sentence} {emojis[1] if len(emojis) > 1 else emojis[0]}"
            else:
                # Single long sentence or limited emojis - just at end
                return f"{text} {emojis[0]}"

def extract_roleplay_action(text: str) -> Tuple[str, Optional[str]]:
    """Extract roleplay actions naturally from text."""
    # Look for action indicators in various formats
    action_patterns = [
        r'^\s*\[(.*?)\]\s*',     # [action]
        r'^\s*\*(.*?)\*\s*',     # *action*
        r'^\s*\((.*?)\)\s*',     # (action)
    ]
    
    for pattern in action_patterns:
        match = re.search(pattern, text)
        if match:
            action = match.group(1).strip()
            cleaned_text = re.sub(pattern, '', text).strip()
            return cleaned_text, action
    
    return text, None

def sanitize_conversation_response(response: str, username: str) -> str:
    """Clean response from AI artifacts while preserving natural flow."""
    if not response.strip():
        return ""
    
    lines = response.splitlines()
    cleaned_lines = []
    
    # Remove conversation prefixes but preserve content
    prefixes_to_remove = [
        "User:", f"{username}:", "Alya:", "Bot:", "Assistant:", 
        "Human:", "AI:", "Response:", "Answer:"
    ]
    
    for line in lines:
        line_stripped = line.strip()
        for prefix in prefixes_to_remove:
            if line_stripped.startswith(prefix):
                line_stripped = line_stripped[len(prefix):].strip()
                break
        if line_stripped:  # Only add non-empty lines
            cleaned_lines.append(line_stripped)
    
    # Join back with spaces to preserve flow
    response = " ".join(cleaned_lines)
    
    # Less aggressive deduplication - only remove if 95%+ similar
    sentences = re.split(r'(?<=[.!?])\s+', response)
    unique_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        is_duplicate = any(
            difflib.SequenceMatcher(None, sentence.lower(), existing.lower()).ratio() > 0.95
            for existing in unique_sentences
        )
        if not is_duplicate:
            unique_sentences.append(sentence)
    
    return " ".join(unique_sentences)

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
    """Create natural, complete conversation responses with emotional intelligence."""
    
    if not message.strip():
        return ""
    
    # Initialize components
    formatter = ConversationFormatter()
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)
    
    # Sanitize but preserve flow
    message = sanitize_conversation_response(message, username)
    
    # Handle variable substitution
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")
    
    # Extract roleplay action
    message, existing_roleplay = extract_roleplay_action(message)
    
    # Preserve conversation flow - don't split aggressively
    formatted_message = formatter.preserve_conversation_flow(message)
    
    # Apply intelligent emoji placement
    message_with_emojis = formatter.intelligent_emoji_placement(
        formatted_message, emotion, mood, intensity
    )
    
    # Build response components
    response_parts = []
    
    # 1. Roleplay action (emotional/physical context)
    roleplay = existing_roleplay or roleplay_action
    if not roleplay and FORMAT_ROLEPLAY:
        # Get persona-appropriate roleplay
        mood_key = mood if mood != "default" else "neutral"
        mood_data = persona.get("emotions", {}).get(mood_key, {})
        expressions = mood_data.get("expressions", [])
        if expressions:
            roleplay = random.choice(expressions)
            if "{username}" in roleplay:
                roleplay = roleplay.replace("{username}", username)
    
    if roleplay:
        response_parts.append(f"<i>{escape_html(roleplay)}</i>")
    
    # 2. Main conversation content (complete and natural)
    response_parts.append(escape_html(message_with_emojis))
    
    # 3. Russian expression (if appropriate and emotional)
    if russian_expression and FORMAT_RUSSIAN:
        response_parts.append(f"<i>{escape_html(russian_expression)}</i>")
    
    # 4. Mood indicator (only if very relevant and high intensity)
    if mood != "default" and FORMAT_EMOTION and intensity > 0.7:
        mood_display = _get_contextual_mood_display(mood)
        if mood_display:
            response_parts.append(mood_display)
    
    # Combine with natural conversation flow
    final_response = "\n\n".join([part for part in response_parts if part and part.strip()])
    
    return clean_html_entities(final_response)

def _get_contextual_mood_display(mood: str) -> Optional[str]:
    """Get contextually appropriate mood display."""
    try:
        import yaml
        from pathlib import Path
        
        yaml_path = Path(__file__).parent.parent / "config" / "persona" / "emotion_display.yml"
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            mood_data = yaml.safe_load(f)
        
        mood_options = mood_data.get("moods", {}).get(mood, [])
        if not mood_options:
            return None  # Don't show fallback mood display
        
        chosen_display = random.choice(mood_options)
        return f"<i>{escape_html(chosen_display)}</i>"
            
    except Exception as e:
        logger.warning(f"Failed to load emotion_display.yml: {e}")
        return None

def format_error_response(error_message: str, username: str = "user") -> str:
    """Format error responses with natural, caring tone."""
    if not error_message:
        return ""
        
    if "{username}" in error_message:
        error_message = error_message.replace("{username}", f"<b>{escape_html(username)}</b>")
    
    # Natural roleplay for errors
    caring_actions = [
        "terlihat khawatir dan ingin membantu",
        "menggelengkan kepala dengan lembut", 
        "menghela napas dan tersenyum maaf",
        "menatap dengan mata berbinar khawatir"
    ]
    
    selected_action = random.choice(caring_actions)
    
    response_parts = [
        f"<i>{selected_action}</i>",
        f"{escape_html(error_message)} 😔💦"
    ]
    
    return clean_html_entities("\n\n".join(response_parts))

# Legacy compatibility functions
def format_markdown_response(
    text: str,
    username: Optional[str] = None,
    telegram_username: Optional[str] = None,
    mentioned_username: Optional[str] = None,
    mentioned_text: Optional[str] = None
) -> str:
    """Legacy compatibility wrapper for markdown responses."""
    return format_response(text or "", username=username or "user")

def format_paragraphs(text: str, markdown: bool = True) -> str:
    """Format paragraphs with natural flow preservation."""
    formatter = ConversationFormatter()
    formatted = formatter.preserve_conversation_flow(text)
    return escape_html(formatted) if not markdown else escape_markdown_v2_safe(formatted)
