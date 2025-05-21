"""
Text Formatting Utilities for Alya Bot.

This module provides utilities for formatting text responses with proper
username handling, MarkdownV2 escaping, and message splitting for Telegram.
"""

import logging
import re
from typing import List, Dict, Any, Optional

# Import core persona functionality
from core.personas import get_persona_context

logger = logging.getLogger(__name__)

# =====================
# Markdown Formatting
# =====================

def format_roleplay_message(message: str, roleplay_action: Optional[str] = None, 
                          mood_action: Optional[str] = None,
                          optional_message: Optional[str] = None
    ) -> str:
    """Format message with proper roleplay and mood styling."""
    parts = []

    if roleplay_action:
        escaped_action = escape_markdown_v2(roleplay_action)
        parts.append(f"_\\[{escaped_action}\\]_")

    if message:
        # Escape all except * and _ for markdown
        preserved_msg = escape_markdown_v2(message, preserve="*_")
        parts.append(preserved_msg)

    if optional_message:
        # Escape all except * and _ for markdown
        preserved_optional = escape_markdown_v2(optional_message, preserve="*_")
        parts.append(preserved_optional)

    if mood_action:
        escaped_mood = escape_markdown_v2(mood_action)
        parts.append(f"_\\{{{escaped_mood}\\}}_")

    return "\n\n".join(part for part in parts if part.strip())

def format_alya_response(text: str, username: Optional[str] = None) -> str:
    """
    Format Alya's response with consistent styling.
    
    Args:
        text: Raw response text
        username: Optional username for substitution
        
    Returns:
        Formatted response text
    """
    # Extract roleplay and mood parts
    roleplay_match = re.search(r'\[([^\]]+)\]', text)
    mood_match = re.search(r'\{([^\}]+)\}', text)
    
    # Split remaining text into main and optional messages
    remaining_text = text
    if roleplay_match:
        remaining_text = remaining_text.replace(roleplay_match.group(0), '')
    if mood_match:
        remaining_text = remaining_text.replace(mood_match.group(0), '')
        
    # Split remaining text into main and optional messages
    parts = remaining_text.split('\n\n')
    main_message = parts[0].strip() if parts else ""
    optional_message = parts[1].strip() if len(parts) > 1 else None
    
    # Format with proper structure
    return format_roleplay_message(
        message=main_message,
        roleplay_action=roleplay_match.group(1) if roleplay_match else None,
        mood_action=mood_match.group(1) if mood_match else None,
        optional_message=optional_message
    )

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
    return format_alya_response(text)

def format_roleplay_action(text: str) -> str:
    """
    Format text as roleplay action with proper spacing.
    
    Args:
        text: Action text like "melirik ke arah jendela"
    
    Returns:
        Safe MarkdownV2 formatted italic text with brackets and spacing
    """
    if not text:
        return ""
    
    # Clean up the text first
    text = text.strip()
    
    # Remove any existing brackets/formatting
    text = re.sub(r'[\[\]\\*_\n]', '', text)
    
    # Remove multiple spaces
    text = ' '.join(text.split())
    
    # Escape special characters for MarkdownV2
    text = escape_markdown_v2(text)
    
    # Format with consistent style and clear spacing
    return f"\n\n_\\[ {text} \\]_\n\n"  # Double newlines for clear separation

def escape_markdown_v2(text: str, preserve: str = "") -> str:
    """
    Escape MarkdownV2 special characters for Telegram, except those in 'preserve'.

    Args:
        text: The text to escape.
        preserve: String of characters to NOT escape (e.g. '*_').

    Returns:
        Escaped text safe for MarkdownV2.
    """
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+',
                     '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        if char not in preserve:
            text = re.sub(rf'(?<!\\){re.escape(char)}', f'\\{char}', text)
    return text

def format_dev_message(text: str) -> str:
    """
    Format text for developer commands with proper MarkdownV2 escaping.
    
    Uses existing escape_markdown_v2 but with special handling for
    common patterns in developer messages.
    
    Args:
        text: Raw text to format
        
    Returns:
        Text formatted for MarkdownV2
    """
    # Replace common patterns with pre-escaped versions
    text = text.replace("...", "\\.\\.\\.")
    
    # Use general escaping for the rest
    return escape_markdown_v2(text)

# =====================
# Message Splitting
# =====================

