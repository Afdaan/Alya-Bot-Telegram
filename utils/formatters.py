"""
Text Formatting Utilities for Alya Bot.

This module provides utilities for formatting text responses with proper
username handling, MarkdownV2 escaping, and message splitting for Telegram.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

# Import core persona functionality
from core.personas import get_persona_context

logger = logging.getLogger(__name__)

# =====================
# Markdown Formatting
# =====================

def format_markdown_response(text: str, username: Optional[str] = None,
                           telegram_username: Optional[str] = None,
                           mentioned_username: Optional[str] = None,
                           mentioned_text: Optional[str] = None) -> str:
    """
    Format bot response with proper Markdown V2 escaping and variable substitution.
    
    Args:
        text: Raw response text from the AI
        username: User's first name for {username} substitution
        telegram_username: User's Telegram username for {telegram_username} substitution
        mentioned_username: Mentioned username for {mentioned_username} substitution
        mentioned_text: Full mention text for {mentioned_text} substitution
        
    Returns:
        Formatted text with Markdown V2 escaping and replaced variables
    """
    if not text:
        return ""
    
    # Step 1: Replace variables before any formatting
    if username:
        text = text.replace('{username}', username)
    if telegram_username:
        text = text.replace('{telegram_username}', telegram_username)
    if mentioned_username:
        text = text.replace('{mentioned_username}', mentioned_username)
    if mentioned_text:
        text = text.replace('{mentioned_text}', mentioned_text)
    
    # Step 2: Split text into regular parts and roleplay actions
    parts = []
    last_end = 0
    
    # Extract roleplay actions (text between asterisks)
    for match in re.finditer(r'\*(.*?)\*', text):
        # Add text before the match
        if match.start() > last_end:
            parts.append(('text', text[last_end:match.start()]))
        
        # Add the roleplay action
        parts.append(('roleplay', match.group(1)))
        last_end = match.end()
    
    # Add remaining text
    if last_end < len(text):
        parts.append(('text', text[last_end:]))
    
    # Step 3: Process each part with appropriate formatting
    result = []
    
    for part_type, content in parts:
        if part_type == 'text':
            # Regular text - escape markdown
            escaped = escape_markdown_v2(content)
            result.append(escaped)
        else:
            # Roleplay action - format with brackets and italics
            formatted_action = format_roleplay_action(content)
            result.append(formatted_action)
    
    return ''.join(result)

def format_roleplay_action(text: str) -> str:
    """
    Format text as roleplay action with Telegram MarkdownV2 safety.
    
    Args:
        text: Action text like "melirik ke arah jendela"
    
    Returns:
        Safe MarkdownV2 formatted italic text with brackets
    """
    if not text:
        return ""
    
    # Escape all MarkdownV2 special characters
    escaped_text = escape_markdown_v2(text)
    
    # Format as distinct block with italic formatting
    return f"\n\n_\\[ {escaped_text} \\]_\n\n"

def escape_markdown_v2(text: str) -> str:
    """
    Escape MarkdownV2 special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Text with escaped special characters
    """
    if not text:
        return ""
    
    # Characters that need escaping in MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', 
                    '-', '=', '|', '{', '}', '.', '!']
    
    # Escape each special character
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text

# =====================
# Message Splitting
# =====================

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
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
        # Check if adding this paragraph would exceed the max length
        if len(current_part) + len(paragraph) + 4 > max_length:
            if current_part:
                # Add the current part to our results
                parts.append(current_part.strip())
                current_part = paragraph
            else:
                # The paragraph itself is too long, split it by lines
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
            # Add the paragraph with a separator
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

def format_response_with_persona(
    message_text: str,
    persona_type: str = "waifu",
    username: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format a response using a specific persona.
    
    Args:
        message_text: Raw message text
        persona_type: Type of persona to use
        username: Username for substitution
        additional_context: Additional context for formatting
        
    Returns:
        Formatted response
    """
    if not message_text:
        return ""
        
    # Get persona context
    persona_context = get_persona_context(persona_type)
    
    # Apply persona traits to the message
    try:
        # Apply personality traits to message
        if '{persona}' in message_text and persona_context:
            message_text = message_text.replace('{persona}', persona_context)
            
        # Handle special formatting for different personas
        if persona_type == "tsundere":
            # Add tsundere hesitation markers
            message_text = message_text.replace("...", "... b-baka!")
            
        elif persona_type == "toxic":
            # Add intensity to toxic mode
            message_text = message_text.replace("!", "!!!")
            
        # Add character closing based on persona
        if additional_context and additional_context.get("add_closing", True):
            closings = {
                "waifu": "\n\n*dengan senyum manis* ✨",
                "tsundere": "\n\n*melipat tangan* Hmph!",
                "toxic": "\n\n*memutar mata* 🙄",
                "smart": "\n\n*merapikan kacamata* 📊"
            }
            
            if persona_type in closings and not message_text.endswith(closings[persona_type]):
                message_text += closings[persona_type]
    except Exception as e:
        logger.error(f"Error applying persona to message: {e}")
    
    # Format with markdown and username
    return format_markdown_response(message_text, username=username)

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
        Appropriate persona type (waifu, tsundere, toxic, smart)
    """
    text_lower = text.lower()
    
    # Check for toxic indicators
    toxic_words = ["najis", "goblok", "bego", "tolol", "anjing", "bodoh"]
    if any(word in text_lower for word in toxic_words):
        return "toxic"
        
    # Check for smart/informative indicators
    smart_words = ["analisis", "menurut data", "berdasarkan", "statistik", "secara teknis"]
    if any(word in text_lower for word in smart_words):
        return "smart"
        
    # Check for embarrassed indicators
    embarrassed_words = ["malu", "maaf", "gomennasai", "sumimasen", "gomen"]
    if any(word in text_lower for word in embarrassed_words):
        return "embarrassed"
        
    # Check for happiness indicators
    happy_words = ["senang", "suka", "bahagia", "yeay", "yay"]
    if any(word in text_lower for word in happy_words):
        return "happy"
        
    # Check for tsundere indicators
    tsundere_words = ["bukan berarti", "hmph", "b-baka", "bukannya", "bukan karena"]
    if any(word in text_lower for word in tsundere_words):
        return "tsundere"
    
    # Default to waifu
    return "waifu"

def format_command_help(commands: Dict[str, str], username: Optional[str] = None) -> str:
    """
    Format command help information.
    
    Args:
        commands: Dictionary of command names and descriptions
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
    
    return escape_markdown_v2(help_text)