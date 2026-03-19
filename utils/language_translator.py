"""
Language translation utilities for voice responses.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LanguageTranslator:
    """Translator for converting responses to different languages."""

    def extract_dialogue(self, text: str) -> str:
        """Extract dialogue from text, removing roleplay action markers."""
        text = re.sub(r'[*_]{1,3}.*?[*_]{1,3}', '', text).strip()

        dialogue_pattern = re.compile(r'["\'""\u300c](.*?)["\'""\u300d]', re.DOTALL)
        quotes = dialogue_pattern.findall(text)

        if quotes:
            cleaned_base = dialogue_pattern.sub(' ', text).strip()
            if cleaned_base and len(cleaned_base.split()) <= 4:
                return f"{cleaned_base} {' '.join(quotes)}".strip()
            return " ".join(q.strip() for q in quotes if q.strip())

        return text

    async def translate_text(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Translate text using Google Translate API."""
        if not text or source_lang == target_lang:
            return text

        try:
            import requests
            import urllib.parse

            # Google Translate uses 'ja' for Japanese, not 'jp'
            lang_map = {"jp": "ja"}
            sl = lang_map.get(source_lang, source_lang)
            tl = lang_map.get(target_lang, target_lang)

            url = (
                f"https://translate.googleapis.com/translate_a/single"
                f"?client=gtx&sl={sl}&tl={tl}&dt=t"
                f"&q={urllib.parse.quote(text)}"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and data[0]:
                    return "".join(s[0] for s in data[0] if s[0])
        except Exception as e:
            logger.warning(f"⚠️ Translation error: {e}")

        return text


_translator: Optional[LanguageTranslator] = None


def get_translator() -> LanguageTranslator:
    """Get or create global translator instance."""
    global _translator
    if _translator is None:
        _translator = LanguageTranslator()
    return _translator


async def translate_response_for_voice(text: str, source_lang: str, voice_lang: str) -> str:
    """Extract dialogue and translate for TTS if needed."""
    translator = get_translator()
    extracted = translator.extract_dialogue(text)

    if source_lang != voice_lang:
        translated = await translator.translate_text(extracted, source_lang, voice_lang)
        return translated if translated else extracted

    return extracted