def split_long_message(text: str, max_length: int = 4096) -> List[str]:
    """
    Split a long message into multiple parts that fit within Telegram limits.
    
    Args:
        text: The message text to split
        max_length: Maximum length per message part
        
    Returns:
        List of message parts
    """
    # If the message is short enough, return it as is
    if not text or len(text) <= max_length:
        return [text] if text else [""]
    
    # Enhanced splitting for content like lyrics
    parts = []
    
    # First try to split by paragraphs (preferred)
    paragraphs = text.split('\n\n')
    current_part = ""
    
    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 4 > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = paragraph
            else:
                lines = paragraph.split('\n')
                temp_part = ""
                for line in lines:
                    if len(temp_part) + len(line) + 1 > max_length:
                        parts.append(temp_part.strip())
                        temp_part = line
                    else:
                        temp_part += "\n" + line if temp_part else line
                if temp_part:
                    current_part = temp_part
        else:
            current_part += "\n\n" + paragraph if current_part else paragraph
    # Add the last part if any
    if current_part:
        parts.append(current_part.strip())
    
    # If we still have parts that are too long, split them
    result = []
    for part in parts:
        if len(part) <= max_length:
            result.append(part)
        else:
            # Last resort: split by character chunks
            for i in range(0, len(part), max_length):
                result.append(part[i:i + max_length])
    
    return result

# =====================
# Persona-based Formatting
# =====================

def format_response_with_persona(message: str, persona: str) -> str:
    """
    Format response with persona traits and inject emoji.
    
    Args:
        message: Raw response message.
        persona: Persona type (e.g., tsundere, waifu).
    
    Returns:
        Formatted response with persona traits.
    """
    persona_context = get_persona_context(persona)
    if persona == "tsundere":
        return f"{persona_context}\n\n{message} Hmph! 😤"
    elif persona == "waifu":
        return f"{persona_context}\n\n{message} 💖"
    elif persona == "toxic":
        return f"{persona_context}\n\n{message} 🔥"
    else:
        return f"{persona_context}\n\n{message} 💫"

def format_simple_message(template_key: str, username: Optional[str] = None, **kwargs) -> str:
    """
    Format a simple message from a template key.
    
    Args:
        template_key: Template key in the responses YAML
        username: Username for substitution
        **kwargs: Additional substitution variables
        
    Returns:
        Formatted message
    """
    from utils.language_handler import get_response  # Import here to avoid circular imports
    
    try:
        # Get the template
        template = get_response(template_key)
        
        # Substitute variables
        for key, value in kwargs.items():
            if isinstance(value, str):
                placeholder = f"{{{key}}}"
                template = template.replace(placeholder, value)
        
        # Format with markdown
        return format_markdown_response(template, username=username)
    except Exception as e:
        logger.error(f"Error formatting simple message: {e}")
        return f"Error: {str(e)}"

def format_error_message(error_text: str, username: Optional[str] = None) -> str:
    """
    Format an error message with consistent styling.
    
    Args:
        error_text: Error text
        username: Username for personalization
        
    Returns:
        Formatted error message
    """
    error_template = (
        "{username}-kun~ Gomenasai! Alya mengalami error:\n\n"
        "```\n{error}\n```\n\n"
        "*menatap dengan mata berkaca-kaca* Maaf ya... 🥺"
    )
    
    # Truncate very long errors
    if len(error_text) > 300:
        error_text = error_text[:300] + "..."
    
    # Replace error text with escaped version
    message = error_template.replace("{error}", error_text)
    
    # Format with markdown and username
    return format_markdown_response(message, username=username)

# =====================
# Specialized Formatters
# =====================

def format_memory_stats(stats: Dict[str, Any], username: str) -> str:
    """
    Format memory statistics for user display.
    
    Args:
        stats: Memory statistics
        username: User's name
        
    Returns:
        Formatted stats message
    """
    template = (
        "*Memory Stats for {username}*\n\n"
        "🗣️ User messages: {user_messages}\n"
        "🤖 Bot messages: {bot_messages}\n"
        "📚 Total messages: {total_messages}\n"
        "🧩 Token usage: {token_usage}\n"
        "🕰️ Memory age: {memory_age}\n"
        "📝 Personal facts: {personal_facts}\n"
        "📊 Memory usage: {memory_usage_percent}%\n\n"
        "*mencatat data ke buku catatan* Memory contextku untuk {username}-kun!"
    )
    
    # Format template with stats
    message = template.format(
        username=username,
        user_messages=stats.get('user_messages', 0),
        bot_messages=stats.get('bot_messages', 0),
        total_messages=stats.get('total_messages', 0),
        token_usage=stats.get('token_usage', 0),
        memory_age=stats.get('memory_age', 'N/A'),
        personal_facts=stats.get('personal_facts', 0),
        memory_usage_percent=stats.get('memory_usage_percent', 0)
    )
    
    # Format with markdown
    return format_markdown_response(message, username=username)

