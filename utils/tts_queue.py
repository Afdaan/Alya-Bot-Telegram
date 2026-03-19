"""
TTS background queue worker for Alya Bot (Microservice Client).
Dispatches TTS jobs to the external Alya-TTS service via REST API.
"""
import logging
import os
import httpx
from typing import Optional
from config.settings import BOT_TOKEN

logger = logging.getLogger(__name__)

TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:5001")

async def dispatch_tts(
    bot,
    chat_id: int,
    reply_to_message_id: int,
    voice_processor,
    response_text: str,
    voice_lang: str,
    user_lang: str,
    loading_message_id: Optional[int] = None
) -> None:
    """
    Send a TTS request to the Alya-TTS microservice.
    This is fire-and-forget; it returns immediately after triggering the request.
    """
    try:
        payload = {
            "text": response_text,
            "voice_lang": voice_lang,
            "user_lang": user_lang,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
            "bot_token": BOT_TOKEN,
            "loading_message_id": loading_message_id
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"[TTS-Client] Dispatching job to {TTS_SERVICE_URL}/tts for chat {chat_id}")
            response = await client.post(
                f"{TTS_SERVICE_URL}/tts", 
                json=payload,
                timeout=5.0
            )
            
            if response.status_code in (200, 202):
                logger.info(f"[TTS-Client] TTS job accepted for chat {chat_id}")
            else:
                logger.error(f"[TTS-Client] Microservice returned error {response.status_code}: {response.text}")
                await _notify_tts_down(bot, chat_id, reply_to_message_id, user_lang)

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"[TTS-Client] Microservice connection failed: {e}")
        await _notify_tts_down(bot, chat_id, reply_to_message_id, user_lang)
    except Exception as e:
        logger.error(f"[TTS-Client] Unexpected error: {e}")

async def _notify_tts_down(bot, chat_id: int, reply_to_message_id: int, user_lang: str = None):
    """Notify the user that voice service is currently unavailable."""
    if user_lang is None:
        from config.settings import DEFAULT_LANGUAGE
        user_lang = DEFAULT_LANGUAGE
    
    notifications = {
        "en": "🎙️ <i>Gomen, the voice service is currently unavailable...</i>",
        "id": "🎙️ <i>Gomen, layanan suara sedang tidak tersedia saat ini...</i>"
    }
    
    text = notifications.get(user_lang, notifications["en"])
    
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_to_message_id=reply_to_message_id
        )
    except Exception as e:
        logger.error(f"[TTS-Client] Failed to send notification: {e}")

class TTSQueueWorker:
    """Backward-compatible stub; actual dispatch is handled by dispatch_tts()."""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        pass

    def enqueue(self, job):
        pass
