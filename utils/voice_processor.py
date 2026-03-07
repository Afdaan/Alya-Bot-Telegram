"""
Voice processing utilities for Alya Bot.
Handles speech-to-text (STT) and text-to-speech (TTS) using the Alya RVC voice model.
"""
import logging
import os
import asyncio
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Voice processor for handling STT and TTS operations."""
    
    def __init__(self):
        """Initialize voice processor with RVC and STT components."""
        self.temp_dir = Path("tmp")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.model_dir = Path("alya_voice")
        self.model_path = self.model_dir / "alya.pth"
        self.index_path = self.model_dir / "added_IVF777_Flat_nprobe_1_alya_v2.index"
        
        self._verify_model_files()
        self._initialize_stt()
        
        self.rvc_handler = None
        self.tts_available = self._initialize_rvc_tts()
        
        logger.info(f"✅ Voice processor initialized (STT: {self.recognizer is not None}, TTS: {self.tts_available})")

    def _verify_model_files(self):
        """Check if required RVC model files exist."""
        if not self.model_path.exists() or not self.index_path.exists():
            logger.error(f"❌ Voice model files missing in {self.model_dir}")
            raise FileNotFoundError(f"Missing RVC model files")
            
        model_size = self.model_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Voice model ready: {self.model_path.name} ({model_size:.1f}MB)")

    def _initialize_stt(self):
        """Initialize speech recognition components."""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
        except ImportError:
            logger.error("❌ speech_recognition not installed")
            self.recognizer = None
    
    def _initialize_rvc_tts(self) -> bool:
        """Initialize RVC TTS system with Alya's voice model."""
        try:
            from utils.rvc_handler import RVCHandler
            if self.model_path.exists() and self.index_path.exists():
                self.rvc_handler = RVCHandler(self.model_path, self.index_path)
        except Exception as e:
            logger.error(f"❌ RVC Handler initialization failed: {e}")
            
        base_tts_available = False
        try:
            import edge_tts
            self.edge_tts = edge_tts
            base_tts_available = True
        except ImportError:
            try:
                from gtts import gTTS
                self.gtts = gTTS
                base_tts_available = True
            except ImportError:
                logger.error("❌ No TTS engine available")
                
        return base_tts_available
    
    async def transcribe_audio(self, audio_path: str, lang: str = "id") -> Optional[Tuple[str, str]]:
        """Transcribe audio to text using Google Speech Recognition."""
        if not self.recognizer:
            return None
            
        try:
            # Convert OGG to WAV if needed
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
            
            # Try primary language first
            try:
                text = self.recognizer.recognize_google(audio_data, language=target_lang)
                return text, lang
            except sr.UnknownValueError:
                # If primary failed, try common alternatives as detection
                for alt_lang, alt_code in [("en", "en-US"), ("id", "id-ID")]:
                    if alt_lang == lang: continue
                    try:
                        text = self.recognizer.recognize_google(audio_data, language=alt_code)
                        return text, alt_lang
                    except: continue
            return None
            
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}")
            return None
        finally:
            if 'wav_path' in locals() and wav_path != audio_path:
                self._safe_remove(wav_path)

    async def _convert_to_wav(self, audio_path: str) -> str:
        """Convert audio file to WAV format."""
        if audio_path.lower().endswith('.wav'):
            return audio_path
        
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            
            wav_path = str(self.temp_dir / f"voice_{os.getpid()}_{os.urandom(4).hex()}.wav")
            audio.export(wav_path, format='wav')
            return wav_path
        except Exception as e:
            logger.error(f"❌ Error converting to WAV: {e}")
            return audio_path

    async def text_to_speech(self, text: str, lang: str = "en") -> Optional[str]:
        """Convert text to speech using RVC and base TTS."""
        if not self.tts_available:
            return None
        
        try:
            clean_text = self._clean_text_for_tts(text)
            if not clean_text: return None
            
            base_audio = await self._generate_base_tts(clean_text, lang)
            if not base_audio: return None
            
            result_audio = base_audio
            if self.rvc_handler and self.rvc_handler.is_available:
                rvc_path = str(self.temp_dir / f"rvc_{os.getpid()}_{os.urandom(4).hex()}.wav")
                wav_base = await self._convert_to_wav(base_audio)
                
                if await self.rvc_handler.convert_voice(wav_base, rvc_path):
                    result_audio = rvc_path
                    if wav_base != base_audio: self._safe_remove(wav_base)
                
            ogg_path = str(self.temp_dir / f"alya_{os.getpid()}_{os.urandom(4).hex()}.ogg")
            await self._convert_to_ogg(result_audio, ogg_path)
            
            # Cleanup
            if base_audio != result_audio: self._safe_remove(base_audio)
            if result_audio != ogg_path: self._safe_remove(result_audio)
                
            return ogg_path if os.path.exists(ogg_path) else None
        except Exception as e:
            logger.error(f"❌ TTS Error: {e}")
            return None

    def _safe_remove(self, path: str):
        """Safely remove a file."""
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")

    async def _generate_base_tts(self, text: str, lang: str) -> Optional[str]:
        """Generate base TTS audio."""
        try:
            if hasattr(self, 'edge_tts'):
                return await self._generate_edge_tts(text, lang)
            elif hasattr(self, 'gtts'):
                return await self._generate_gtts(text, lang)
            return None
        except Exception as e:
            logger.error(f"❌ Error generating base TTS: {e}")
            return None

    async def _generate_edge_tts(self, text: str, lang: str) -> Optional[str]:
        """Generate TTS using edge-tts."""
        try:
            rvc_active = self.rvc_handler and self.rvc_handler.is_available
            if rvc_active:
                voice = "ja-JP-NanamiNeural"
            else:
                voice_map = {
                    "en": "en-US-AnaNeural",
                    "id": "id-ID-GadisNeural",
                    "ru": "ru-RU-SvetlanaNeural",
                    "jp": "ja-JP-NanamiNeural"
                }
                voice = voice_map.get(lang, "en-US-AnaNeural")
            mp3_path = str(self.temp_dir / f"tts_{os.getpid()}_{os.urandom(4).hex()}.mp3")
            
            communicate = self.edge_tts.Communicate(text, voice)
            await communicate.save(mp3_path)
            return mp3_path
        except Exception:
            if hasattr(self, 'gtts'):
                return await self._generate_gtts(text, lang)
            return None

    async def _generate_gtts(self, text: str, lang: str) -> Optional[str]:
        """Generate TTS using gTTS."""
        try:
            mp3_path = str(self.temp_dir / f"tts_{os.getpid()}_{os.urandom(4).hex()}.mp3")
            tts = self.gtts(text=text, lang=lang, slow=False)
            await asyncio.to_thread(tts.save, mp3_path)
            return mp3_path
        except Exception:
            return None

    async def _convert_to_ogg(self, audio_path: str, output_path: str) -> str:
        """Convert audio file to OGG format for Telegram."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            audio.export(output_path, format='ogg', codec='libopus', parameters=['-ar', '48000', '-ac', '1'])
            return output_path
        except Exception:
            return audio_path

    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS processing."""
        # Remove formatting
        for tag in ['<b>', '</b>', '<i>', '</i>', '<code>', '</code>', '*', '_', '`']:
            text = text.replace(tag, '')
        
        # Remove emojis
        emoji_pattern = re.compile("[" "\U0001F600-\U0001F64F" "\U0001F300-\U0001F5FF" "\U0001F680-\U0001F6FF" "\U0001F1E0-\U0001F1FF" "\U00002600-\U000026FF" "\U00002700-\U000027BF" "\U0001F900-\U0001F9FF" "\U0001FA70-\U0001FAFF" "]+", flags=re.UNICODE)
        text = emoji_pattern.sub('', text)
        
        # Trim length
        text = ' '.join(text.split())[:500]
        return text.strip()
