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

# Common Russian-Latin hybrid variants (typos, keyboard misdetection, etc.)
RUSSIAN_LATIN_VARIANTS: Dict[str, str] = {
    "boze": "боже",      # Bože → боже (oh god)
    "boz": "боже",
    "buze": "боже",
    "buzhe": "боже",
    "bozhe": "боже",
    "durak": "дурак",    # Common typo variant
    "durack": "дурак",
    "baka": "бака",
    "baca": "бака",
}


def detect_russian_expressions(text: str) -> List[str]:
    """Detect and extract Russian (Cyrillic) words from text.
    
    Handles:
    - Pure Cyrillic words
    - Cyrillic with diacritics (é, è, ž, etc.)
    - Mixed case variations
    - Common Russian-Latin variants (typos like "Bože", "boze")
    - Latin words with Cyrillic-like diacritics
    
    Args:
        text: Text to analyze
        
    Returns:
        List of unique Russian words found (normalized)
    """
    if not text:
        return []
    
    detected = []
    
    # Pattern 1: Pure Cyrillic (а-я, А-Я, ё, Ё)
    cyrillic_pattern = r'[а-яёА-ЯЁ]+'
    cyrillic_matches = re.findall(cyrillic_pattern, text, re.UNICODE)
    
    if cyrillic_matches:
        detected.extend([m.lower() for m in cyrillic_matches])
    
    # Pattern 2: Latin words with diacritics (Slavic variants like "Bože", "naïve", etc.)
    # Match words containing diacritical marks that suggest Russian/Slavic origin
    # Pattern: Latin letters + at least one diacritical mark
    diacritic_pattern = r'\b[a-zA-Z]*[àáâãäåèéêëìíîïòóôõöùúûüýÿžžčščđ][a-zA-Z]*\b'
    diacritic_matches = re.findall(diacritic_pattern, text, re.UNICODE)
    
    if diacritic_matches:
        for match in diacritic_matches:
            match_lower = match.lower()
            # Check if this matches a known Russian variant
            if match_lower in RUSSIAN_LATIN_VARIANTS:
                canonical = RUSSIAN_LATIN_VARIANTS[match_lower]
                detected.append(canonical.lower())
            elif normalize_russian_variant(match_lower) in RUSSIAN_LATIN_VARIANTS:
                canonical = RUSSIAN_LATIN_VARIANTS[normalize_russian_variant(match_lower)]
                detected.append(canonical.lower())
            # Also add the original for display
            detected.append(match_lower)
    
    # Pattern 3: Known Russian-Latin variants (typos/keyboard misdetection)
    text_lower = text.lower()
    for variant, canonical in RUSSIAN_LATIN_VARIANTS.items():
        if variant in text_lower and variant not in [m.lower() for m in diacritic_matches]:
            # Add canonical Cyrillic form
            detected.append(canonical.lower())
            # Find actual occurrence in text with original case
            pattern = re.compile(re.escape(variant), re.IGNORECASE)
            matches = pattern.findall(text)
            if matches:
                detected.append(matches[0].lower())
    
    # Return unique Russian words
    return list(set(detected))


def has_russian_expressions(text: str) -> bool:
    """Quick check if text contains any Russian expressions.
    
    Checks for:
    - Pure Cyrillic characters
    - Latin words with diacritics (Slavic variants like "Bože", "čeština", etc.)
    - Common Russian-Latin variants (typos like "Bože", "boze", etc.)
    
    Args:
        text: Text to check
        
    Returns:
        True if Russian detected, False otherwise
    """
    if not text:
        return False
    
    # Check for pure Cyrillic
    if re.search(r'[а-яёА-ЯЁ]', text):
        return True
    
    # Check for Latin with diacritics (Slavic-looking)
    if re.search(r'[àáâãäåèéêëìíîïòóôõöùúûüýÿžčščđ]', text, re.UNICODE):
        return True
    
    # Check for common Russian-Latin variants
    text_lower = text.lower()
    for variant in RUSSIAN_LATIN_VARIANTS.keys():
        if variant in text_lower:
            return True
    
    return False


