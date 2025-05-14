"""
Text Formatting Utilities for Alya Telegram Bot.

This module provides utilities for formatting text responses with proper
Markdown escaping, username handling, and message splitting.
"""

import re
import logging

logger = logging.getLogger(__name__)

def sanitize_markdown(text: str) -> str:
    """
    Sanitize text for MarkdownV2 formatting by removing problematic patterns.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text safe for MarkdownV2 formatting
    """
    if not text:
        return ""
        
    # Remove code blocks completely as they're often problematic
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    
    # Fix unmatched formatting characters
    for char in ['*', '_', '~', '`']:
        count = text.count(char) - text.count(f'\\{char}')
        if count % 2 != 0:
            # Find last unescaped occurrence and remove it
            pos = len(text) - 1
            while pos >= 0:
                if text[pos] == char and (pos == 0 or text[pos-1] != '\\'):
                    text = text[:pos] + text[pos+1:]
                    break
                pos -= 1
    
    # Replace problematic sequences
    text = text.replace('***', '*')
    text = text.replace('___', '_')
    
    return text

def escape_markdown_v2(text):
    """
    Escape all special characters for MarkdownV2 format.
    
    Args:
        text: Text to escape
        
    Returns:
        Properly escaped text for MarkdownV2
    """
    if not isinstance(text, str):
        text = str(text)
        
    # All characters that need escaping for MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Escape all special characters
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text

def format_markdown_response(text: str, username: str = None, 
                           telegram_username: str = None, 
                           mentioned_username: str = None,
                           mentioned_text: str = None) -> str:
    """
    Format response for MarkdownV2 with better escape and Telegram mention support.
    
    Args:
        text: The text to format
        username: User's first name
        telegram_username: Full @username mention
        mentioned_username: Username without @ symbol
        mentioned_text: Original mention text with @
        
    Returns:
        Markdown-formatted text with proper escaping
    """
    try:
        if not isinstance(text, str):
            text = str(text)
        
        # First sanitize to remove problematic patterns
        text = sanitize_markdown(text)
        
        # First, handle the mentioned user properly (keeping it as is)
        if mentioned_text and mentioned_text.startswith('@'):
            # Preserve mentions but escape special characters
            safe_mention = mentioned_text
            for char in ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '{', '}', '.', '!']:
                safe_mention = safe_mention.replace(char, f'\\{char}')
            
            # Replace all raw occurrences of the mention
            text = text.replace(mentioned_text, safe_mention)
        
        # Now replace username placeholders with the actual user's name
        if username:
            # Escape username for markdown safety
            safe_username = username.replace('-', '\\-').replace('.', '\\.')
            
            # Replace all username placeholders with the actual name
            # Start with bracket patterns
            bracket_patterns = [
                r'\[username\]', r'\[user\]', r'\[nama\]',
                r'\[username\]-kun', r'\[user\]-kun', r'\[nama\]-kun', 
                r'\[([A-Za-z0-9_-]+)\]-kun',  # Catch any name in brackets with -kun
                r'\[username\]-chan', r'\[user\]-chan', r'\[nama\]-chan',
                r'\[([A-Za-z0-9_-]+)\]-chan'  # Catch any name in brackets with -chan
            ]
            
            # Replace all bracket patterns with user's name
            for pattern in bracket_patterns:
                text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)
            
            # Handle suffix patterns without brackets for backward compatibility
            suffix_patterns = [
                r'username-kun', r'user-kun', r'nama-kun',
                r'username-chan', r'user-chan', r'nama-chan',
            ]
            
            for pattern in suffix_patterns:
                text = re.sub(pattern, f"{safe_username}", text, flags=re.IGNORECASE)
            
            # Special case: If there's a mentioned username in brackets (likely from AI confusion)
            # This handles [Mentioned_Username]-kun patterns replacing them with actual user's name
            # But only if it's clearly a placeholder, not a genuine reference to that user
            if mentioned_username:
                placeholder_patterns = [
                    f"\\[{re.escape(mentioned_username)}\\]-kun",
                    f"\\[{re.escape(mentioned_username)}\\]-chan"
                ]
                for pattern in placeholder_patterns:
                    text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)

        # Escape special characters with explicit order
        escapes = [
            ('\\', '\\\\'),  # Must be first
            ('_', '\\_'),
            ('*', '\\*'),
            ('|', '\\|'),  # Added pipe character escape
            ('<', '\\<'),  # Added less than
            ('>', '\\>'),  # Added greater than
            ('=', '\\='),  # Added equals
            ('$', '\\$'),  # Added dollar sign
            ('+', '\\+'),
            ('[', '\\['),
            (']', '\\]'),
            ('(', '\\('),
            (')', '\\)'),
            ('~', '\\~'),
            ('#', '\\#'),
            ('-', '\\-'),
            ('{', '\\{'),
            ('}', '\\}'),
            ('!', '\\!'),
            ('.', '\\.')
        ]
        
        # Apply escapes except for already escaped characters and mentions
        for char, escape in escapes:    
            # Skip if it's already escaped
            if char != '\\':  # Skip the backslash itself since it's already handled
                # Replace the character but don't replace if it's preceded by a backslash
                text = re.sub(f'(?<!\\\\){re.escape(char)}', escape, text)
        
        # Re-preserve mentions
        if mentioned_text and mentioned_text.startswith('@'):
            # Re-escape the mention to ensure it's properly formatted
            safe_mention = mentioned_text
            for char in ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '{', '}', '.', '!']:
                safe_mention = safe_mention.replace(char, f'\\{char}')
                
            # Make sure mentions stay as they are (don't get double escaped)
            text = text.replace(f"\\{safe_mention}", safe_mention)
            
        # Fix common patterns that should remain unescaped
        fixes = [
            (r'\\\*(.+?)\\\*', r'*\1*'),           # Bold
            (r'\\_(.+?)\\_', r'_\1_'),             # Italic
            (r'\\`(.+?)\\`', r'`\1`'),             # Code
            (r'([😀-🙏💕✨🌸])', r'\1'),            # Emojis
            (r'\s\\~\s', r' ~ ')                   # Decorative tildes
        ]

        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)
            
        # Final cleanup for any remaining bracket patterns that might have been missed
        if username:
            # More aggressive cleanup for [name]-kun/chan patterns
            text = re.sub(r'\\\[([A-Za-z0-9_-]+)\\\]-kun', f"{safe_username}", text)
            text = re.sub(r'\\\[([A-Za-z0-9_-]+)\\\]-chan', f"{safe_username}", text)

        return text
    except Exception as e:
        logger.error(f"Error formatting markdown: {e}")
        # Return a safe version of text with all special characters escaped
        return escape_markdown_v2(f"Error: {str(e)}")

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
    # If the message is short enough, return it as is
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