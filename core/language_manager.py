"""
Simple language management system for Alya Bot multilingual support.
Focus on ID/EN switching without complex file loading - let Gemini handle the rest.
"""

import logging
from typing import Dict, Any, Optional

from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


class LanguageManager:
    """Simple multilingual support for bot responses."""
    
    def __init__(self):
        """Initialize language manager with basic translations."""
        self.default_language = DEFAULT_LANGUAGE
        self.supported_languages = set(SUPPORTED_LANGUAGES.keys())
        
        # Basic translation templates - Gemini will handle the rest
        self._create_basic_translations()
    
    def _create_basic_translations(self) -> None:
        """Create basic translation templates for language switching only."""
        self.basic_texts = {
            "id": {
                # Language switching messages only
                "language_changed": "Bahasa berhasil diubah ke Bahasa Indonesia! 🇮🇩\n\nAlya akan merespons dalam bahasa Indonesia mulai sekarang~ ✨",
                "language_current": "Bahasa saat ini: **Bahasa Indonesia** 🇮🇩",
                "language_usage": "Gunakan:\n• `/lang id` - Bahasa Indonesia 🇮🇩\n• `/lang en` - English 🇺🇸",
                "language_unsupported": "Hmph! Bahasa '{}' tidak didukung. Alya hanya bisa bahasa Indonesia dan English! 😤"
            },
            "en": {
                # Language switching messages only
                "language_changed": "Language successfully changed to English! 🇺🇸\n\nAlya will respond in English from now on~ ✨",
                "language_current": "Current language: **English** 🇺🇸", 
                "language_usage": "Use:\n• `/lang id` - Bahasa Indonesia 🇮🇩\n• `/lang en` - English 🇺🇸",
                "language_unsupported": "Hmph! Language '{}' is not supported. Alya only knows Indonesian and English! 😤"
            }
        }
    
    def get_text(self, key: str, language: str = None, **kwargs) -> str:
        """Get translated text for given key and language.
        
        Args:
            key: Translation key 
            language: Language code ('id' or 'en'). If None, uses default.
            **kwargs: Format arguments for string formatting
            
        Returns:
            Translated and formatted text
        """
        if language is None:
            language = self.default_language
            
        # Fallback to default language if requested language not available
        if language not in self.supported_languages:
            language = self.default_language
            
        # Get basic text
        text = self.basic_texts.get(language, {}).get(key, key)
        
        # Format string if kwargs provided
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"String formatting error for key '{key}': {e}")
                return text
                
        return text
    
    def is_supported_language(self, language: str) -> bool:
        """Check if language is supported."""
        return language in self.supported_languages
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages with display names."""
        return SUPPORTED_LANGUAGES
    
    def get_language_prompt(self, user_language: str) -> str:
        """Get language instruction for Gemini prompts.
        
        This tells Gemini what language to respond in.
        """
        if user_language == "id":
            return "Respond in Bahasa Indonesia with Alya's tsundere/waifu personality. Use casual Indonesian language with some cute expressions."
        elif user_language == "en":
            return "Respond in English with Alya's tsundere/waifu personality. Use casual English with some cute expressions."
        else:
            return "Respond in English with Alya's tsundere/waifu personality. Use casual English with some cute expressions."


# Global language manager instance
language_manager = LanguageManager()