def get_russian_translations_for_words(
    russian_words: List[str]
) -> Dict[str, str]:
    """Get translations for detected Russian words.
    
    Uses normalization to handle variants, typos, and diacritics.
    
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
        
        # Try direct lookup first
        if word_lower in RUSSIAN_TRANSLATIONS:
            translations[word] = RUSSIAN_TRANSLATIONS[word_lower]
            continue
        
        # Try normalized variant (removes diacritics, handles typos)
        normalized = normalize_russian_variant(word)
        if normalized in RUSSIAN_TRANSLATIONS:
            translations[word] = RUSSIAN_TRANSLATIONS[normalized]
    
    return translations


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
    
    # Russian Cyrillic to Latin transliteration mapping (ISO 9, BGN/PCGN standards)
    transliteration_map = {
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D",
        "Е": "E", "Ё": "Yo", "Ж": "Zh", "З": "Z", "И": "I",
        "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N",
        "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
        "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch",
        "Ш": "Sh", "Щ": "Shch", "Ъ": "", "Ы": "Y", "Ь": "",
        "Э": "E", "Ю": "Yu", "Я": "Ya",
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
    """Get translation for a Russian word with variant/typo handling.
    
    Uses variant mapping, normalization, then romanization.
    Handles:
    - Pure Cyrillic lookups
    - Latin variants (e.g., "Bože" → "боже")
    - Diacritic removal
    - Fallback romanization
    
    Args:
        word: Russian word to translate (may have typos/diacritics)
        
    Returns:
        Translation string or romanized fallback
    """
    if not word:
        return ""
    
    word_lower = word.lower()
    
    # Check direct Cyrillic dictionary lookup
    if word_lower in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[word_lower]
    
    # Check if it's a known Latin variant (e.g., "bože" → "боже")
    if word_lower in RUSSIAN_LATIN_VARIANTS:
        canonical = RUSSIAN_LATIN_VARIANTS[word_lower].lower()
        if canonical in RUSSIAN_TRANSLATIONS:
            return RUSSIAN_TRANSLATIONS[canonical]
    
    # Try normalized variant (handles diacritics like "Bože" → "boze" → lookup)
    normalized = normalize_russian_variant(word)
    if normalized in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[normalized]
    
    # Check if normalized form maps to a known variant
    if normalized in RUSSIAN_LATIN_VARIANTS:
        canonical = RUSSIAN_LATIN_VARIANTS[normalized].lower()
        if canonical in RUSSIAN_TRANSLATIONS:
            return RUSSIAN_TRANSLATIONS[canonical]
    
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
                user_id=0,
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
    
    # Separate known and unknown words for efficient processing
    unique_words = sorted(set(russian_words))
    known_translations = {}
    unknown_words = []
    
    # First pass: collect known translations
    for word in unique_words:
        word_lower = word.lower()
        if word_lower in RUSSIAN_TRANSLATIONS:
            known_translations[word] = RUSSIAN_TRANSLATIONS[word_lower]
        else:
            unknown_words.append(word)
    
    # Second pass: AI translate unknown words if client available
    ai_translations = {}
    if unknown_words and gemini_client:
        try:
            prompt = build_gemini_translation_prompt(unknown_words)
            response = await gemini_client.generate_response(
                user_id=0,
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
            
            if response:
                # Parse AI response: "word = meaning" format
                for line in response.split("\n"):
                    line = line.strip()
                    if "=" in line:
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            word_part = parts[0].strip().strip('"\'')
                            meaning = parts[1].strip()
                            ai_translations[word_part] = meaning
        except Exception as e:
            logger.debug(f"AI translation batch failed: {e}")
    
    # Build final translation lines
    translation_lines = [header]
    
    for word in unique_words:
        translation = None
        
        # Try known translation first
        if word in known_translations:
            translation = known_translations[word]
        # Try AI translation
        elif word in ai_translations:
            translation = ai_translations[word]
        # Fallback to romanization
        else:
            romanized = romanize_russian_word(word)
            if romanized and romanized != word:
                translation = f"{romanized} (romanized)"
        
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


def normalize_russian_variant(word: str) -> str:
    """Normalize Russian word variant to canonical form for dictionary lookup.
    
    Handles:
    - Latin diacritics (é, è, ž, etc.) → remove
    - Case variations → lowercase
    - Extra spaces → remove
    
    Args:
        word: Russian word (possibly with variants/typos)
        
    Returns:
        Normalized word for dictionary lookup
    """
    if not word:
        return ""
    
    # Convert to lowercase and remove diacritics
    normalized = word.lower().strip()
    
    # Map common diacritics to base Latin characters (e.g., "Bože" → "boze")
    diacritic_map = {
        'é': 'e', 'è': 'e', 'ê': 'e',
        'ä': 'a', 'ö': 'o', 'ü': 'u',
        'ž': 'z', 'č': 'c', 'š': 's', 'ć': 'c', 'đ': 'd',
        'à': 'a', 'ù': 'u', 'ì': 'i',
        'ý': 'y', 'ý': 'y',
    }
    
    for diacritic, replacement in diacritic_map.items():
        normalized = normalized.replace(diacritic, replacement)
    
    return normalized


def build_gemini_translation_prompt(russian_words: List[str]) -> str:
    """Build a prompt for Gemini to translate Russian expressions.
    
    Creates a single, efficient prompt that requests translations for
    multiple Russian words at once.
    
    Args:
        russian_words: List of Russian words to translate
        
    Returns:
        Prompt string for Gemini translation request
    """
    if not russian_words:
        return ""
    
    # Remove duplicates and sort
    unique_words = sorted(set(russian_words))
    words_str = ", ".join([f'"{word}"' for word in unique_words])
    
    prompt = f"""Translate these Russian words/expressions to English with brief meanings.

Russian words: {words_str}

Respond in format:
word = meaning

Examples:
люблю = lyublyu (I love)
дурак = durak (fool)
боже = bozhe (oh god)

Keep meanings SHORT and concise. Only translate, no explanations."""
    
    return prompt
