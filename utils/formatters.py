import re
import logging

logger = logging.getLogger(__name__)

def format_markdown_response(text: str, username: str = None, telegram_username: str = None) -> str:
    """Format response for MarkdownV2 with better escape and support Telegram mention."""
    try:
        if not isinstance(text, str):
            text = str(text)
        
        # If ada telegram_username (misal @afdaan), gunakan mention Telegram
        safe_mention = None
        if telegram_username and telegram_username.startswith('@'):
            # Telegram mention for MarkdownV2: [username](tg://user?id=USER_ID) is not supported for @username, so just use @username
            safe_mention = telegram_username

        # Handle username first if provided
        if username:
            # Escape dashes in username
            safe_username = username.replace('-', '\\-')
            
            # Fix for words that match username patterns but aren't actual placeholders
            # Periksa dulu kata-kata yang bukan placeholder username
            non_placeholder_patterns = [
                'search', 'carikan', 'find', 'cari', 'tolong', 'please',
                'help', 'bantu', 'tanya', 'ask'
            ]
            
            # Untuk kata-kata pada non_placeholder_patterns, jangan diganti menjadi [username]
            for word in non_placeholder_patterns:
                # Protect these words from username replacement
                text = text.replace(f"[{word}]", f"__PROTECTED__{word}__PROTECTED__")
            
            # Expanded username patterns to catch more variations
            username_patterns = [
                r'\[user\]', r'\[nama\]', r'\[username\]',
                r'\[User\]', r'\[Nama\]', r'\[Username\]',
                r'\[USER\]', r'\[NAMA\]', r'\[USERNAME\]'
            ]
            
            # Ganti placeholder username dengan username yang benar
            for pattern in username_patterns:
                text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)
                
            # Ganti pattern dengan spasi seperti [user] kun, [nama] chan, dll.
            text = re.sub(r'\[\s*(?:user|nama|username)\s*\][\s\-]*(?:kun|chan)?', safe_username, text, flags=re.IGNORECASE)
            
            # Explicit replacements untuk pattern umum
            text = text.replace("[user]-kun", safe_username)
            text = text.replace("[nama]-kun", safe_username)
            text = text.replace("[username]-kun", safe_username)
            text = text.replace("[user]-chan", safe_username)
            text = text.replace("[nama]-chan", safe_username)
            text = text.replace("[username]-chan", safe_username)
            
            # Kembalikan kata-kata yang dilindungi
            for word in non_placeholder_patterns:
                text = text.replace(f"__PROTECTED__{word}__PROTECTED__", f"[{word}]")
            
            # If we have a mention, use it for direct mentions
            if safe_mention:
                text = re.sub(r'(\{usertele\}|\[mention\])', safe_mention, text, flags=re.IGNORECASE)

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