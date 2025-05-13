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
        
        # Handle username mentions - this needs special care
        if telegram_username and telegram_username.startswith('@'):
            # For debugging
            logger.info(f"Processing mention: {telegram_username}, mentioned_username: {mentioned_username}")
            
            # Replace exact username patterns first if available
            if mentioned_username:
                # Pattern like [Hoshizoran] or [Hoshizoran]-kun
                exact_username_pattern = re.escape(f"[{mentioned_username}]")
                text = re.sub(f"{exact_username_pattern}(?:-(?:kun|chan))?", telegram_username, text, flags=re.IGNORECASE)
            
            # Now replace general username placeholders with the mention
            generic_patterns = [
                r'\[username\](?:-(?:kun|chan))?',
                r'\[user\](?:-(?:kun|chan))?',
                r'\[nama\](?:-(?:kun|chan))?',
            ]
            
            for pattern in generic_patterns:
                text = re.sub(pattern, telegram_username, text, flags=re.IGNORECASE)
                
        # Then handle regular username replacement (if no mention or for remaining placeholders)
        elif username:
            safe_username = username.replace('-', '\\-')
            
            # Replace username placeholders with actual username
            username_patterns = [
                r'\[username\](?:-(?:kun|chan))?',
                r'\[user\](?:-(?:kun|chan))?',
                r'\[nama\](?:-(?:kun|chan))?',
            ]
            
            for pattern in username_patterns:
                text = re.sub(pattern, safe_username, text, flags=re.IGNORECASE)
        
        # Restore protected keywords
        for word in reserved_keywords:
            text = text.replace(f"__PROTECTED__{word}__PROTECTED__", f"[{word}]")

        # Special handling for mentions before escaping
        mentions_placeholder = {}
        if telegram_username:
            # Use a unique placeholder for each mention to preserve it
            placeholder = f"__MENTION_{hash(telegram_username)}__"
            mentions_placeholder[placeholder] = telegram_username
            text = text.replace(telegram_username, placeholder)

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
            
        # Restore mentions after escaping
        for placeholder, mention in mentions_placeholder.items():
            text = text.replace(placeholder, mention)

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

        # Final check for any remaining incorrect patterns
        text = text.replace('MENTION-kun', telegram_username or username) if telegram_username or username else text
        text = text.replace('_MENTION-kun', telegram_username or username) if telegram_username or username else text
        text = text.replace('MENTION_-kun', telegram_username or username) if telegram_username or username else text

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