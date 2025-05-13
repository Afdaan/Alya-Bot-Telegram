"""
Language Handling for Alya Telegram Bot.

This module provides multilingual support with response templates,
language management, and formatting functions.
"""

import logging
from typing import Dict, Any, Optional
from telegram.ext import CallbackContext

from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# =========================
# Response Templates
# =========================

RESPONSES = {
    # Basic commands
    "start": {
        "id": "Halo\\! Alya\\-chan di sini untuk membantu kamu\\~ 🌸\n\nAku sangat senang bisa berbicara denganmu\\! Bagaimana kabarmu hari ini\\? ✨",
        "en": "Hello\\! Alya\\-chan is here to help you\\~ 🌸\n\nI'm so happy to talk with you\\! How are you doing today\\? ✨"
    },
    "help": {
        "id": "Ini adalah daftar perintah yang bisa kamu gunakan\\:",
        "en": "Here is the list of commands you can use\\:"
    },
    "reset": {
        "id": "History chat telah dihapus\\! Ayo mulai percakapan baru\\~ 💕",
        "en": "Chat history has been cleared\\! Let's start a new conversation\\~ 💕"
    },
    
    # System messages
    "language_changed": {
        "id": "Bahasa telah diubah ke *{language}*\\. Alya\\-chan akan berbicara dalam Bahasa Indonesia sekarang\\~",
        "en": "Language has been changed to *{language}*\\. Alya\\-chan will speak in English now\\~"
    },
    "dev_only": {
        "id": "Ara\\~ Command ini khusus developer sayang\\~ 💅✨",
        "en": "Ara\\~ This command is for developers only darling\\~ 💅✨"
    },
    
    # Search-related
    "search_usage": {
        "id": "Cara penggunaan\\:\n\\!search \\<kata kunci\\>\n\nContoh\\:\n\\!search jadwal KRL lempuyangan jogja",
        "en": "How to use\\:\n\\!search \\<keywords\\>\n\nExample\\:\n\\!search train schedule from Jakarta to Bandung"
    },
    "searching": {
        "id": "🔍 Sedang mencari informasi\\.\\.\\.",
        "en": "🔍 Searching for information\\.\\.\\."
    },
    
    # Error messages
    "timeout": {
        "id": "Aduh\\, maaf ya\\~ Alya\\-chan butuh waktu lebih lama untuk memikirkan jawaban yang tepat\\. Coba tanyakan dengan cara yang lebih sederhana ya\\? 🥺💕",
        "en": "Oops\\, sorry\\~ Alya\\-chan needs more time to think about the right answer\\. Could you ask in a simpler way\\? 🥺💕" 
    },
    "error": {
        "id": "Gomenasai\\~ Ada masalah kecil\\. Alya akan lebih baik lagi ya\\~ 🥺💕",
        "en": "Gomenasai\\~ There was a small problem\\. Alya will do better next time\\~ 🥺💕"
    },
    
    # Language command help
    "lang_help": {
        "id": "*Pengaturan Bahasa*\n\n*Bahasa saat ini:* `{current_code}` \\({current_name}\\)\n\n*Cara penggunaan:*\n`/lang <kode_bahasa>`\n\n*Bahasa yang tersedia:*\n• `id` \\- Bahasa Indonesia\n• `en` \\- English \\(Inggris\\)\n\n*Contoh:*\n`/lang en` \\- Ganti ke Bahasa Inggris\n`/lang id` \\- Ganti ke Bahasa Indonesia",
        "en": "*Language Settings*\n\n*Current language:* `{current_code}` \\({current_name}\\)\n\n*Usage:*\n`/lang <language_code>`\n\n*Available languages:*\n• `id` \\- Indonesian\n• `en` \\- English\n\n*Example:*\n`/lang en` \\- Switch to English\n`/lang id` \\- Switch to Indonesian"
    },
    "lang_invalid": {
        "id": "*Kode bahasa tidak valid:* `{code}`\n\n*Bahasa yang tersedia:*\n• `id` \\- Bahasa Indonesia\n• `en` \\- English \\(Inggris\\)",
        "en": "*Invalid language code:* `{code}`\n\n*Available languages:*\n• `id` \\- Indonesian\n• `en` \\- English"
    },
    "lang_success": {
        "id": "*Bahasa berhasil diubah ke {language_name}*\n\nAlya\\-chan akan berbicara dalam Bahasa Indonesia sekarang\\~",
        "en": "*Language changed to {language_name}*\n\nAlya\\-chan will speak in English now\\~"
    }
}

