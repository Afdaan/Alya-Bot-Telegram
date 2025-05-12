import re
import logging

logger = logging.getLogger(__name__)

def format_markdown_response(text: str, username: str = None) -> str:
    """Format response for MarkdownV2 with better escape."""
    try:
        # Handle username first if provided
        if username:
            # Escape dashes in username
            safe_username = username.replace('-', '\\-')
            username_patterns = [r'\[user\]', r'\[nama\]', r'\[username\]']
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
        return text.replace('-', '\\-').replace('!', '\\!')