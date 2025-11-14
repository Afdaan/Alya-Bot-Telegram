"""
Russian expression detection and translation for Alya Bot.

Detects when Alya uses Russian (Cyrillic) expressions in emotional moments
and provides translations to users.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

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

RUSSIAN_LATIN_VARIANTS: Dict[str, str] = {
    "boze": "боже",
    "boz": "боже",
    "buze": "боже",
    "buzhe": "боже",
    "bozhe": "боже",
    "durak": "дурак",
    "durack": "дурак",
    "baka": "бака",
    "baca": "бака",
}

RUSSIAN_STOPWORDS: set = {
    "и", "в", "на", "для", "к", "с", "из", "по", "то", "не", "но", "или",
    "а", "то", "это", "как", "что", "где", "когда", "если", "ли", "быть",
    "их", "того", "той", "там", "тем", "те", "таки", "ее", "его", "она",
    "я", "он", "она", "оно", "они", "мы", "вы", "ты", "ему", "ей", "им",
    "мне", "тебе", "ему", "ей", "нас", "вас", "так", "же", "ж", "уж",
    "ну", "вот", "вдруг", "даже", "еще", "очень", "всё", "всё", "все",
    "она", "перед", "из", "под", "без", "кроме", "через", "над", "при",
    "очень", "более", "менее", "только", "всегда", "никогда", "иногда",
}

EMOTION_PRIORITY_EXPRESSIONS: set = {
    "боже", "боюсь", "люблю", "ненавижу", "сука", "гадость", "дурак",
    "бака", "милый", "милая", "красивый", "красивая", "умный", "умная",
    "глупый", "глупая", "хорошо", "плохо", "дешевый", "аи", "ах",
    "спасибо", "пожалуйста", "извини", "извините", "привет", "пока",
    "да", "нет", "мой", "моя", "ладно", "ору", "орёшь", "орал",
}


def detect_russian_expressions(text: str) -> List[str]:
    """Detect and extract Russian (Cyrillic) words from text.
    
    Deduplicates variants, filters stopwords, and prioritizes emotional expressions.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of unique Russian words found (canonical forms only)
    """
    if not text:
        return []
    
    detected_set = set()
    
    cyrillic_pattern = r'[а-яёА-ЯЁ]+'
    cyrillic_matches = re.findall(cyrillic_pattern, text, re.UNICODE)
    
    if cyrillic_matches:
        for match in cyrillic_matches:
            detected_set.add(match.lower())
    
    diacritic_pattern = r'\b[a-zA-Z]*[àáâãäåèéêëìíîïòóôõöùúûüýÿžžčščđ][a-zA-Z]*\b'
    diacritic_matches = re.findall(diacritic_pattern, text, re.UNICODE)
    
    if diacritic_matches:
        for match in diacritic_matches:
            match_lower = match.lower()
            normalized = normalize_russian_variant(match_lower)
            
            if normalized in RUSSIAN_LATIN_VARIANTS:
                canonical = RUSSIAN_LATIN_VARIANTS[normalized].lower()
                detected_set.add(canonical)
            elif match_lower in RUSSIAN_LATIN_VARIANTS:
                canonical = RUSSIAN_LATIN_VARIANTS[match_lower].lower()
                detected_set.add(canonical)
            else:
                detected_set.add(normalized if normalized != match_lower else match_lower)
    
    text_lower = text.lower()
    for variant, canonical in RUSSIAN_LATIN_VARIANTS.items():
        if variant in text_lower:
            detected_set.add(canonical.lower())
    
    filtered_words = [
        w for w in detected_set
        if w not in RUSSIAN_STOPWORDS or w in EMOTION_PRIORITY_EXPRESSIONS or w in RUSSIAN_TRANSLATIONS
    ]
    
    return sorted(list(filtered_words))


def has_russian_expressions(text: str) -> bool:
    """Quick check if text contains any Russian expressions.
    
    Args:
        text: Text to check
        
    Returns:
        True if Russian detected, False otherwise
    """
    if not text:
        return False
    
    if re.search(r'[а-яёА-ЯЁ]', text):
        return True
    
    if re.search(r'[àáâãäåèéêëìíîïòóôõöùúûüýÿžčščđ]', text, re.UNICODE):
        return True
    
    text_lower = text.lower()
    for variant in RUSSIAN_LATIN_VARIANTS.keys():
        if variant in text_lower:
            return True
    
    return False


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
            continue
        
        normalized = normalize_russian_variant(word)
        if normalized in RUSSIAN_TRANSLATIONS:
            translations[word] = RUSSIAN_TRANSLATIONS[normalized]
    
    return translations


def romanize_russian_word(word: str) -> str:
    """Romanize Russian (Cyrillic) word to Latin characters.
    
    Args:
        word: Russian word in Cyrillic
        
    Returns:
        Romanized version of the word
    """
    if not word:
        return ""
    
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
    
    Args:
        word: Russian word to translate
        
    Returns:
        Translation string or romanized fallback
    """
    if not word:
        return ""
    
    word_lower = word.lower()
    
    if word_lower in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[word_lower]
    
    if word_lower in RUSSIAN_LATIN_VARIANTS:
        canonical = RUSSIAN_LATIN_VARIANTS[word_lower].lower()
        if canonical in RUSSIAN_TRANSLATIONS:
            return RUSSIAN_TRANSLATIONS[canonical]
    
    normalized = normalize_russian_variant(word)
    if normalized in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[normalized]
    
    if normalized in RUSSIAN_LATIN_VARIANTS:
        canonical = RUSSIAN_LATIN_VARIANTS[normalized].lower()
        if canonical in RUSSIAN_TRANSLATIONS:
            return RUSSIAN_TRANSLATIONS[canonical]
    
    romanized = romanize_russian_word(word)
    if romanized and romanized != word:
        return f"{romanized} (romanized)"
    
    return word


