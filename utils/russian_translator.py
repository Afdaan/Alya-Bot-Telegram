"""
Russian expression detection and translation for Alya Bot.

Detects when Alya uses Russian (Cyrillic) expressions in emotional moments
and provides translations to users.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Russian-English translation dictionary for common expressions
RUSSIAN_TRANSLATIONS: Dict[str, str] = {
    "бака": "baka (idiot/fool)",
    "дурак": "durak (stupid/fool)",
    "что": "chto (what)",
    "ну": "nu (well/so)",
    "аи": "ai (oh)",
    "ах": "akh (oh/ah)",
    "боже": "bozhe (oh god)",
    "мой": "moy (my)",
    "моя": "moya (my - feminine)",
    "боюсь": "boyus (I'm afraid)",
    "люблю": "lyublyu (I love)",
    "ненавижу": "nenavizhu (I hate)",
    "не": "ne (no/not)",
    "да": "da (yes)",
    "нет": "net (no)",
    "сука": "suka (bitch - harsh expression)",
    "гадость": "gadost (garbage/nasty)",
    "хорошо": "khorosho (good/okay)",
    "плохо": "plokho (bad)",
    "милый": "milyy (cute/sweet - masculine)",
    "милая": "milaya (cute/sweet - feminine)",
    "дешевый": "deshetyy (cheap)",
    "красивый": "krasivyy (beautiful - masculine)",
    "красивая": "krasivaya (beautiful - feminine)",
    "умный": "umnyy (smart - masculine)",
    "умная": "umnaya (smart - feminine)",
    "глупый": "glupyy (stupid - masculine)",
    "глупая": "glupaya (stupid - feminine)",
    "привет": "privet (hello)",
    "пока": "poka (bye)",
    "спасибо": "spasibo (thank you)",
    "пожалуйста": "pozhaluysta (please)",
    "извини": "izvini (sorry - informal)",
    "извините": "izvinite (sorry - formal)",
    "ладно": "adno (alright)",
    "конечно": "konechno (of course)",
    "может": "mozhet (maybe/can)",
    "должна": "dolzhna (must/should - feminine)",
    "должен": "dolzhen (must/should - masculine)",
    "хочу": "khochu (I want)",
    "можно": "mozhno (can/may)",
    "нельзя": "nelsya (cannot/must not)",
    "понимаешь": "ponimaesh (you understand - informal)",
    "знаешь": "znaesh (you know - informal)",
}


def detect_russian_expressions(text: str) -> List[str]:
    """Detect and extract Russian (Cyrillic) words from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of unique Russian words found (case-insensitive)
    """
    if not text:
        return []
    
    # Cyrillic Unicode range: \u0400-\u04FF
    # Pattern matches one or more Cyrillic characters (words)
    cyrillic_pattern = r'[а-яёА-ЯЁ]+'
    matches = re.findall(cyrillic_pattern, text)
    
    if not matches:
        return []
    
    # Return unique Russian words (normalized to lowercase for matching)
    unique_words = list(set(word.lower() for word in matches))
    return unique_words


def has_russian_expressions(text: str) -> bool:
    """Quick check if text contains any Russian expressions.
    
    Args:
        text: Text to check
        
    Returns:
        True if Cyrillic text found, False otherwise
    """
    if not text:
        return False
    return bool(re.search(r'[а-яёА-ЯЁ]', text))


def get_russian_translations_for_words(
    russian_words: List[str]
) -> Dict[str, str]:
    """Get translations for detected Russian words.
    
    Args:
        russian_words: List of Russian words to translate
        
    Returns:
        Dictionary of word -> translation pairs
    """
    if not russian_words:
        return {}
    
    translations = {}
    for word in russian_words:
        word_lower = word.lower()
        if word_lower in RUSSIAN_TRANSLATIONS:
            translations[word] = RUSSIAN_TRANSLATIONS[word_lower]
    
    return translations


# ---------- Romanization fallback for unmapped Russian words ----------

def romanize_russian_word(word: str) -> str:
    """Romanize Russian (Cyrillic) word to Latin characters.
    
    Uses transliteration rules for Russian Cyrillic alphabet.
    This is a fallback for Russian words not in the translation dictionary.
    
    Args:
        word: Russian word in Cyrillic
        
    Returns:
        Romanized (transliterated) version of the word
    """
    if not word:
        return ""
    
    # Russian Cyrillic to Latin transliteration mapping
    # Based on common transliteration standards (ISO 9, BGN/PCGN)
    transliteration_map = {
        # Uppercase
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D",
        "Е": "E", "Ё": "Yo", "Ж": "Zh", "З": "Z", "И": "I",
        "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N",
        "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
        "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch",
        "Ш": "Sh", "Щ": "Shch", "Ъ": "", "Ы": "Y", "Ь": "",
        "Э": "E", "Ю": "Yu", "Я": "Ya",
        # Lowercase
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
        "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
        "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    }
    
    romanized = ""
    for char in word:
        romanized += transliteration_map.get(char, char)
    
    return romanized


def get_translation_for_word(word: str) -> str:
    """Get translation for a Russian word with dictionary + romanization fallback.
    
    If word is in dictionary, return translation.
    If word is not in dictionary, return romanized version with note.
    
    Args:
        word: Russian word to translate
        
    Returns:
        Translation string or romanized fallback
    """
    if not word:
        return ""
    
    word_lower = word.lower()
    
    # Check dictionary first
    if word_lower in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[word_lower]
    
    # Fallback: romanize the word
    romanized = romanize_russian_word(word)
    if romanized and romanized != word:
        return f"{romanized} (romanized)"
    
    return word  # Return original if romanization failed


async def get_translation_for_word_with_ai(
    word: str,
    gemini_client: Optional[object] = None
) -> str:
    """Get translation for Russian word with AI fallback for unknown words.
    
    Uses dictionary first, then AI for unknown Russian words.
    This is async to support integration with Gemini client.
    
    Args:
        word: Russian word to translate
        gemini_client: Optional GeminiClient instance for AI translation
        
    Returns:
        Translation string or romanized fallback
    """
    if not word:
        return ""
    
    word_lower = word.lower()
    
    # Check dictionary first
    if word_lower in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[word_lower]
    
    # Try AI translation if client available
    if gemini_client:
        try:
            prompt = f"""Translate this Russian word to English with brief meaning:
