"""
Voice processing utilities for Alya Bot.
Handles speech-to-text (STT) and text-to-speech (TTS) using the Alya RVC voice model.
"""
import logging
import os
from pathlib import Path
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """
    Voice processor for handling STT and TTS operations.
    Uses Google Speech Recognition for STT and RVC/Alya model for TTS.
    """
    
    def __init__(self):
        """Initialize voice processor with local RVC model."""
        # Setup temp directory in project root (Docker-friendly)
        self.temp_dir = Path("tmp")
        self.temp_dir.mkdir(exist_ok=True)
        logger.info(f"📁 Temp directory: {self.temp_dir.absolute()}")
        
        # Voice model paths
        self.model_dir = Path("alya_voice")
        self.model_path = self.model_dir / "alya.pth"
        self.index_path = self.model_dir / "added_IVF777_Flat_nprobe_1_alya_v2.index"
        
        # Verify model files exist
        if not self.model_path.exists():
            logger.error(f"❌ Voice model not found at {self.model_path}")
            raise FileNotFoundError(f"Voice model not found: {self.model_path}")
        
        if not self.index_path.exists():
            logger.error(f"❌ Voice index not found at {self.index_path}")
            raise FileNotFoundError(f"Voice index not found: {self.index_path}")
        
        logger.info(f"✅ Found voice model: {self.model_path}")
        logger.info(f"✅ Found voice index: {self.index_path}")
        
        # Initialize STT (Speech Recognition)
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            logger.info("✅ Speech recognition initialized")
        except ImportError:
            logger.error("❌ speech_recognition not installed. Install with: pip install SpeechRecognition")
            self.recognizer = None
        
        # Initialize RVC TTS
        self.rvc_handler = None
        self.tts_available = self._initialize_rvc_tts()
        
        logger.info(f"✅ Voice processor initialized (STT: {self.recognizer is not None}, TTS: {self.tts_available}, RVC: {self.rvc_handler is not None})")
    
    def _initialize_rvc_tts(self) -> bool:
        """Initialize RVC TTS system with Alya's voice model."""
        try:
            # Try to initialize RVCHandler
            try:
                from utils.rvc_handler import RVCHandler
                if self.model_path.exists() and self.index_path.exists():
                    self.rvc_handler = RVCHandler(self.model_path, self.index_path)
                    if self.rvc_handler.is_available:
                        logger.info("✅ RVCHandler initialized successfully")
                    else:
                        self.rvc_handler = None
            except ImportError as e:
                logger.warning(f"Could not import RVCHandler: {e}")
            
            # Fallback to edge-tts for base audio
            try:
                import edge_tts
                self.edge_tts = edge_tts
                logger.info("✅ Edge-TTS initialized (base for RVC)")
                return True
            except ImportError:
                logger.warning("⚠️ edge-tts not installed. Install with: pip install edge-tts")
                
                # Final fallback to gTTS
                try:
                    from gtts import gTTS
                    self.gtts = gTTS
                    logger.info("✅ Google TTS initialized (fallback)")
                    return True
                except ImportError:
                    logger.error("❌ No TTS engine available")
                    return False
                    
        except ImportError as e:
            logger.error(f"❌ Failed to initialize TTS: {e}")
            return False
    
    async def transcribe_audio(self, audio_path: str, language: str = "en") -> Optional[str]:
        """
        Transcribe audio file to text using Google Speech Recognition.
        
        Args:
            audio_path: Path to audio file (OGG, WAV, etc.)
            language: Language code (en, id, ru, ja)
        
        Returns:
            Transcribed text or None if failed
        """
        if not self.recognizer:
            logger.error("❌ Speech recognizer not available")
            return None
        
        try:
            # Convert OGG to WAV if needed
            wav_path = await self._convert_to_wav(audio_path)
            
            # Import here to avoid loading if not needed
            import speech_recognition as sr
            
            # Load audio file
            with sr.AudioFile(wav_path) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
            
            # Map language codes
            lang_map = {
                "en": "en-US",
                "id": "id-ID",
                "ru": "ru-RU",
                "ja": "ja-JP"
            }
            google_lang = lang_map.get(language, "en-US")
            
            # Transcribe using Google Speech Recognition
            text = await asyncio.to_thread(
                self.recognizer.recognize_google,
                audio_data,
                language=google_lang
            )
            
            logger.info(f"✅ Transcription successful: {text[:50]}...")
            
            # Clean up temporary WAV file if it was converted
            if wav_path != audio_path:
                try:
                    os.unlink(wav_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp WAV file: {e}")
            
            return text
        
        except sr.UnknownValueError:
            logger.warning("⚠️ Speech recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"❌ Could not request results from speech recognition service: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error transcribing audio: {e}", exc_info=True)
            return None
    
    async def _convert_to_wav(self, audio_path: str) -> str:
        """
        Convert audio file to WAV format if needed.
        Uses project tmp directory instead of system /tmp.
        
        Args:
            audio_path: Path to input audio file
        
        Returns:
            Path to WAV file
        """
        # Check if already WAV
        if audio_path.lower().endswith('.wav'):
            return audio_path
        
        try:
            from pydub import AudioSegment
            
            # Load audio file
            audio = AudioSegment.from_file(audio_path)
            
            # Create WAV file in project tmp directory
            wav_filename = f"voice_{os.getpid()}_{os.urandom(4).hex()}.wav"
            wav_path = str(self.temp_dir / wav_filename)
            
            # Export as WAV
            audio.export(wav_path, format='wav')
            
            logger.info(f"✅ Converted {audio_path} to WAV: {wav_path}")
            return wav_path
        
        except ImportError:
            logger.error("❌ pydub not installed. Install with: pip install pydub")
            logger.error("❌ Also install ffmpeg: https://ffmpeg.org/download.html")
            return audio_path
        except Exception as e:
            logger.error(f"❌ Error converting audio to WAV: {e}")
            return audio_path
    
    async def text_to_speech(self, text: str, lang: str = "en") -> Optional[str]:
        """
        Convert text to speech using Alya's RVC voice model.
        
        Process:
        1. Generate base TTS audio (edge-tts or gTTS)
        2. Apply RVC voice conversion using alya.pth model
        3. Return converted audio in OGG format
        
        Args:
            text: Text to convert to speech
            lang: Language code (en, id, ru, ja)
        
        Returns:
            Path to generated audio file (OGG format) or None if failed
        """
        if not self.tts_available:
            logger.error("❌ TTS not available")
            return None
        
        try:
            # Clean text for TTS
            clean_text = self._clean_text_for_tts(text)
            
            if not clean_text:
                logger.warning("⚠️ No text to convert to speech")
                return None
            
            # Step 1: Generate base TTS audio
            base_audio_path = await self._generate_base_tts(clean_text, lang)
            
            if not base_audio_path:
                logger.error("❌ Failed to generate base TTS")
                return None
            
            # Step 2: Apply RVC voice conversion (if available)
            converted_audio_path = base_audio_path
            
            if self.rvc_handler and self.rvc_handler.is_available:
                try:
                    # Create path for converted audio
                    rvc_filename = f"rvc_{os.getpid()}_{os.urandom(4).hex()}.wav"
                    rvc_path = str(self.temp_dir / rvc_filename)
                    
                    # Convert base TTS to WAV first (RVC expects WAV)
                    wav_base_path = await self._convert_to_wav(base_audio_path)
                    
                    # Run RVC inference
                    success = await self.rvc_handler.convert_voice(
                        wav_base_path,
                        rvc_path
                    )
                    
                    if success:
                        logger.info(f"✅ RVC Voice conversion successful")
                        converted_audio_path = rvc_path
                        
                        # Cleanup intermediate WAV if it was created
                        if wav_base_path != base_audio_path:
                            try:
                                os.unlink(wav_base_path)
                            except:
                                pass
                    else:
                        logger.warning("⚠️ RVC conversion failed, using base TTS")
                        
                except Exception as e:
                    logger.error(f"❌ Error during RVC conversion: {e}")
            
            # Step 3: Convert to OGG for Telegram
            ogg_path = await self._convert_to_ogg(converted_audio_path)
            
            # Clean up intermediate files
            if base_audio_path != ogg_path and base_audio_path != converted_audio_path:
                try:
                    os.unlink(base_audio_path)
                except Exception as e:
                    logger.warning(f"Failed to delete base audio file: {e}")
            
            if converted_audio_path != ogg_path and converted_audio_path != base_audio_path:
                try:
                    os.unlink(converted_audio_path)
                except Exception as e:
                    logger.warning(f"Failed to delete converted audio file: {e}")
            
            logger.info(f"✅ TTS generated: {ogg_path}")
            return ogg_path
        
        except Exception as e:
            logger.error(f"❌ Error generating TTS: {e}", exc_info=True)
            return None
    
    async def _generate_base_tts(self, text: str, lang: str) -> Optional[str]:
        """
        Generate base TTS audio using edge-tts or gTTS.
        
        Args:
            text: Text to convert
            lang: Language code
        
        Returns:
            Path to generated audio file (MP3)
        """
        try:
            # Try edge-tts first (better quality)
            if hasattr(self, 'edge_tts'):
                return await self._generate_edge_tts(text, lang)
            
            # Fallback to gTTS
            elif hasattr(self, 'gtts'):
                return await self._generate_gtts(text, lang)
            
            else:
                logger.error("❌ No TTS engine available")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating base TTS: {e}")
            return None
    
    async def _generate_edge_tts(self, text: str, lang: str) -> Optional[str]:
        """Generate TTS using edge-tts (Microsoft Edge TTS)."""
        try:
            # Map language codes to edge-tts voices (younger/anime-style)
            voice_map = {
                "en": "en-US-AnaNeural",    # Young female voice (matches anime character better)
                "id": "id-ID-GadisNeural",  # Indonesian female (standard)
                "ru": "ru-RU-SvetlanaNeural", # Russian female (standard)
                "ja": "ja-JP-NanamiNeural"  # Japanese female (anime-style)
            }
            voice = voice_map.get(lang, "en-US-AnaNeural")
            
            # Create MP3 file in project tmp directory
            mp3_filename = f"tts_{os.getpid()}_{os.urandom(4).hex()}.mp3"
            mp3_path = str(self.temp_dir / mp3_filename)
            
            # Generate TTS
            communicate = self.edge_tts.Communicate(text, voice)
            await communicate.save(mp3_path)
            
            logger.info(f"✅ Edge-TTS generated: {mp3_path}")
            return mp3_path
            
        except Exception as e:
            logger.error(f"❌ Edge-TTS failed: {e}")
            # Fallback to gTTS if available
            if hasattr(self, 'gtts'):
                return await self._generate_gtts(text, lang)
            return None
    
    async def _generate_gtts(self, text: str, lang: str) -> Optional[str]:
        """Generate TTS using gTTS (Google TTS)."""
        try:
            # Map language codes
            lang_map = {
                "en": "en",
                "id": "id",
                "ru": "ru",
                "ja": "ja"
            }
            tts_lang = lang_map.get(lang, "en")
            
            # Generate TTS
            tts = self.gtts(text=text, lang=tts_lang, slow=False)
            
            # Create MP3 file in project tmp directory
            mp3_filename = f"tts_{os.getpid()}_{os.urandom(4).hex()}.mp3"
            mp3_path = str(self.temp_dir / mp3_filename)
            
            await asyncio.to_thread(tts.save, mp3_path)
            
            logger.info(f"✅ gTTS generated: {mp3_path}")
            return mp3_path
            
        except Exception as e:
            logger.error(f"❌ gTTS failed: {e}")
            return None
    
    async def _convert_to_ogg(self, audio_path: str) -> str:
        """
        Convert audio file to OGG format for Telegram.
        Uses project tmp directory.
        
        Args:
            audio_path: Path to input audio file
        
        Returns:
            Path to OGG file
        """
        try:
            from pydub import AudioSegment
            
            # Load audio file
            audio = AudioSegment.from_file(audio_path)
            
            # Create OGG file in project tmp directory
            ogg_filename = f"voice_{os.getpid()}_{os.urandom(4).hex()}.ogg"
            ogg_path = str(self.temp_dir / ogg_filename)
            
            # Export as OGG with opus codec
            audio.export(
                ogg_path,
                format='ogg',
                codec='libopus',
                parameters=['-ar', '48000', '-ac', '1']  # 48kHz mono
            )
            
            logger.info(f"✅ Converted to OGG: {ogg_path}")
            return ogg_path
        
        except ImportError:
            logger.warning("⚠️ pydub not installed, returning original file")
            return audio_path
        except Exception as e:
            logger.error(f"❌ Error converting to OGG: {e}")
            return audio_path
    
    def _clean_text_for_tts(self, text: str) -> str:
        """
        Clean text for TTS processing.
        
        Args:
            text: Input text
        
        Returns:
            Cleaned text suitable for TTS
        """
        # Remove markdown and HTML
        text = text.replace('*', '').replace('_', '').replace('`', '')
        text = text.replace('<b>', '').replace('</b>', '')
        text = text.replace('<i>', '').replace('</i>', '')
        text = text.replace('<code>', '').replace('</code>', '')
        
        # Remove emojis (they don't sound good in TTS)
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Limit length (TTS works better with shorter text)
        max_length = 500
        if len(text) > max_length:
            # Try to cut at sentence boundary
            sentences = text[:max_length].split('.')
            if len(sentences) > 1:
                text = '.'.join(sentences[:-1]) + '.'
            else:
                text = text[:max_length] + '...'
        
        return text.strip()