def detect_persona_type_from_text(text: str) -> str:
    """
    Detect appropriate persona type from text content.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Appropriate persona type (default, toxic, smart, embarrassed, happy)
    """
    text_lower = text.lower()
    
    # Check for toxic indicators
    if any(word in text_lower for word in ["bad", "angry", "annoyed"]):
        return "toxic"
        
    # Check for smart/informative indicators
    if any(word in text_lower for word in ["analyze", "data", "based", "statistics", "technical"]):
        return "smart"
        
    # Check for embarrassed indicators
    if any(word in text_lower for word in ["sorry", "apologize", "regret"]):
        return "embarrassed"
        
    # Check for happiness indicators
    if any(word in text_lower for word in ["happy", "like", "joy", "yay"]):
        return "happy"
    
    # Default persona
    return "default"

def format_help_text(commands: Dict[str, str], username: Optional[str] = None) -> str:
    """
    Format help text with command descriptions.
    
    Args:
        commands: Dictionary of command descriptions
        username: User's name for personalization
        
    Returns:
        Formatted help text
    """
    # Start with header
    help_text = f"*Alya\\-chan's Command List* 📋\n\n"
    
    # Group commands by category
    categories = {
        "Basic": ["start", "help", "ping", "mode"],
        "Search": ["search", "img", "sauce"],
        "Fun": ["roast", "gif", "sticker"],
        "Utility": ["translate", "ocr", "analyze"],
        "Settings": ["lang", "stats", "privacy"]
    }
    
    # Format each category
    for category, cmd_list in categories.items():
        category_commands = {cmd: desc for cmd, desc in commands.items() if cmd in cmd_list}
        if category_commands:
            help_text += f"*{category} Commands:*\n"
            for cmd, desc in category_commands.items():
                help_text += f"• `/{cmd}` \\- {desc}\n"
            help_text += "\n"
    
    # Add footer
    if username:
        help_text += f"\n*menatap {username} dengan antusias* Ada yang bisa Alya bantu lagi\\~?"
    else:
        help_text += "\n*tersenyum manis* Ada yang bisa Alya bantu\\~?"
    
    # Return with final escaping
    return help_text  # Text is already escaped through the construction process

def fix_html_formatting(text: str) -> str:
    """
    Fix common HTML formatting issues in text outputs.
    
    Args:
        text: Text with potential HTML formatting issues
        
    Returns:
        Text with fixed HTML formatting
    """
    # Fix incomplete tags at end of text (like "</u")
    text = re.sub(r'</?[a-zA-Z0-9]*$', '', text)
    
    # Replace unsupported tags with simpler format
    text = text.replace('<ul>', '')
    text = text.replace('</ul>', '')
    text = text.replace('<li>', '• ')
    text = text.replace('</li>', '\n')
    text = text.replace('<p>', '')
    text = text.replace('</p>', '\n\n')
    
    # Count and balance tags
    supported_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a']
    for tag in supported_tags:
        # Count opening tags
        open_tags = len(re.findall(f'<{tag}[^>]*>', text))
        # Count closing tags
        close_tags = len(re.findall(f'</{tag}>', text))
        # Add closing tags if missing 
        if open_tags > close_tags:
            text += f'</{tag}>' * (open_tags - close_tags)
        # Remove extra closing tags from end
        elif close_tags > open_tags:
            for _ in range(close_tags - open_tags):
                last_idx = text.rfind(f'</{tag}>')
                if last_idx >= 0:
                    text = text[:last_idx] + text[last_idx + len(f'</{tag}>'):]
    
    # Remove all unsupported tags
    all_tags = re.findall(r'</?([a-zA-Z0-9]+)[^>]*>', text)
    for tag in set(all_tags):
        if tag.lower() not in supported_tags:
            text = re.sub(f'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
            text = re.sub(f'</{tag}>', '', text, flags=re.IGNORECASE)
    
    # Fix common HTML issues
    text = text.replace('&nbsp;', ' ')
    text = text.replace('\n\n\n\n', '\n\n')
    text = text.replace('\n\n\n', '\n\n')
    
    # Final check: remove duplicate end tags
    text = re.sub(r'(</?[a-zA-Z0-9]+>)\1+', r'\1', text)
    
    return text

def format_document_analysis(text: str, metadata: Dict[str, str]) -> str:
    """
    Format document analysis with consistent styling.
    
    Args:
        text: Analysis text content
        metadata: Document metadata dictionary
        
    Returns:
        Formatted HTML text
    """
    from utils.language_handler import get_response
    
    header = (
        f"<b>📄 {get_response('doc_analysis.title')}</b>\n\n"
        f"<b>{get_response('doc_analysis.info_header')}</b>\n"
    )
    
    # Add metadata
    for key, value in metadata.items():
        header += f"• {key}: {value}\n"
    
    # Format main content with proper spacing
    no_content_msg = get_response('doc_analysis.no_content')
    body = f"\n{text.strip()}" if text else f"\n<i>{no_content_msg}</i>"
    
    return fix_html_formatting(f"{header}\n{body}")