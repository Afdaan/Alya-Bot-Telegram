"""
Text Formatting Utilities for Alya Telegram Bot.

This module provides utilities for formatting text responses with proper
Markdown escaping, username handling, and message splitting.
"""

import re
import logging

logger = logging.getLogger(__name__)

# =========================
# Markdown Formatting
# =========================

def format_markdown_response(text: str, username: str = None, 
                           telegram_username: str = None, 
                           mentioned_username: str = None) -> str:
    """
    Format response for MarkdownV2 with better escape and Telegram mention support.
    
    Args:
        text: The text to format
        username: User's first name
        telegram_username: Full @username mention
        mentioned_username: Username without @ symbol
        
    Returns:
        Markdown-formatted text with proper escaping
    """
    try:
        if not isinstance(text, str):
            text = str(text)
        
        # First protect the mention if it exists
        mention_placeholder = None
        if telegram_username and telegram_username.startswith('@'):
            mention_placeholder = "MENTION_PLACEHOLDER_TOKEN"
            text = text.replace(telegram_username, mention_placeholder)
        
        # Replace username placeholders
        if telegram_username:
            # Replace all standard username patterns with the actual mention
            username_patterns = [
                r'\[username\]', r'\[user\]', r'\[nama\]',
                r'\[username\]-kun', r'\[user\]-kun', r'\[nama\]-kun',
                r'\[username\]-chan', r'\[user\]-chan', r'\[nama\]-chan',
            ]
            
            for pattern in username_patterns:
                text = re.sub(pattern, telegram_username, text, flags=re.IGNORECASE)
            
            # If we have a specific mentioned username, replace that too
            if mentioned_username:
                pattern = f"\\[{re.escape(mentioned_username)}\\]"
                text = re.sub(pattern, telegram_username, text, flags=re.IGNORECASE)
                
                # Also handle [username]-kun/chan patterns
                text = re.sub(f"\\[{re.escape(mentioned_username)}\\]-kun", 
                             telegram_username, text, flags=re.IGNORECASE)
                text = re.sub(f"\\[{re.escape(mentioned_username)}\\]-chan", 
                             telegram_username, text, flags=re.IGNORECASE)
                
        elif username:
            # If no telegram mention but we have a regular username
            safe_username = username.replace('-', '\\-')
            
            # Replace standard username patterns
            username_patterns = [
                r'\[username\]', r'\[user\]', r'\[nama\]',
                r'\[username\]-kun', r'\[user\]-kun', r'\[nama\]-kun',
                r'\[username\]-chan', r'\[user\]-chan', r'\[nama\]-chan',
            ]
            
            for pattern in username_patterns:
                text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)

        # Escape special characters with explicit order
        escapes = [
            ('\\', '\\\\'),  # Must be first
            ('_', '\\_'),
            ('*', '\\*'),
            ('[', '\\['),
            (']', '\\]'),
            ('(', '\\('),
            (')', '\\)'),
            ('~', '\\~'),
            ('>', '\\>'),
            ('#', '\\#'),
            ('+', '\\+'),
            ('-', '\\-'),
            ('=', '\\='),
            ('{', '\\{'),
            ('}', '\\}'),
            ('!', '\\!'),
            ('.', '\\.')
        ]
        
        for char, escape in escapes:
            text = text.replace(char, escape)
        
        # Restore the mention if needed
        if telegram_username and mention_placeholder:
            text = text.replace(mention_placeholder, telegram_username)

        # Fix common patterns
        fixes = [
            (r'\\\*(.+?)\\\*', r'*\1*'),           # Bold
            (r'\\_(.+?)\\_', r'_\1_'),             # Italic
            (r'\\`(.+?)\\`', r'`\1`'),             # Code
            (r'([😀-🙏💕✨🌸])', r'\1'),            # Emojis
            (r'\s\\~\s', r' ~ ')                   # Decorative tildes
        ]

        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)
            
        # Final cleanup for any broken mention patterns
        if telegram_username:
            broken_patterns = [
                r'_MENTION[^_\s]*_', 
                r'MENTION_PLACEHOLDER_TOKEN',
                r'_REAL[^_\s]*_'
            ]
            for pattern in broken_patterns:
                text = re.sub(pattern, telegram_username, text)

        return text
    except Exception as e:
        logger.error(f"Error formatting markdown: {e}")
        return f"Error: {str(e)}".replace('-', '\\-').replace('!', '\\!')

# =========================
# Message Splitting
# =========================

def split_long_message(text: str, max_length: int = 4000) -> list:
    """
    Split a long message into multiple parts that fit within Telegram limits.
    
    Attempts to break on paragraph boundaries when possible for more natural splits.
    
    Args:
        text: The message text to split
        max_length: Maximum length per message part
        
    Returns:
        List of message parts
    """
    if len(text) <= max_length:
        return [text]
        
    parts = []
    
    # Try to split on double newlines (paragraphs) when possible
    paragraphs = text.split('\n\n')
    current_part = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed max_length
        if len(current_part) + len(paragraph) + 2 > max_length:
            # If current_part is not empty, add it to parts
            if current_part:
                parts.append(current_part)
                current_part = paragraph
            else:
                # If the paragraph itself is too long
                if len(paragraph) > max_length:
                    # Split the paragraph at max_length
                    for i in range(0, len(paragraph), max_length):
                        parts.append(paragraph[i:i+max_length])
                else:
                    current_part = paragraph
        else:
            if current_part:
                current_part += "\n\n" + paragraph
            else:
                current_part = paragraph
    
    # Don't forget the last part
    if current_part:
        parts.append(current_part)
        
    return parts