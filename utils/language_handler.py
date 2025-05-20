"""
Language Handling Utilities for Alya Bot.

This module provides multilingual support including translation loading,
language detection, and language-specific formatting.
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path

from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, LANGUAGE_FILE_MAPPING

logger = logging.getLogger(__name__)

# Base paths for locales
BASE_DIR = Path(__file__).parent.parent
LOCALE_DIR = BASE_DIR / "config" / "locales"

class LanguageHandler:
    """
    Handler for loading and accessing language translations.
    
    This class manages loading translations from YAML files,
    detecting languages, and providing translated responses.
    """
    
    def __init__(self):
        """Initialize language handler with default settings."""
        # Initialize translations dictionary - FIX: Add this line
        self.translations = {}
        self.default_language = DEFAULT_LANGUAGE
        self.supported_languages = SUPPORTED_LANGUAGES
        self.fallbacks = {"en": "id", "id": "en"}  # Fallback chain
        
        # Track loaded languages
        self.loaded_languages = set()
        
        # Load all languages
        self._load_all_languages()
        
    def _get_language_file_path(self, language: str) -> Path:
        """
        Get path to language file.
        
        Args:
            language: Language code
            
        Returns:
            Path to language file
        """
        # Get filename from mapping or fallback to language code
        filename = LANGUAGE_FILE_MAPPING.get(language, language)
        return LOCALE_DIR / f"{filename}.yaml"
        
    def _load_all_languages(self):
        """Load all supported languages."""
        # Ensure default language is loaded first
        self._load_language(self.default_language)
        
        # Load remaining languages
        for lang in self.supported_languages:
            if lang != self.default_language:
                self._load_language(lang)
                
        # Log language loading status
        logger.info(f"Loaded translations for {len(self.loaded_languages)} languages: {', '.join(self.loaded_languages)}")
        
    def _load_language(self, language: str) -> bool:
        """
        Load translations for a specific language.
        
        Args:
            language: Language code
            
        Returns:
            True if loaded successfully
        """
        if language in self.loaded_languages:
            return True
            
        file_path = self._get_language_file_path(language)
        
        try:
            if not file_path.exists():
                logger.warning(f"Translation file not found: {file_path}")
                return False
                
            # Load translations from file
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = yaml.safe_load(f)
                
            # Check if translations are valid
            if not isinstance(translations, dict):
                logger.error(f"Invalid translation format in {file_path}")
                return False
                
            # Set translations
            try:
                self.translations[language] = translations
                self.loaded_languages.add(language)
                return True
            except Exception as e:
                logger.error(f"Error loading translations for {language}: {e}")
                # Initialize with empty dictionary if not already present
                self.translations[language] = {}
                return False
                
        except Exception as e:
            logger.error(f"Error loading language file {file_path}: {e}")
            return False
            
    def get_text(self, key: str, language: str = None) -> str:
        """
        Get translated text for a key.
        
        Args:
            key: Translation key
            language: Language code
            
        Returns:
            Translated text or key if translation not found
        """
        # Use default language if none specified
        language = language or self.default_language
        
        # Ensure language is loaded
        if language not in self.loaded_languages:
            self._load_language(language)
            
        # Try to get translation
        try:
            translations = self.translations.get(language, {})
            
            # Check multilingual section first
            if "multilingual" in translations and language in translations["multilingual"]:
                if key in translations["multilingual"][language]:
                    return translations["multilingual"][language][key]
            
            # Check main translations
            if key in translations:
                return translations[key]
                
            # Try fallback language
            fallback = self.fallbacks.get(language)
            if fallback and fallback in self.translations:
                fallback_translations = self.translations[fallback]
                if key in fallback_translations:
                    return fallback_translations[key]
                
            # If still not found, try default language
            if language != self.default_language and self.default_language in self.translations:
                default_translations = self.translations[self.default_language]
                if key in default_translations:
                    return default_translations[key]
        except Exception as e:
            logger.error(f"Error getting translation for key '{key}': {e}")
            
        # Return key as last resort
        logger.warning(f"Translation not found for key: {key}")
        return key
        
    def format_text(self, key: str, language: str = None, **kwargs) -> str:
        """
        Get and format translated text with variables.
        
        Args:
            key: Translation key
            language: Language code
            **kwargs: Variables for formatting
            
        Returns:
            Formatted translated text
        """
        text = self.get_text(key, language)
        
        try:
            # Replace variables
            for var_name, var_value in kwargs.items():
                placeholder = "{" + var_name + "}"
                text = text.replace(placeholder, str(var_value))
        except Exception as e:
            logger.error(f"Error formatting text: {e}")
            
        return text
        
    def detect_language(self, text: str) -> str:
        """
        Detect language of input text.
        
        Args:
            text: Input text
            
        Returns:
            Detected language code or default language
        """
        # Simple detection based on common words
        # For a production system, consider using a proper language detection library
        common_words = {
            "id": ["apa", "ini", "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "tidak"],
            "en": ["the", "is", "and", "to", "of", "in", "you", "that", "have", "for"]
        }
        
        text_lower = text.lower()
        scores = {}
        
        for lang, words in common_words.items():
            scores[lang] = sum(1 for word in words if f" {word} " in f" {text_lower} ")
            
        # Get language with highest score
        if scores:
            max_score = max(scores.values())
            # Only return detected language if score is significant
            if max_score > 1:
                for lang, score in scores.items():
                    if score == max_score:
                        return lang
                        
        # Return default language if detection failed
        return self.default_language

    def get_response(self, key: str, language: str = None) -> str:
        """
        Get response text for a specific key from translations.
        
        Args:
            key: Response key from responses YAML
            language: Optional language code (defaults to default language)
            
        Returns:
            Formatted response text or empty string if not found
        """
        try:
            # Use default language if none specified
            language = language or self.default_language
            
            # Try to get from translations dict
            if language in self.translations and key in self.translations[language]:
                return self.translations[language][key]
            
            # If not found and not default language, try default
            if language != self.default_language:
                if self.default_language in self.translations and key in self.translations[self.default_language]:
                    return self.translations[self.default_language][key]
                    
            # Not found
            logger.warning(f"Response not found for key: '{key}' in language: '{language}'")
            return ""
        except Exception as e:
            logger.error(f"Error getting response for key '{key}': {e}")
            return ""

# Create singleton instance
language_handler = LanguageHandler()

# Convenience functions
def get_text(key: str, language: str = None) -> str:
    """
    Get translated text (convenience function).
    
    Args:
        key: Translation key
        language: Language code
        
    Returns:
        Translated text
    """
    return language_handler.get_text(key, language)

def format_text(key: str, language: str = None, **kwargs) -> str:
    """
    Format translated text (convenience function).
    
    Args:
        key: Translation key
        language: Language code
        **kwargs: Variables for formatting
        
    Returns:
        Formatted translated text
    """
    return language_handler.format_text(key, language, **kwargs)

def detect_language(text: str) -> str:
    """
    Detect language of text (convenience function).
    
    Args:
        text: Input text
        
    Returns:
        Detected language code
    """
    return language_handler.detect_language(text)

def get_response(key: str, language: str = None) -> str:
    """
    Get response text from translations (convenience function).
    
    Args:
        key: Response key from responses YAML
        language: Language code (defaults to default language)
        
    Returns:
        Response text or empty string if not found
    """
    return language_handler.get_response(key, language)

def get_language(user_data: Dict[str, Any]) -> str:
    """
    Get user's preferred language.
    
    Args:
        user_data: User data dictionary
        
    Returns:
        Language code
    """
    return user_data.get("language", DEFAULT_LANGUAGE)

def get_prompt_language_instruction(language: str) -> str:
    """
    Get language instruction for model prompts.
    
    Args:
        language: Language code
        
    Returns:
        Language instruction string
    """
    if language == "en":
        return "IMPORTANT: RESPOND IN ENGLISH."
    else:
        return "IMPORTANT: RESPOND IN INDONESIAN."
