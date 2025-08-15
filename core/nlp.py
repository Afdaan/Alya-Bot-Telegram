"""
NLP utilities for Alya Bot, including emotion detection and personality modeling.
"""
import os
import time
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from transformers import pipeline, Pipeline
from pathlib import Path

from config.settings import (
    EMOTION_CONFIDENCE_THRESHOLD,
    SLIDING_WINDOW_SIZE,
    EMOTION_MODEL_ID,
    EMOTION_MODEL_EN
)
from database.database_manager import db_manager, DatabaseManager

logger = logging.getLogger(__name__)

class NLPEngine:
    """NLP engine for emotion detection and context-aware features."""
    def __init__(self):
        self.emotion_classifier_id: Optional[Pipeline] = None
        self.emotion_classifier_en: Optional[Pipeline] = None
        self._emotion_cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = 300
        self._max_cache_size = 1000
        self._initialize_models()

    def _get_text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _is_cache_valid(self, timestamp: float) -> bool:
        return time.time() - timestamp < self._cache_ttl

    def _cleanup_cache(self, cache_dict: Dict[str, Tuple]) -> None:
        current_time = time.time()
        expired_keys = [key for key, value in cache_dict.items() if current_time - value[-1] > self._cache_ttl]
        for key in expired_keys:
            cache_dict.pop(key, None)
        if len(cache_dict) > self._max_cache_size:
            sorted_items = sorted(cache_dict.items(), key=lambda x: x[1][-1])
            for key, _ in sorted_items[:len(cache_dict) - self._max_cache_size]:
                cache_dict.pop(key, None)

    def _initialize_models(self) -> None:
        try:
            # Load Indonesian emotion classifier from config
            logger.info(f"Loading EmoSense-ID (Indonesian emotion classifier): {EMOTION_MODEL_ID}")
            self.emotion_classifier_id = pipeline(
                task="text-classification",
                model=EMOTION_MODEL_ID,
                top_k=1
            )
            logger.info("EmoSense-ID loaded.")
            # Load English/multilingual emotion classifier from config
            logger.info(f"Loading multilingual_go_emotions (English emotion classifier): {EMOTION_MODEL_EN}")
            self.emotion_classifier_en = pipeline(
                task="text-classification",
                model=EMOTION_MODEL_EN,
                top_k=3
            )
            logger.info("multilingual_go_emotions loaded.")
        except Exception as e:
            logger.error(f"Error initializing emotion models: {str(e)}")
            self.emotion_classifier_id = None
            self.emotion_classifier_en = None

    def detect_emotion(self, text: str, user_id: int = None) -> Optional[str]:
        """
        Detect emotion using the appropriate model based on user language.
        """
        # Determine user language from database
        lang = "id"
        if user_id:
            user_settings = db_manager.get_user_settings(user_id)
            lang = user_settings.get("language", "id")
        self._cleanup_cache(self._emotion_cache)
        text_hash = self._get_text_hash(f"{lang}:{text}")
        if text_hash in self._emotion_cache:
            emotion, timestamp = self._emotion_cache[text_hash]
            if self._is_cache_valid(timestamp):
                return emotion
        try:
            if lang == "id" and self.emotion_classifier_id:
                result = self.emotion_classifier_id(text)
                if result and len(result) > 0:
                    emotion = result[0]["label"] if isinstance(result[0], dict) else result[0][0]["label"]
                    self._emotion_cache[text_hash] = (emotion, time.time())
                    return emotion
            elif lang == "en" and self.emotion_classifier_en:
                result = self.emotion_classifier_en(text)
                if result and len(result[0]) > 0:
                    # Pick the highest confidence emotion above threshold
                    for candidate in result[0]:
                        if candidate["score"] >= EMOTION_CONFIDENCE_THRESHOLD:
                            emotion = candidate["label"]
                            self._emotion_cache[text_hash] = (emotion, time.time())
                            return emotion
                    # Fallback: pick top-1
                    emotion = result[0][0]["label"]
                    self._emotion_cache[text_hash] = (emotion, time.time())
                    return emotion
        except Exception as e:
            logger.error(f"Emotion detection failed: {e}")
        return None

    def get_message_context(self, text: str, user_id: int = None) -> Dict[str, Any]:
        """Analyze message for emotion only."""
        emotion = self.detect_emotion(text, user_id)
        return {
            "emotion": emotion
        }

    def suggest_mood_for_response(self, user_context: Dict[str, Any], relationship_level: int) -> str:
        """Suggest Alya's mood for response based on user context and relationship."""
        emotion = user_context.get("emotion", "neutral")
        if relationship_level >= 7:
            if emotion == "joy":
                return "dere_caring"
            elif emotion == "anger":
                return "tsundere_defensive"
            elif emotion == "sadness":
                return "tsundere_cold"
            else:
                return "waifu"
        elif relationship_level >= 3:
            if emotion == "joy":
                return "waifu"
            elif emotion == "anger":
                return "tsundere_defensive"
            elif emotion == "sadness":
                return "tsundere_cold"
            else:
                return "tsundere_cold"
        else:
            return "tsundere_cold"

    def suggest_emojis(self, message: str, mood: str, count: int = 4) -> List[str]:
        """Suggest emojis for Alya's response based on mood."""
        mood_emoji_map = {
            "dere_caring": ["✨", "🌸", "💖", "😊"],
            "tsundere_defensive": ["😳", "💫", "😠", "😒"],
            "tsundere_cold": ["😒", "💫", "😑", "😳"],
            "waifu": ["✨", "🌸", "😳", "💖"]
        }
        emojis = mood_emoji_map.get(mood, ["✨"])
        return emojis[:count]

    def get_emotion_description(self, emotion: str) -> str:
        """Get a human-readable description for an emotion label."""
        desc_map = {
            "joy": "senang",
            "anger": "marah",
            "sadness": "sedih",
            "fear": "takut",
            "surprise": "kaget",
            "neutral": "biasa aja",
            "trust": "percaya",
            "anticipation": "antisipasi",
            "disgust": "jijik"
        }
        return desc_map.get(emotion, emotion)

    def analyze_conversation_flow(self, user_id: int, current_message: str) -> Dict[str, Any]:
        """Analyze conversation flow for context-aware response."""
        return self.get_message_context(current_message, user_id)

