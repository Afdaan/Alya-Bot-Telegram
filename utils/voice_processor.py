"""
Lightweight Voice processor for Alya Bot (STT Only).
Handles only speech-to-text (STT). TTS is handled by the Alya-TTS microservice.
"""
import logging
import os
import asyncio
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """Lightweight voice processor for handling STT operations."""
    
    def __init__(self):
        """Initialize voice processor with only STT components."""
        self.temp_dir = Path("tmp")
        self.temp_dir.mkdir(exist_ok=True)
        self._initialize_stt()
        logger.info(f"✅ Lightweight Voice processor initialized (STT: {self.recognizer is not None})")

    def _initialize_stt(self):
        """Initialize speech recognition components."""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
        except ImportError:
            logger.error("❌ speech_recognition not installed")
            self.recognizer = None
    
    async def transcribe_audio(self, audio_path: str, lang: str = None) -> Optional[Tuple[str, str]]:
        """Transcribe audio to text using Google Speech Recognition."""
        if lang is None:
            from config.settings import DEFAULT_LANGUAGE
            lang = DEFAULT_LANGUAGE
            
        if not self.recognizer:
            return None
            
        try:
            # Convert OGG to WAV if needed (requires pydub + ffmpeg)
            wav_path = audio_path
            if audio_path.endswith('.ogg'):
                wav_path = str(self.temp_dir / f"stt_{os.getpid()}_{os.urandom(4).hex()}.wav")
                from pydub import AudioSegment
                audio = AudioSegment.from_file(audio_path, format="ogg")
                audio.export(wav_path, format="wav")
            
            import speech_recognition as sr
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
            
            # Map language codes for Google SR
            lang_map = {"en": "en-US", "id": "id-ID", "ru": "ru-RU", "jp": "ja-JP"}
            target_lang = lang_map.get(lang, "id-ID")
            
            # Simple wrapper to run blocking recognize_google in thread
            text = await asyncio.to_thread(self.recognizer.recognize_google, audio_data, language=target_lang)
            return text, lang
            
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}")
            return None
        finally:
            if 'wav_path' in locals() and wav_path != audio_path:
                self._safe_remove(wav_path)

    def _safe_remove(self, path: str):
        """Safely remove a file."""
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