# =========================
# Language Functions
# =========================

def get_language(context: Optional[CallbackContext] = None) -> str:
    """
    Get current language setting from context.
    
    Args:
        context: CallbackContext containing bot_data
        
    Returns:
        Language code (defaults to DEFAULT_LANGUAGE if not set)
    """
    if context and hasattr(context, 'bot_data'):
        return context.bot_data.get("language", DEFAULT_LANGUAGE)
    return DEFAULT_LANGUAGE


def set_language(context: CallbackContext, language_code: str) -> bool:
    """
    Set the language in the bot context.
    
    Args:
        context: CallbackContext for storing language setting
        language_code: Language code to set
        
    Returns:
        True if language was set successfully, False otherwise
    """
    if language_code in SUPPORTED_LANGUAGES:
        context.bot_data["language"] = language_code
        logger.info(f"Language set to {language_code} ({SUPPORTED_LANGUAGES[language_code]})")
        return True
    return False


def get_response(key: str, context: Optional[CallbackContext] = None, 
                language: Optional[str] = None, **kwargs) -> str:
    """
    Get a localized response with formatting.
    
    Args:
        key: Response key
        context: CallbackContext for getting language setting
        language: Override language (optional)
        **kwargs: Format parameters for the response template
    
    Returns:
        Localized and formatted response text
    """
    # Determine language to use - priority: explicit language > context > default
    selected_language = DEFAULT_LANGUAGE
    
    if language is not None:
        selected_language = language
    elif context is not None:
        selected_language = get_language(context)
        
    # Get response template
    response_dict = RESPONSES.get(key, {})
    response = response_dict.get(selected_language, response_dict.get(DEFAULT_LANGUAGE, f"Missing response key: {key}"))
    
    # Format with kwargs if provided
    if kwargs:
        try:
            # Escape curly braces for Markdown V2 before formatting
            escaped_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, str):
                    # Double escape curly braces to ensure they are properly escaped
                    escaped_kwargs[k] = v.replace('{', '\\{').replace('}', '\\}')
                else:
                    escaped_kwargs[k] = v
            
            response = response.format(**escaped_kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key in response template: {e}")
            # Attempt to use original template if formatting fails
            response = f"Error formatting response: {str(e)}"
    
    # Double check that all { and } are properly escaped
    response = response.replace('{', '\\{').replace('}', '\\}')
    
    return response


def get_prompt_language_instruction(language: Optional[str] = None, context: Optional[CallbackContext] = None) -> str:
    """
    Get language instruction for AI prompts.
    
    Provides a soft language preference rather than a strict requirement,
    allowing the AI to respond in other languages if requested by the user.
    
    Args:
        language: Language code (optional)
        context: CallbackContext for getting language setting (optional)
        
    Returns:
        Instruction string for the AI model
    """
    # If language not provided, get from context
    if language is None and context is not None:
        language = get_language(context)
    elif language is None:
        language = DEFAULT_LANGUAGE
    
    if language == "en":
        return """
        Your default response language is English.
        Please respond in English unless the user specifically requests another language.
        If the user asks you to speak in another language (like Japanese, Sundanese, Javanese, etc.), 
        you can accommodate their request and respond in that language.
        """
    elif language == "id":
        return """
        Bahasa default untuk responmu adalah Bahasa Indonesia.
        Mohon jawab dalam Bahasa Indonesia kecuali jika pengguna secara khusus meminta bahasa lain.
        Jika pengguna memintamu berbicara dalam bahasa lain (seperti Jawa, Sunda, Jepang, dll.),
        kamu boleh mengikuti permintaan mereka dan menjawab dalam bahasa tersebut.
        """
    return ""


def translate_key(key: str, language: Optional[str] = None, context: Optional[CallbackContext] = None, **kwargs) -> str:
    """
    Shorthand function to translate a key based on current language.
    
    Args:
        key: Translation key
        language: Language code (optional)
        context: CallbackContext for getting language (optional)
        **kwargs: Format parameters
        
    Returns:
        Translated string
    """
    # Determine language to use
    selected_language = language
    if selected_language is None and context is not None:
        selected_language = get_language(context)
    
    # Get translated string
    return get_response(key, language=selected_language, **kwargs)
