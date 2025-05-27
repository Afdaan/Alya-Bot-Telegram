"""
Response formatters for Alya Bot that handle HTML escaping and message structure.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
import html
import re
import emoji

from config.settings import (
    FORMAT_ROLEPLAY, FORMAT_EMOTION, FORMAT_RUSSIAN, 
    MAX_EMOJI_PER_RESPONSE, RUSSIAN_EXPRESSIONS
)
from core.persona import PersonaManager

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """Escape HTML special characters in text.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for HTML parsing
    """
    return html.escape(text)

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
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Escape each special character with a backslash
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
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

def format_response(
    message: str,
    emotion: str = "neutral",
    mood: str = "default",
    intensity: float = 0.5,
    username: str = "user",
    target_name: Optional[str] = None,
    persona_name: str = "waifu"
) -> str:
    """Format a bot response with proper structure and HTML formatting.
    
    Args:
        message: The main message content
        emotion: Detected or assigned emotion
        mood: Selected mood for response
        intensity: Emotional intensity (0.0-1.0)
        username: User's name for personalization
        target_name: Target name for roasting (if applicable)
        persona_name: Name of persona to use for roleplay and mood
        
    Returns:
        Formatted HTML response according to persona settings
    """
    # Initialize PersonaManager if not already instantiated
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)
    
    # Replace username and target placeholders if not already formatted with HTML
    if "{username}" in message:
        message = message.replace("{username}", f"<b>{escape_html(username)}</b>")
    if target_name and "{target}" in message:
        message = message.replace("{target}", f"<b>{escape_html(target_name)}</b>")
    
    # Extract existing roleplay if any
    message, existing_roleplay = detect_roleplay(message)
    
    # Split message into paragraphs for cleaner formatting
    paragraphs = message.split('\n\n')
    
    # Determine if we should keep it short or allow multiple paragraphs
    allow_multiple_paragraphs = (
        intensity > 0.7 or 
        mood in ["apologetic_sincere", "academic_serious"] or
        emotion in ["anger", "surprise"]
    )
    
    # Limit to first paragraph unless we allow multiple
    if not allow_multiple_paragraphs and len(paragraphs) > 1:
        main_message = paragraphs[0]
        optional_messages = []
    else:
        # Even with multiple paragraphs, limit to at most 3 for conciseness
        main_message = paragraphs[0]
        optional_messages = paragraphs[1:3] if len(paragraphs) > 1 else []
    
    # Extract existing emojis from main message
    _, extracted_emojis = extract_emoji_sentiment(main_message)
    
    # ===== PERSONA-DRIVEN CONTENT =====
    # Get roleplay actions from persona file instead of hardcoded dictionaries
    if not existing_roleplay and FORMAT_ROLEPLAY:
        # Get roleplay action from persona emotions section
        emotions_data = persona.get("emotions", {})
        mood_data = emotions_data.get(mood if mood != "default" else "neutral", {})
        
        if not mood_data and emotion != "neutral":
            # Fall back to emotion-based lookup
            for persona_mood, mood_data in emotions_data.items():
                if emotion in persona_mood.lower():
                    break
        
        # Get expressions from mood data
        expressions = mood_data.get("expressions", [])
        if expressions:
            roleplay = random.choice(expressions)
            if "{username}" in roleplay:
                roleplay = roleplay.replace("{username}", username)
        else:
            # Fallback when no expressions found for this mood/emotion
            roleplay = f"menatap {username}"
    else:
        roleplay = existing_roleplay
        if roleplay and "{username}" in roleplay:
            roleplay = roleplay.replace("{username}", username)
    
    # Get emoji based on persona
    if not extracted_emojis and emotion != "neutral" and FORMAT_EMOTION:
        # Look for emojis in persona file for this mood/emotion
        emoji_options = []
        for persona_mood, mood_data in persona.get("emotions", {}).items():
            if emotion in persona_mood.lower() or mood in persona_mood.lower():
                emoji_options = mood_data.get("emoji", [])
                break
        
        # Add emoji if found in persona
        if emoji_options:
            selected_emoji = random.choice(emoji_options)
            # Don't escape emojis
            main_message = f"{main_message} {selected_emoji}"
    
    # Process Russian expressions
    russian_expr = None
    romaji = None
    if FORMAT_RUSSIAN and random.random() < 0.3:  # Only add Russian 30% of the time
        russian_triggers = []
        
        # Try to find Russian expressions for this mood/emotion
        for persona_mood, mood_data in persona.get("emotions", {}).items():
            if emotion in persona_mood.lower() or mood in persona_mood.lower():
                russian_triggers = mood_data.get("russian_triggers", [])
                break
        
        # If found in persona, get a random expression
        if russian_triggers:
            russian_expr = random.choice(russian_triggers) if russian_triggers else None
            if russian_expr:
                # Look up romaji from global config if available
                for emotion_key, expressions in RUSSIAN_EXPRESSIONS.items():
                    if russian_expr in expressions.get("expressions", []):
                        idx = expressions["expressions"].index(russian_expr)
                        romaji = expressions["romaji"][idx] if idx < len(expressions["romaji"]) else None
                        break
    
    # Generate mood display based on persona language data
    mood_display = None
    if mood != "default" and FORMAT_EMOTION:
        # Try to find an appropriate mood description in persona data
        persona_moods = persona.get("emotions", {})
        for persona_mood, mood_data in persona_moods.items():
            if mood in persona_mood.lower():
                responses = mood_data.get("responses", [])
                if responses:
                    # Take a random action description from the first response
                    response = random.choice(responses)
                    # Extract a mood action from the response
                    mood_matches = re.search(r"(sedang|sambil|dengan)\s+([^,.!?]+)", response)
                    if mood_matches:
                        mood_display = mood_matches.group(0)
                    break
                    
        # Fallback for mood display if nothing found
        if not mood_display:
            mood_descriptions = {
                "tsundere_cold": "sedang bersikap dingin",
                "tsundere_defensive": "menjadi defensif",
                "dere_caring": "menunjukkan kepedulian",
                "academic_serious": "dalam mode serius",
                "surprised_genuine": "terkejut sungguhan",
                "happy_genuine": "terlihat bahagia",
                "apologetic_sincere": "merasa menyesal"
            }
            mood_display = mood_descriptions.get(mood, mood.replace("_", " "))
    
    # Build the formatted response with proper HTML tags
    result = []
    
    # 1. Add roleplay in italic if present
    if roleplay:
        result.append(f"<i>{escape_html(roleplay)}</i>")
    
    # 2. Add main message with Russian expression if present
    main_content = main_message
    if russian_expr:
        # Insert Russian expression with italic formatting
        if romaji:
            main_content = main_content.replace("*Что ты говоришь?!*", f"<i>{russian_expr}</i> ({romaji})")
            main_content = main_content.replace(f"*{russian_expr}*", f"<i>{russian_expr}</i> ({romaji})")
        
        # Process any remaining *text* patterns as italic
        main_content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', main_content)
    else:
        # Process *text* patterns as italic
        main_content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', main_content)
    
    # Apply bold formatting for name emphasis, preserving italic tags
    main_content = re.sub(r'([A-Za-z]+-kun|[A-Za-z]+-sama|[A-Za-z]+-san|[A-Za-z]+-chan)', r'<b>\1</b>', main_content)
    
    # Ensure we're not double-escaping after applying formatting
    if "<i>" in main_content or "<b>" in main_content:
        # Don't escape content that already has HTML tags
        result.append(main_content)
    else:
        # Escape regular content
        result.append(escape_html(main_content))
    
    # 3. Add optional messages (limited to keep responses shorter)
    for opt_msg in optional_messages:
        if opt_msg.strip():
            # Process *text* patterns as italic
            opt_msg = re.sub(r'\*(.*?)\*', r'<i>\1</i>', opt_msg)
            
            if "<i>" in opt_msg or "<b>" in opt_msg:
                # Don't escape content that already has HTML tags
                result.append(opt_msg)
            else:
                # Escape regular content
                result.append(escape_html(opt_msg))
    
    # 4. Add mood description in italic at the bottom
    if mood_display:
        result.append(f"<i>{escape_html(mood_display)}</i>")
    
    # Join all parts with line breaks
    formatted_response = "\n\n".join(result)
    
    # Final safety check to ensure we don't have double HTML tags
    return formatted_response

def format_error_response(error_message: str, username: str = "user") -> str:
    """Format an error response with appropriate tone.
    
    Args:
        error_message: Error message to format
        username: User's name for personalization
        
    Returns:
        Formatted HTML error response
    """
    # Replace username placeholder with bold formatting
    if "{username}" in error_message:
        error_message = error_message.replace("{username}", f"<b>{escape_html(username)}</b>")
        
    # Initialize persona manager to get persona-appropriate error expressions
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona()
    
    # Get roleplay from persona if possible
    roleplay = "terlihat bingung dan khawatir"  # Default fallback
    
    # Try to get an apologetic expression from persona
    apologetic_mood = persona.get("emotions", {}).get("apologetic_sincere", {})
    expressions = apologetic_mood.get("expressions", [])
    if expressions:
        roleplay = random.choice(expressions)
        if "{username}" in roleplay:
            roleplay = roleplay.replace("{username}", username)
    
    # Format according to the specified pattern
    result = [
        f"<i>{escape_html(roleplay)}</i>",
        f"{escape_html(error_message)} 😳"
    ]
    
    return "\n\n".join(result)
