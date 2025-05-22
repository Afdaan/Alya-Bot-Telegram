"""
Response Templates for Alya Telegram Bot.

This module provides a simple mechanism for accessing localized response templates,
primarily for basic commands and system messages.
"""

import logging
import os
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = Path(__file__).parent.parent
# Updated from RESPONSES_DIR to LOCALE_DIR
LOCALE_DIR = BASE_DIR / "config" / "locales"
DEFAULT_LANGUAGE = "id"

# =========================
# Response Templates
# =========================

# Hardcoded responses for critical templates that must always be available
DEFAULT_RESPONSES = {
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
    },
    "error": {
        "id": "Maaf, terjadi kesalahan\\: *{error}*",
        "en": "Sorry, an error occurred\\: *{error}*"
    },
    "rate_limit": {
        "id": "Pelan\\-pelan ya\\~ Tunggu {seconds} detik sebelum mencoba lagi\\.",
        "en": "Slow down\\~ Wait {seconds} seconds before trying again\\."
    }
}

# Cached responses loaded from YAML files
_RESPONSE_CACHE: Dict[str, Dict[str, Dict[str, str]]] = {}

def _load_responses(language: str = DEFAULT_LANGUAGE, reload: bool = False) -> Dict[str, str]:
    """
    Load responses for a specific language from YAML file.
    
    Args:
        language: Language code (e.g., 'id', 'en')
        reload: Force reload from disk
        
    Returns:
        Dictionary of response key to template
    """
    # Return from cache if available and not forcing reload
    if language in _RESPONSE_CACHE and not reload:
        return _RESPONSE_CACHE[language]
    
    # Default to hardcoded responses
    language_responses = {key: responses.get(language, responses.get(DEFAULT_LANGUAGE))
                         for key, responses in DEFAULT_RESPONSES.items()}
    
    # Try to load from file with new filename format using LANGUAGE_FILE_MAPPING
    from config.settings import LANGUAGE_FILE_MAPPING
    
    # Get filename from mapping or fallback to language code
    filename = LANGUAGE_FILE_MAPPING.get(language, language)
    response_path = LOCALE_DIR / f"{filename}.yaml"
    
    try:
        if not response_path.exists():
            logger.warning(f"Response file not found: {response_path}")
            return language_responses
            
        with open(response_path, 'r', encoding='utf-8') as f:
            file_responses = yaml.safe_load(f)
            
        # Validate and merge responses
        if isinstance(file_responses, dict):
            language_responses.update(file_responses)
        else:
            logger.error(f"Invalid response format in {response_path}")
            
    except Exception as e:
        logger.error(f"Error loading responses from {response_path}: {e}")
    
    # Cache for future use
    _RESPONSE_CACHE[language] = language_responses
    
    return language_responses

# =========================
# Response Functions
# =========================

def get_response(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Get a response template in the specified language with proper escaping.
    
    Args:
        key: Response template key
        language: Language code ('id' or 'en')
        
    Returns:
        Properly escaped response string for MarkdownV2 formatting
    """
    # Get responses for the language
    responses = _load_responses(language)
    
    # Get the response or fallback to default language
    response = responses.get(key)
    
    # If not found, try default language
    if not response and language != DEFAULT_LANGUAGE:
        responses = _load_responses(DEFAULT_LANGUAGE)
        response = responses.get(key)
    
    # If still not found, return empty string
    if not response:
        logger.warning(f"No response template found for key: {key}")
        return ""
    
    # Ensure response is properly escaped for MarkdownV2
    return ensure_markdown_escaped(response)

def format_response(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Get and format a response with variable substitution.
    
    Args:
        key: Response template key
        language: Language code ('id' or 'en')
        **kwargs: Variables to substitute in the response
        
    Returns:
        Formatted response string
    """
    # Get the template
    template = get_response(key, language)
    
    # Substitute variables
    for var_name, var_value in kwargs.items():
        if isinstance(var_value, str):
            placeholder = "{" + var_name + "}"
            template = template.replace(placeholder, str(var_value))
    
    return template

def ensure_markdown_escaped(text: str) -> str:
    """
    Ensure text is properly escaped for Telegram's MarkdownV2 format.
    
    Args:
        text: Text to escape
        
    Returns:
        Properly escaped text (assume text is already correctly escaped)
    """
    # Just return text as is - we expect all hard-coded templates to be already escaped
    # and formatting functions in formatters.py to handle non-template text
    return text

def reload_responses() -> None:
    """Reload all response templates from disk."""
    _RESPONSE_CACHE.clear()
    # Load default language responses
    _load_responses(DEFAULT_LANGUAGE, reload=True)
    
    # Also preload English as a common fallback
    if DEFAULT_LANGUAGE != "en":
        _load_responses("en", reload=True)

def get_available_languages() -> List[str]:
    """
    Get list of available language codes.
    
    Returns:
        List of language codes with available response files
    """
    languages = [DEFAULT_LANGUAGE, "en"]  # Always include default and English
    
    try:
        for file_path in LOCALE_DIR.glob("*.yaml"):
            lang_code = file_path.stem
            if lang_code not in languages:
                languages.append(lang_code)
    except Exception as e:
        logger.error(f"Error scanning response directory: {e}")
        
    return languages

# Initialize response cache
reload_responses()
