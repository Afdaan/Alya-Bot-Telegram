"""
Response Templates for Alya Telegram Bot.

This module provides a simple mechanism for accessing localized response templates,
primarily for basic commands and system messages.
"""

import logging

logger = logging.getLogger(__name__)

# =========================
# Response Templates
# =========================

RESPONSES = {
    "start": {
        "id": "Halo\\! Alya\\-chan di sini untuk membantu kamu\\~ 🌸",
        "en": "Hello\\! Alya\\-chan is here to help you\\~ 🌸"
    },
    "help": {
        "id": "Ini adalah daftar perintah yang bisa kamu gunakan\\:",
        "en": "Here is the list of commands you can use\\:"
    },
    "language_changed": {
        "id": "Bahasa telah diubah ke *{language}*\\.",
        "en": "Language has been changed to *{language}*\\."
    }
}

# =========================
# Response Functions
# =========================

def get_response(key: str, language: str = "id") -> str:
    """
    Get a response template in the specified language with proper escaping.
    
    Args:
        key: Response template key
        language: Language code ('id' or 'en')
        
    Returns:
        Properly escaped response string for MarkdownV2 formatting
    """
    # Get the response template
    response_dict = RESPONSES.get(key, {})
    response = response_dict.get(language, response_dict.get("id", ""))
    
    # If no response found, return empty string
    if not response:
        logger.warning(f"No response template found for key: {key}, language: {language}")
        return ""
        
    # Ensure response is properly escaped for MarkdownV2
    return ensure_markdown_escaped(response)

def ensure_markdown_escaped(text: str) -> str:
    """
    Ensure text is properly escaped for Telegram's MarkdownV2 format.
    
    Args:
        text: Text to escape
        
    Returns:
        Properly escaped text
    """
    # These characters need to be escaped in MarkdownV2
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', 
        '+', '-', '=', '|', '{', '}', '.', '!'
    ]
    
    # Only escape characters that aren't already escaped
    for char in special_chars:
        if char in text and not f"\\{char}" in text:
            text = text.replace(char, f"\\{char}")
    
    return text
