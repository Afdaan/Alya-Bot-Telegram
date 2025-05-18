"""
Text Formatting Utilities for Alya Bot.

This module provides utilities for formatting text responses with proper
username handling and message splitting to create natural human-like conversations.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from telegram.helpers import escape_markdown  # Import built-in helper

from core.personas import persona_manager

logger = logging.getLogger(__name__)

def format_markdown_response(text: str, username: Optional[str] = None, telegram_username: Optional[str] = None,
                           mentioned_username: Optional[str] = None, mentioned_text: Optional[str] = None) -> str:
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
    
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', 
                    '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text

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
    
    # Try splitting by paragraphs first
    paragraphs = text.split('\n\n')
    current_part = ""
    
    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 4 > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = paragraph
            else:
                # Handle large paragraphs by splitting them at line breaks
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
    
    # If no parts were created (which shouldn't happen), fall back to rough splitting
    if not parts:
        for i in range(0, len(text), max_length):
            parts.append(text[i:i + max_length])
    
    return parts

def format_response_with_persona(
    response_key: str, 
    persona_type: str = "waifu", 
    username: str = None,
    context_data: Dict[str, Any] = None, 
    **kwargs
) -> str:
    """
    Format a response using the appropriate persona and response template from YAML.
    
    Args:
        response_key: Key to identify response template in YAML
        persona_type: Type of persona to use (waifu, toxic, smart)
        username: User's name
        context_data: Context data including conversation history and personal facts
        **kwargs: Additional variables for template substitution
        
    Returns:
        Fully formatted response with persona traits applied
    """
    # Get personal facts if available
    personal_facts = {}
    if context_data and "personal_facts" in context_data:
        personal_facts = context_data.get("personal_facts", {})
    
    # Add username to template variables
    template_vars = {"username": username}
    
    # Add personal facts to template variables
    if "name" in personal_facts and personal_facts["name"] != username:
        template_vars["actual_name"] = personal_facts["name"]
    
    # Add other kwargs to template variables
    template_vars.update(kwargs)
    
    # Get response from persona manager
    response = persona_manager.get_response_template(response_key, persona_type, **template_vars)
    
    # Format with markdown
    return format_markdown_response(response, username)

def format_memory_stats(stats: Dict[str, Any], username: str) -> str:
    """
    Format memory statistics for user display.
    
    Args:
        stats: Memory statistics
        username: User's name
        
    Returns:
        Formatted stats message
    """
    # Instead of hardcoding the response, use persona template
    return format_response_with_persona(
        "memory_stats", 
        "informative",
        username=username,
        stats=stats
    )

def detect_persona_type_from_text(text: str) -> str:
    """
    Detect appropriate persona type from text content.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Appropriate persona type (waifu, tsundere, toxic, smart)
    """
    # Check for toxic indicators
    toxic_words = ["najis", "goblok", "bego", "tolol", "anjing", "bodoh"]
    if any(word in text.lower() for word in toxic_words):
        return "toxic"
        
    # Check for smart/informative indicators
    smart_words = ["analisis", "menurut data", "berdasarkan", "statistik", "secara teknis"]
    if any(word in text.lower() for word in smart_words):
        return "smart"
        
    # Check for embarrassed indicators
    embarrassed_words = ["malu", "maaf", "gomennasai", "sumimasen", "gomen"]
    if any(word in text.lower() for word in embarrassed_words):
        return "embarrassed"
        
    # Check for happiness indicators
    happy_words = ["senang", "suka", "bahagia", "yeay", "yay"]
    if any(word in text.lower() for word in happy_words):
        return "happy"
        
    # Check for tsundere indicators
    tsundere_words = ["bukan berarti", "hmph", "b-baka", "bukannya", "bukan karena"]
    if any(word in text.lower() for word in tsundere_words):
        return "tsundere"
    
    # Default to waifu
    return "waifu"

def get_character_action(persona_type: str = "waifu") -> str:
    """
    Get a random character action text from the YAML config.
    
    Args:
        persona_type: The persona type to use for the action
        
    Returns:
        A random action with asterisks
    """
    try:
        # Try getting action from persona_manager
        action = persona_manager.get_response_template("action", persona_type)
        
        # If failed to get from YAML, log and use generic fallback
        if not action or len(action) < 3 or "__" in action:
            logger.warning(f"Failed to load action template for {persona_type}, falling back to generic")
            return persona_manager.get_response_template("fallback.action", persona_type)
        
        return action
    except Exception as e:
        logger.error(f"Error getting character action text: {e}")
        # Even this fallback should be in YAML, but keep as ultimate fallback
        return "*melakukan sesuatu*"