class ContextManager:
    """Manages conversation context and memory with DB-backed sliding window and summary."""
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def get_context_window(self, user_id: int) -> List[Dict[str, Any]]:
        """Get sliding window of recent messages for user."""
        return self.db.get_conversation_history(user_id, limit=SLIDING_WINDOW_SIZE)

    def get_conversation_summaries(self, user_id: int) -> List[Dict[str, Any]]:
        """Get conversation summaries for user."""
        return self.db.get_conversation_summaries(user_id)

    def add_summary(self, user_id: int, summary: Dict[str, Any]) -> None:
        """Add a summary to the database."""
        self.db.save_conversation_summary(user_id, summary)

    def apply_sliding_window(self, user_id: int) -> None:
        """Apply sliding window and summarize old messages if needed."""
        messages = self.db.get_conversation_history(user_id, limit=SLIDING_WINDOW_SIZE+1)
        if len(messages) > SLIDING_WINDOW_SIZE:
            # Summarize the oldest messages
            old_messages = messages[:-SLIDING_WINDOW_SIZE]
            summary_text = self._summarize_messages(old_messages)
            summary = {
                "content": summary_text,
                "message_count": len(old_messages),
                "date_range_start": old_messages[0]["timestamp"],
                "date_range_end": old_messages[-1]["timestamp"]
            }
            self.add_summary(user_id, summary)
            # Remove old messages from conversation history
            self.db.delete_conversation_messages(user_id, before=old_messages[-1]["timestamp"])

    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Summarize a list of messages (simple join, can be replaced with LLM)."""
        # TODO: Integrate GeminiClient for LLM-based summary if available
        return "\n".join([msg["content"] for msg in messages])