async def get_translation_for_word_with_ai(
    word: str,
    gemini_client: Optional[object] = None
) -> str:
    """Get translation for Russian word with AI fallback for unknown words.
    
    Args:
        word: Russian word to translate
        gemini_client: Optional GeminiClient instance for AI translation
        
    Returns:
        Translation string or romanized fallback
    """
    if not word:
        return ""
    
    word_lower = word.lower()
    
    if word_lower in RUSSIAN_TRANSLATIONS:
        return RUSSIAN_TRANSLATIONS[word_lower]
    
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
    
    romanized = romanize_russian_word(word)
    if romanized and romanized != word:
        return f"{romanized} (romanized)"
    
    return word


def format_russian_translation_block(
    russian_words: List[str],
    lang: str = "id"
) -> str:
    """Format Russian words with their translations as HTML blockquote.
    
    Args:
        russian_words: List of Russian words found
        lang: User language preference (id or en)
        
    Returns:
        Formatted HTML translation block, or empty string if no translations
    """
    if not russian_words:
        return ""
    
    headers = {
        "id": "💬 <i>Terjemahan Russian:</i>",
        "en": "💬 <i>Russian Translation:</i>",
    }
    header = headers.get(lang, headers["en"])
    
    unique_words = sorted(set(russian_words))
    
    translation_lines = [header]
    for word in unique_words:
        translation = get_translation_for_word(word)
        if translation:
            translation_lines.append(f"<b>{word}</b> = {translation}")
    
    if len(translation_lines) <= 1:
        return ""
    
    translation_text = "\n".join(translation_lines)
    return f"<blockquote>{translation_text}</blockquote>"


async def format_russian_translation_block_with_ai(
    russian_words: List[str],
    lang: str = "id",
    gemini_client: Optional[object] = None
) -> str:
    """Format Russian words with translations using AI fallback for unknown words.
    
    Args:
        russian_words: List of Russian words found
        lang: User language preference (id or en)
        gemini_client: Optional GeminiClient for AI-powered translation
        
    Returns:
        Formatted HTML translation block, or empty string if no translations
    """
    if not russian_words:
        return ""
    
    headers = {
        "id": "💬 <i>Terjemahan Russian:</i>",
        "en": "💬 <i>Russian Translation:</i>",
    }
    header = headers.get(lang, headers["en"])
    
    unique_words = sorted(set(russian_words))
    unique_words = [w for w in unique_words if w and re.search(r'[а-яёА-ЯЁ]', w)]
    
    if not unique_words:
        return ""
    
    known_translations = {}
    unknown_words = []
    
    for word in unique_words:
        word_lower = word.lower()
        if word_lower in RUSSIAN_TRANSLATIONS:
            known_translations[word] = RUSSIAN_TRANSLATIONS[word_lower]
        else:
            unknown_words.append(word)
    
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
    
    translation_lines = [header]
    
    for word in unique_words:
        translation = None
        
        if word in known_translations:
            translation = known_translations[word]
        elif word in ai_translations:
            translation = ai_translations[word]
        else:
            romanized = romanize_russian_word(word)
            if romanized and romanized != word:
                translation = f"{romanized} (romanized)"
        
        if translation:
            translation_lines.append(f"<b>{word}</b> = {translation}")
    
    if len(translation_lines) <= 1:
        return ""
    
    translation_text = "\n".join(translation_lines)
    return f"<blockquote>{translation_text}</blockquote>"


def append_russian_translation_if_needed(
    response: str,
    lang: str = "id"
) -> str:
    """Append Russian translation paragraph to response if it contains Russian.
    
    Args:
        response: The bot response text
        lang: User language preference (id or en)
        
    Returns:
        Original response with Russian translation block appended if applicable
    """
    if not response or not has_russian_expressions(response):
        return response
    
    russian_words = detect_russian_expressions(response)
    if not russian_words:
        return response
    
    translation_block = format_russian_translation_block(russian_words, lang)
    if not translation_block:
        return response
    
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
    
    Args:
        response: The bot response text
        lang: User language preference (id or en)
        gemini_client: Optional GeminiClient for AI-powered translation
        
    Returns:
        Original response with Russian translation block appended if applicable
    """
    if not response or not has_russian_expressions(response):
        return response
    
    russian_words = detect_russian_expressions(response)
    if not russian_words:
        return response
    
    translation_block = await format_russian_translation_block_with_ai(
        russian_words, 
        lang, 
        gemini_client
    )
    if not translation_block:
        return response
    
    try:
        return f"{response}\n\n{translation_block}"
    except Exception as e:
        logger.error(f"Error appending Russian translation (async): {e}")
        return response


def normalize_russian_variant(word: str) -> str:
    """Normalize Russian word variant to canonical form for dictionary lookup.
    
    Args:
        word: Russian word (possibly with variants/typos)
        
    Returns:
        Normalized word for dictionary lookup
    """
    if not word:
        return ""
    
    normalized = word.lower().strip()
    
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
    
    Args:
        russian_words: List of Russian words to translate
        
    Returns:
        Prompt string for Gemini translation request
    """
    if not russian_words:
        return ""
    
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
