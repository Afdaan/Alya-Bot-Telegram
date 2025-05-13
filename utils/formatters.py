import re
import logging

logger = logging.getLogger(__name__)

def format_markdown_response(text: str, username: str = None, telegram_username: str = None, mentioned_username: str = None) -> str:
    """Format response for MarkdownV2 with better escape and support Telegram mention."""
    try:
        if not isinstance(text, str):
            text = str(text)
        
        # First, handle special keywords that should not be replaced
        reserved_keywords = [
            'search', 'carikan', 'find', 'cari', 'tolong', 'please',
            'help', 'bantu', 'tanya', 'ask'
        ]
        
        # Temporarily protect these words
        for word in reserved_keywords:
            text = text.replace(f"[{word}]", f"__PROTECTED__{word}__PROTECTED__")
        
        # Properly handle Telegram mentions - FIXED VERSION
        if telegram_username and telegram_username.startswith('@'):
            # Basic placeholder substitutions
            patterns = [
                r'\[username\]', r'\[user\]', r'\[nama\]',
                r'\[username\]-kun', r'\[user\]-kun', r'\[nama\]-kun',
                r'\[username\]-chan', r'\[user\]-chan', r'\[nama\]-chan',
            ]
            
            # Replace all standard patterns with the telegram @username
            for pattern in patterns:
                text = re.sub(pattern, telegram_username, text, flags=re.IGNORECASE)
            
            # If we have a specific mentioned username (without @)
            if mentioned_username:
                # Also replace [Specific username] with @username
                specific_pattern = f"\\[{re.escape(mentioned_username)}\\]"
                text = re.sub(specific_pattern, telegram_username, text, flags=re.IGNORECASE)
                
                # And [Specific username]-kun/chan forms
                text = re.sub(f"\\[{re.escape(mentioned_username)}\\]-kun", telegram_username, text, flags=re.IGNORECASE)
                text = re.sub(f"\\[{re.escape(mentioned_username)}\\]-chan", telegram_username, text, flags=re.IGNORECASE)
            
        # Regular username replacement (if no mentions or for remaining ones)
        elif username:
            safe_username = username.replace('-', '\\-')
            
            # Replace all variations of username placeholders
            username_patterns = [
                r'\[username\]', r'\[user\]', r'\[nama\]',
                r'\[username\]-kun', r'\[user\]-kun', r'\[nama\]-kun',
                r'\[username\]-chan', r'\[user\]-chan', r'\[nama\]-chan',
            ]
            
            for pattern in username_patterns:
                text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)
        
        # Restore protected keywords
        for word in reserved_keywords:
            text = text.replace(f"__PROTECTED__{word}__PROTECTED__", f"[{word}]")

        # *** CRITICAL FIX: Protect mentions before escaping ***
        if telegram_username:
            # We need to handle @ mentions specially - temporarily replace with a unique token
            # that won't be affected by escaping
            mention_placeholder = "__REAL_MENTION_TOKEN__"
            text = text.replace(telegram_username, mention_placeholder)
        
        # Escape special characters in correct order
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
        
        # *** CRITICAL FIX: Restore the actual mention after escaping ***
        if telegram_username:
            text = text.replace(mention_placeholder, telegram_username)

        # Fix common patterns for proper markdown
        fixes = [
            (r'\\\*(.+?)\\\*', r'*\1*'),           # Bold
            (r'\\_(.+?)\\_', r'_\1_'),             # Italic
            (r'\\`(.+?)\\`', r'`\1`'),             # Code
            (r'([😀-🙏💕✨🌸])', r'\1'),            # Emojis
            (r'\s\\~\s', r' ~ ')                   # Decorative tildes
        ]

        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)

        # *** FINAL CLEANUP: Fix any broken mention patterns that might remain ***
        if telegram_username:
            # Replace any remaining broken patterns like _MENTION-xxx__-kun
            text = re.sub(r'_MENTION[^_\s]+__-kun', telegram_username, text)
            text = re.sub(r'_MENTION[^_\s]+__-chan', telegram_username, text)
            text = re.sub(r'MENTION[^_\s]+__-kun', telegram_username, text)
            text = re.sub(r'MENTION[^_\s]+__-chan', telegram_username, text)

        return text
    except Exception as e:
        logger.error(f"Error formatting markdown: {e}")
        return f"Error: {str(e)}".replace('-', '\\-').replace('!', '\\!')

def split_long_message(text: str, max_length: int = 4000) -> list:
    """Split a long message into multiple parts that fit within Telegram limits.
    
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