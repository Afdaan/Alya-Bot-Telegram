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
        
        # If we have a mention (@username), check if we should replace [username] with it
        if mentioned_username:
            # Replace all occurrences of [username] or [Hoshizoran] with the @mention
            patterns_to_replace = []
            
            # Add the exact username patterns (e.g., [Hoshizoran])
            if mentioned_username:
                patterns_to_replace.append(re.escape(f"[{mentioned_username}]"))
            
            # Add generic patterns
            patterns_to_replace.extend([
                r'\[username\]', r'\[user\]', r'\[nama\]',
                r'\[Username\]', r'\[User\]', r'\[Nama\]',
                r'\[USERNAME\]', r'\[USER\]', r'\[NAMA\]'
            ])
            
            # Replace all patterns with the telegram mention
            for pattern in patterns_to_replace:
                text = re.sub(pattern, telegram_username, text, flags=re.IGNORECASE)
            
            # Also handle the -kun/-chan suffixes specifically for mentioned usernames
            text = re.sub(f"\\[{re.escape(mentioned_username)}\\]-kun", telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(f"\\[{re.escape(mentioned_username)}\\]-chan", telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(r'\[username\]-kun', telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(r'\[username\]-chan', telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(r'\[user\]-kun', telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(r'\[user\]-chan', telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(r'\[nama\]-kun', telegram_username, text, flags=re.IGNORECASE)
            text = re.sub(r'\[nama\]-chan', telegram_username, text, flags=re.IGNORECASE)
        
        # If we still have [username] patterns and a username (fallback)
        if username:
            # Escape dashes in username
            safe_username = username.replace('-', '\\-')
            
            # Generic username patterns that might still be in the text
            username_patterns = [
                r'\[user\]', r'\[nama\]', r'\[username\]', 
                r'\[User\]', r'\[Nama\]', r'\[Username\]',
                r'\[USER\]', r'\[NAMA\]', r'\[USERNAME\]'
            ]
            
            for pattern in username_patterns:
                text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)
            
            # Handle -kun/-chan patterns for non-mentioned usernames
            text = re.sub(r'\[user\]-kun', f"{safe_username}", text, flags=re.IGNORECASE)
            text = re.sub(r'\[user\]-chan', f"{safe_username}", text, flags=re.IGNORECASE)
            text = re.sub(r'\[nama\]-kun', f"{safe_username}", text, flags=re.IGNORECASE)
            text = re.sub(r'\[nama\]-chan', f"{safe_username}", text, flags=re.IGNORECASE)
            text = re.sub(r'\[username\]-kun', f"{safe_username}", text, flags=re.IGNORECASE)
            text = re.sub(r'\[username\]-chan', f"{safe_username}", text, flags=re.IGNORECASE)
        
        # Restore protected keywords
        for word in reserved_keywords:
            text = text.replace(f"__PROTECTED__{word}__PROTECTED__", f"[{word}]")

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

        # Skip escaping @ symbol in telegram mentions
        if telegram_username:
            # Temporarily replace the mention to protect it from escaping
            text = text.replace(telegram_username, "__MENTION__")
            
        # Apply escapes
        for char, escape in escapes:
            text = text.replace(char, escape)
            
        # Restore the mention if it was present
        if telegram_username:
            text = text.replace("__MENTION__", telegram_username)

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