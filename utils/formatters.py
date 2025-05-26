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
    if "<" not in message:
        if "{username}" in message:
            message = message.format(username=username)
        if target_name and "{target}" in message:
            message = message.format(target=target_name)
    
    # For roasting responses with existing HTML, preserve the HTML formatting
    if "<b>" in message or "<i>" in message:
        # Check if roleplay is already formatted in HTML
        existing_roleplay_match = re.search(r'<i>\((.*?)\)</i>', message)
        if existing_roleplay_match:
            existing_roleplay = existing_roleplay_match.group(0)
            message = re.sub(r'<i>\(.*?\)</i>', '', message, count=1).strip()
            
            # Split into paragraphs
            paragraphs = [p for p in message.split('\n\n') if p.strip()]
            
            # Build final response, preserving HTML
            result = [existing_roleplay]
            result.extend(paragraphs)
            
            # Join with double newlines
            return "\n\n".join(result)
        
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
        else:
            # Fallback when no expressions found for this mood/emotion
            roleplay = "menatap {username}"
    else:
        roleplay = existing_roleplay
    
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
            main_message = f"{main_message} {selected_emoji}"
    
    # Get optional Russian expression from persona
    if FORMAT_RUSSIAN and random.random() < 0.3:  # Only add Russian 30% of the time
        russian_triggers = {}
        
        # Try to find Russian expressions for this mood/emotion
        for persona_mood, mood_data in persona.get("emotions", {}).items():
            if emotion in persona_mood.lower() or mood in persona_mood.lower():
                russian_triggers = mood_data.get("russian_triggers", [])
                break
        
        # If found in persona, add to optional messages
        if russian_triggers:
            russian_expr = random.choice(russian_triggers) if russian_triggers else None
            if russian_expr and len(optional_messages) < 2:
                # Look up romaji from global config if available
                for emotion_key, expressions in RUSSIAN_EXPRESSIONS.items():
                    if russian_expr in expressions.get("expressions", []):
                        idx = expressions["expressions"].index(russian_expr)
                        romaji = expressions["romaji"][idx] if idx < len(expressions["romaji"]) else None
                        if romaji:
                            russian_text = f"{russian_expr} ({romaji})"
                            optional_messages.append(f"({russian_text})")
                            break
                else:
                    # If not found, just use the expression
                    optional_messages.append(f"({russian_expr})")
    
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
    
    # Build the formatted response according to the specified format
    result = []
    
    # 1. Add roleplay in italic if present
    if roleplay:
        # Format roleplay with username
        roleplay_text = roleplay.format(username=username) if "{username}" in roleplay else roleplay
        result.append(f"<i>{escape_html(roleplay_text)}</i>")
    
    # 2. Add main message
    result.append(escape_html(main_message))
    
    # 3. Add optional messages (limited to keep responses shorter)
    for opt_msg in optional_messages:
        if opt_msg.strip():
            result.append(escape_html(opt_msg))
    
    # 4. Add mood description in italic at the bottom
    if mood_display:
        result.append(f"<i>{escape_html(mood_display)}</i>")
    
    # Join all parts with line breaks
    return "\n\n".join(result)

def format_error_response(error_message: str, username: str = "user") -> str:
    """Format an error response with appropriate tone.
    
    Args:
        error_message: Error message to format
        username: User's name for personalization
        
    Returns:
        Formatted HTML error response
    """
    # Replace username placeholder
    if "{username}" in error_message:
        error_message = error_message.format(username=username)
        
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
    
    # Format according to the specified pattern
    result = [
        f"<i>{escape_html(roleplay)}</i>",
        f"{escape_html(error_message)} 😳"
    ]
    
    return "\n\n".join(result)
