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
    EMOTION_MODEL_EN,
    ZERO_SHOT_MODEL,
    ZERO_SHOT_CONFIDENCE_THRESHOLD,
    DEFAULT_LANGUAGE
)
from database.database_manager import db_manager, DatabaseManager

logger = logging.getLogger(__name__)

class NLPEngine:
    """NLP engine for emotion detection and context-aware features."""
    def __init__(self):
        self.emotion_classifier_id: Optional[Pipeline] = None
        self.emotion_classifier_en: Optional[Pipeline] = None
        self.zero_shot_classifier: Optional[Pipeline] = None
        self._emotion_cache: Dict[str, Tuple[str, float]] = {}
        self._intent_cache: Dict[str, Tuple[str, float]] = {}
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
            # Load zero-shot classification model for intent detection
            logger.info(f"Loading zero-shot classifier: {ZERO_SHOT_MODEL}")
            self.zero_shot_classifier = pipeline(
                task="zero-shot-classification",
                model=ZERO_SHOT_MODEL
            )
            logger.info("Zero-shot classifier loaded.")
        except Exception as e:
            logger.error(f"Error initializing emotion models: {str(e)}")
            self.emotion_classifier_id = None
            self.emotion_classifier_en = None
            self.zero_shot_classifier = None

    def detect_emotion(self, text: str, user_id: int = None) -> Optional[str]:
        """
        Detect emotion using the appropriate model based on user language.
        
        Args:
            text: Input text to analyze
            user_id: User ID for language detection
            
        Returns:
            Detected emotion label or None if detection fails, defaults to DEFAULT_LANGUAGE
        """
        # Determine user language from database
        lang = DEFAULT_LANGUAGE
        if user_id:
            user_settings = db_manager.get_user_settings(user_id)
            lang = user_settings.get("language", DEFAULT_LANGUAGE)
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
        """Analyze message for emotion, intent, and relationship signals.
        
        Detects:
        - Emotion: User's emotional state (joy, anger, sadness, etc.)
        - Intent: What the user is trying to do (gratitude, insult, greeting, etc.)
        - Relationship signals: Positive/negative behaviors affecting affection
        
        Args:
            text: User's message text
            user_id: User ID for language detection
            
        Returns:
            Dict with emotion, intent, relationship_signals, and directed_at_alya flag
        """
        # Periodic cache cleanup
        self._cleanup_cache(self._emotion_cache)
        self._cleanup_cache(self._intent_cache)
        
        emotion = self.detect_emotion(text, user_id)
        intent = self._detect_intent(text, user_id)
        relationship_signals = self._detect_relationship_signals(text, emotion, intent)
        directed_at_alya = self._is_directed_at_alya(text)
        
        return {
            "emotion": emotion,
            "intent": intent,
            "relationship_signals": relationship_signals,
            "directed_at_alya": directed_at_alya
        }
    
    def _detect_intent(self, text: str, user_id: int = None) -> str:
        """Detect user's intent from message text using zero-shot classification.
        
        Uses zero-shot classification for semantic intent detection with multilingual support
        (Indonesian & English):
        - gratitude: thanks, appreciation
        - apology: sorry, apologetic
        - greeting: hello, casual opening
        - compliment: praise, positive feedback
        - insult: derogatory, negative
        - romantic_interest: romantic signals
        - affection: emotional attachment
        - question: information seeking
        - toxic_behavior: harmful, bullying
        - rudeness: impolite language
        - asking_about_alya: questions about Alya
        - remembering_details: referencing past conversations
        - meaningful_conversation: substantive discussion
        - normal: default/neutral
        
        Args:
            text: User's message text
            user_id: User ID for caching
            
        Returns:
            str: Detected intent category
        """
        if not self.zero_shot_classifier:
            logger.warning("Zero-shot classifier not loaded, defaulting to 'normal'")
            return "normal"
        
        # Check cache first
        text_hash = self._get_text_hash(f"intent:{text}")
        if text_hash in self._intent_cache:
            intent, timestamp = self._intent_cache[text_hash]
            if self._is_cache_valid(timestamp):
                return intent
        
        # Get user language for bilingual label selection
        lang = DEFAULT_LANGUAGE
        if user_id:
            user_settings = db_manager.get_user_settings(user_id)
            lang = user_settings.get("language", DEFAULT_LANGUAGE)
        
        # Define candidate intent labels (bilingual support)
        # Labels are crafted to be semantically distinct for better zero-shot classification
        if lang == "id":
            candidate_labels = [
                "ucapan terima kasih dan rasa syukur",
                "permintaan maaf dan penyesalan",
                "salam sapaan dan pembukaan percakapan",
                "memuji keindahan atau kualitas baik",
                "menghina atau merendahkan dengan kata buruk",
                "ungkapan cinta dan minat romantis",
                "ungkapan sayang dan perhatian kasih",
                "pertanyaan atau meminta informasi penjelasan",
                "ancaman berbahaya atau perilaku jahat",
                "kata-kata kasar tidak sopan atau menyerang",
                "bertanya spesifik tentang bot atau dirinya",
                "mereferensikan atau mengingat percakapan sebelumnya",
                "diskusi mendalam penting atau bermakna",
                "obrolan santai tanpa maksud khusus"
            ]
        else:  # English
            candidate_labels = [
                "thanking expressing gratitude and appreciation",
                "apologizing saying sorry and feeling regret",
                "greeting saying hello and starting chat",
                "praising complimenting beauty and quality",
                "insulting name calling and putting down",
                "declaring love expressing romantic feelings",
                "showing care affection and tenderness",
                "questioning asking seeking information",
                "threatening dangerous behavior and harm",
                "cursing being rude impolite language",
                "asking about the bot personal questions",
                "referencing remembering previous chats",
                "discussing important meaningful topics",
                "chatting casual neutral normal talk"
            ]
        
        try:
            # Use zero-shot classification
            result = self.zero_shot_classifier(
                text,
                candidate_labels,
                multi_label=False
            )
            
            # Check if top result meets confidence threshold
            if result and result.get("scores") and result["scores"][0] >= ZERO_SHOT_CONFIDENCE_THRESHOLD:
                # Map classification result back to intent
                top_label = result["labels"][0]
                intent = self._map_label_to_intent(top_label, lang)
                self._intent_cache[text_hash] = (intent, time.time())
                return intent
            else:
                # Fallback if confidence is too low
                logger.debug(f"Intent confidence too low for: {text}")
                self._intent_cache[text_hash] = ("normal", time.time())
                return "normal"
                
        except Exception as e:
            logger.error(f"Error in zero-shot intent detection: {e}")
            return "normal"
    
    def _map_label_to_intent(self, label: str, lang: str = "en") -> str:
        """Map zero-shot classification label to intent category (bilingual).
        
        Args:
            label: Zero-shot classification label (Indonesian or English)
            lang: Language of the label ("id" or "en")
            
        Returns:
            str: Intent category
        """
        label_lower = label.lower()
        
        # Gratitude patterns (Indonesian & English)
        if any(word in label_lower for word in ["gratitude", "thanks", "terima kasih", "apresiasi", "appreciation", "syukur"]):
            return "gratitude"
        
        # Apology patterns
        if any(word in label_lower for word in ["apology", "sorry", "maaf", "penyesalan", "regret", "permintaan maaf"]):
            return "apology"
        
        # Greeting patterns
        if any(word in label_lower for word in ["greeting", "hello", "sapaan", "pembukaan", "friendly", "salam", "opening"]):
            return "greeting"
        
        # Compliment patterns (matching "memuji", "puja", "keindahan", "compliment", "praise", "praising", "beautiful", "quality")
        if any(word in label_lower for word in ["compliment", "praise", "pujian", "positif", "positive", "muji", "keindahan", "beautiful", "quality", "praising"]):
            return "compliment"
        
        # Insult patterns (matching "menghina", "merendahkan", "insult", "name calling", "putting down")
        if any(word in label_lower for word in ["insult", "derogatory", "hinaan", "merendahkan", "name calling", "putting down"]):
            return "insult"
        
        # Romantic interest / Love patterns (matching "declaring", "love", "cinta", "romantic", "minat romantis")
        if any(word in label_lower for word in ["romantic", "love", "cinta", "minat romantis", "declaring", "expressing love"]):
            return "romantic_interest"
        
        # Affection patterns (matching "sayang", "perhatian", "kasih", "affection", "care", "tenderness", "emotional attachment")
        if any(word in label_lower for word in ["affection", "attachment", "kasih", "sayang", "keterikatan", "emotional", "care", "tenderness", "perhatian"]):
            return "affection"
        
        # Question patterns (matching "tanya", "informasi", "pertanyaan", "question", "asking", "seeking")
        if any(word in label_lower for word in ["question", "asking", "pertanyaan", "tanya", "seeking", "informasi", "penjelasan"]):
            return "question"
        
        # Toxic behavior patterns (matching "ancam", "bahaya", "jahat", "threat", "dangerous", "toxic")
        if any(word in label_lower for word in ["toxic", "threatening", "threat", "dangerous", "ancam", "bahaya", "jahat", "harmful"]):
            return "toxic_behavior"
        
        # Rudeness patterns (matching "kasar", "sopan", "menyerang", "rude", "impolite", "crude")
        if any(word in label_lower for word in ["rude", "impolite", "crude", "kasar", "tidak sopan", "menyerang", "cursing"]):
            return "rudeness"
        
        # Asking about bot/person patterns (matching "bot", "spesifik", "personal")
        if any(word in label_lower for word in ["bot", "person", "penanya", "about the", "spesifik", "personal"]):
            return "asking_about_alya"
        
        # Remembering patterns (matching "referensikan", "mengingat", "percakapan", "remembering", "past", "previous", "chats")
        if any(word in label_lower for word in ["remembering", "past", "mengingat", "masa lalu", "referencing", "percakapan", "referensikan", "previous", "chats"]):
            return "remembering_details"
        
        # Meaningful conversation patterns (matching "diskusi", "mendalam", "penting", "bermakna", "meaningful", "important", "substantive")
        if any(word in label_lower for word in ["meaningful", "substantive", "bermakna", "substansial", "discussion", "diskusi", "mendalam", "penting", "important"]):
            return "meaningful_conversation"
        
        # Default to normal
        return "normal"
    
    def _detect_relationship_signals(self, text: str, emotion: str, intent: str) -> Dict[str, float]:
        """Detect relationship signals (positive/negative behaviors).
        
        Returns a dict with:
        - friendliness: 0 = hostile, 1 = very friendly
        - romantic_interest: 0 = none, 1 = strong romantic signal
        - conflict: 0 = none, 1 = conflict present
        
        Args:
            text: User's message
            emotion: Detected emotion
            intent: Detected intent
            
        Returns:
            Dict with relationship signal scores
        """
        signals = {
            "friendliness": 0,
            "romantic_interest": 0,
            "conflict": 0
        }
        
        text_lower = text.lower()
        
        # Friendliness signals
        if intent in ["gratitude", "compliment", "greeting", "affection"]:
            signals["friendliness"] = 1
        elif emotion in ["joy", "happiness", "love"]:
            signals["friendliness"] = 0.8
        elif intent in ["asking_about_alya", "meaningful_conversation", "remembering_details"]:
            signals["friendliness"] = 0.7
        elif emotion in ["sadness", "fear", "worry"]:
            # Showing vulnerability builds connection
            signals["friendliness"] = 0.5
        elif intent in ["insult", "rudeness", "toxic_behavior"]:
            signals["conflict"] = 1
        
        # Romantic interest signals
        if intent == "affection":
            signals["romantic_interest"] = 1
        elif intent == "romantic_interest":
            signals["romantic_interest"] = 0.8
        elif any(word in text_lower for word in ["jadi pacarnya", "pacaran", "istri", "suami", "marry"]):
            signals["romantic_interest"] = 0.9
        elif emotion == "love":
            signals["romantic_interest"] = 0.6
        
        # Conflict signals
        if emotion in ["anger", "frustration", "disgust"]:
            signals["conflict"] = 0.7
        elif intent in ["insult", "rudeness", "toxic_behavior"]:
            signals["conflict"] = 1
        elif intent == "apology":
            signals["conflict"] = -0.5  # Resolve conflict
        
        return signals
    
    def _is_directed_at_alya(self, text: str) -> bool:
        """Check if message is directed at Alya specifically.
        
        Args:
            text: User's message
            
        Returns:
            bool: True if message is directed at Alya
        """
        text_lower = text.lower()
        
        # Check for direct address patterns
        alya_patterns = [
            "alya", "kamu", "lu", "elu", "lo", "mu", "kau",
            "you", "ur", "yourself", "yourself"
        ]
        
        # If message starts with or contains direct address, likely directed at Alya
        for pattern in alya_patterns:
            if text_lower.startswith(pattern) or f" {pattern} " in text_lower:
                return True
        
        # If message is a question or response in conversation context, likely directed at Alya
        if text_lower.endswith("?") or any(word in text_lower for word in ["apa", "siapa", "bagaimana"]):
            return True
        
        # Default to True if not clear (safer assumption)
        return True

    def suggest_mood_for_response(self, user_context: Dict[str, Any], relationship_level: int) -> str:
        """Suggest Alya's mood for response based on user context and relationship.
        
        Uses a scalable mood configuration map for easy maintenance and extensibility.
        
        Relationship levels (0-4):
        0: Stranger - Full tsundere cold mode
        1: Acquaintance - Mostly tsundere with hints of warmth
        2: Friend - Mix of tsundere and warm waifu
        3: Close friend - Waifu mode activated, minimal tsundere
        4: Soulmate - Dere mode fully unlocked, most caring
        
        Args:
            user_context: Dictionary containing detected user emotion
            relationship_level: Current relationship level (0-4)
            
        Returns:
            Mood string to use for response generation
        """
        emotion = user_context.get("emotion", "neutral")
        
        # Scalable mood configuration map - easy to add more levels or emotions
        # Format: {level: {emotion: mood}}
        mood_map = {
            4: {  # Soulmate - Dere mode unlocked, most caring and open
                "joy": "dere_caring",
                "happiness": "dere_caring",
                "love": "dere_caring",
                "anger": "tsundere_defensive",  # Still protective when angry
                "sadness": "dere_caring",
                "fear": "dere_caring",
                "surprise": "waifu",
                "default": "waifu"
            },
            3: {  # Close friend - Waifu mode primary, comfortable and warm
                "joy": "waifu",
                "happiness": "waifu",
                "love": "waifu",
                "anger": "tsundere_defensive",
                "sadness": "waifu",  # Shows caring side
                "fear": "waifu",
                "surprise": "waifu",
                "default": "waifu"
            },
            2: {  # Friend - Warm waifu with occasional tsundere moments
                "joy": "waifu",
                "happiness": "waifu",
                "love": "tsundere_defensive",  # Still defensive about love
                "anger": "tsundere_defensive",
                "sadness": "waifu",  # Caring for friends' sadness
                "fear": "waifu",
                "surprise": "tsundere_defensive",
                "default": "waifu"  # Default to warm for friends
            },
            1: {  # Acquaintance - Mostly defensive with hints of warmth
                "joy": "tsundere_defensive",
                "happiness": "tsundere_defensive",
                "love": "tsundere_defensive",
                "anger": "tsundere_defensive",
                "sadness": "tsundere_defensive",  # Slightly concerned but guarded
                "fear": "tsundere_cold",
                "surprise": "tsundere_defensive",
                "default": "tsundere_cold"
            },
            0: {  # Stranger - Full tsundere cold mode, maximum distance
                "joy": "tsundere_cold",
                "happiness": "tsundere_cold",
                "love": "tsundere_cold",
                "anger": "tsundere_defensive",  # Only defensive when provoked
                "sadness": "tsundere_cold",
                "fear": "tsundere_cold",
                "surprise": "tsundere_cold",
                "default": "tsundere_cold"
            }
        }
        
        # Get mood configuration for current level, fallback to level 0 if not found
        level_moods = mood_map.get(relationship_level, mood_map[0])
        
        # Get mood for current emotion, fallback to default mood for this level
        mood = level_moods.get(emotion, level_moods["default"])
        
        return mood

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
                "date_range_start": old_messages[0].get("created_at") or old_messages[0].get("timestamp"),
                "date_range_end": old_messages[-1].get("created_at") or old_messages[-1].get("timestamp")
            }
            self.add_summary(user_id, summary)
            # Remove old messages from conversation history
            before_timestamp = old_messages[-1].get("created_at") or old_messages[-1].get("timestamp")
            if before_timestamp:
                self.db.delete_conversation_messages(user_id, before=before_timestamp)

    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Summarize a list of messages (simple join, can be replaced with LLM)."""
        # TODO: Integrate GeminiClient for LLM-based summary if available
        return "\n".join([msg["content"] for msg in messages])