"{word}"

Respond in format: word (meaning) 
Example: любовь (love)
Keep it short and simple."""
            
            translation = await gemini_client.generate_response(
                user_id=0,  # System request, no user context
                username="system",
                message=prompt,
                context="",
                relationship_level=0,
                is_admin=False,
                lang="en",
                retry_count=1,
                is_media_analysis=False,
                media_context=None
            )
            
            if translation and translation.strip():
                return translation.strip()
        except Exception as e:
            logger.debug(f"AI translation failed for '{word}': {e}")
    
    # Fallback: romanize if AI not available or failed
    romanized = romanize_russian_word(word)
    if romanized and romanized != word:
        return f"{romanized} (romanized)"
    
    return word  # Return original if all else fails


def format_russian_translation_block(
    russian_words: List[str],
    lang: str = "id"
) -> str:
    """Format Russian words with their translations as HTML blockquote.
    
    Uses dictionary lookup first, then romanization fallback for unknown words.
    This is the synchronous version - use async version for AI-powered translation.
    
    Args:
        russian_words: List of Russian words found
        lang: User language preference (id or en)
        
    Returns:
        Formatted HTML translation block, or empty string if no translations found
    """
    if not russian_words:
        return ""
    
    # Build header based on language
    headers = {
        "id": "💬 <i>Terjemahan Russian:</i>",
        "en": "💬 <i>Russian Translation:</i>",
    }
    header = headers.get(lang, headers["en"])
    
    # Build translation lines with fallback romanization
    translation_lines = [header]
    for word in sorted(set(russian_words)):
        translation = get_translation_for_word(word)
        if translation:
            translation_lines.append(f"<b>{word}</b> = {translation}")
    
    # Return empty if only header exists
    if len(translation_lines) <= 1:
        return ""
    
    # Format as HTML blockquote
    translation_text = "\n".join(translation_lines)
    return f"<blockquote>{translation_text}</blockquote>"


async def format_russian_translation_block_with_ai(
    russian_words: List[str],
    lang: str = "id",
    gemini_client: Optional[object] = None
) -> str:
    """Format Russian words with translations using AI fallback for unknown words.
    
    This is the async version that can use Gemini for unknown Russian expressions.
    More robust for random/edge-case Russian generation from AI.
    
    Args:
        russian_words: List of Russian words found
        lang: User language preference (id or en)
        gemini_client: Optional GeminiClient for AI-powered translation
        
    Returns:
        Formatted HTML translation block, or empty string if no translations found
    """
    if not russian_words:
        return ""
    
    # Build header based on language
    headers = {
        "id": "💬 <i>Terjemahan Russian:</i>",
        "en": "💬 <i>Russian Translation:</i>",
    }
    header = headers.get(lang, headers["en"])
    
    # Build translation lines with AI fallback support
    translation_lines = [header]
    
    # If gemini_client available, use async AI translation for all unknown words
    if gemini_client:
        for word in sorted(set(russian_words)):
            translation = await get_translation_for_word_with_ai(word, gemini_client)
            if translation:
                translation_lines.append(f"<b>{word}</b> = {translation}")
    else:
        # Fallback to synchronous dictionary + romanization
        for word in sorted(set(russian_words)):
            translation = get_translation_for_word(word)
            if translation:
                translation_lines.append(f"<b>{word}</b> = {translation}")
    
    # Return empty if only header exists
    if len(translation_lines) <= 1:
        return ""
    
    # Format as HTML blockquote
    translation_text = "\n".join(translation_lines)
    return f"<blockquote>{translation_text}</blockquote>"


def append_russian_translation_if_needed(
    response: str,
    lang: str = "id"
) -> str:
    """Append Russian translation paragraph to response if it contains Russian.
    
    Synchronous version using dictionary + romanization fallback.
    
    Args:
        response: The bot response text (may be HTML formatted)
        lang: User language preference (id or en)
        
    Returns:
        Original response with Russian translation block appended if applicable
    """
    if not response or not has_russian_expressions(response):
        return response
    
    # Detect Russian words in response
    russian_words = detect_russian_expressions(response)
    if not russian_words:
        return response
    
    # Get translation block
    translation_block = format_russian_translation_block(russian_words, lang)
    if not translation_block:
        return response
    
    # Append translation block to response
    try:
        return f"{response}\n\n{translation_block}"
    except Exception as e:
        logger.error(f"Error appending Russian translation: {e}")
        return response


async def append_russian_translation_if_needed_async(
    response: str,
    lang: str = "id",
    gemini_client: Optional[object] = None
) -> str:
    """Append Russian translation to response with optional AI-powered translation.
    
    Async version that can use Gemini for unknown Russian expressions.
    Better for handling random/edge-case Russian from AI generation.
    
    Args:
        response: The bot response text (may be HTML formatted)
        lang: User language preference (id or en)
        gemini_client: Optional GeminiClient for AI-powered translation
        
    Returns:
        Original response with Russian translation block appended if applicable
    """
    if not response or not has_russian_expressions(response):
        return response
    
    # Detect Russian words in response
    russian_words = detect_russian_expressions(response)
    if not russian_words:
        return response
    
    # Get translation block with optional AI fallback
    translation_block = await format_russian_translation_block_with_ai(
        russian_words, 
        lang, 
        gemini_client
    )
    if not translation_block:
        return response
    
    # Append translation block to response
    try:
        return f"{response}\n\n{translation_block}"
    except Exception as e:
        logger.error(f"Error appending Russian translation (async): {e}")
        return response
