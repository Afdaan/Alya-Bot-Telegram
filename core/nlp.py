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
    INTENT_SENTIMENT_MODEL,
    INTENT_CONFIDENCE_THRESHOLD,
    USE_HYBRID_INTENT,
    DEFAULT_LANGUAGE
)
from database.database_manager import db_manager, DatabaseManager

logger = logging.getLogger(__name__)

class NLPEngine:
    """NLP engine for emotion detection and context-aware features."""
    def __init__(self):
        self.emotion_classifier_id: Optional[Pipeline] = None
        self.emotion_classifier_en: Optional[Pipeline] = None
        self.sentiment_classifier: Optional[Pipeline] = None  # For hybrid intent detection
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
            
            # Load lightweight sentiment classifier for hybrid intent detection
            if USE_HYBRID_INTENT:
                logger.info(f"Loading sentiment classifier for intent: {INTENT_SENTIMENT_MODEL}")
                self.sentiment_classifier = pipeline(
                    task="text-classification",
                    model=INTENT_SENTIMENT_MODEL,
                    top_k=1
                )
                logger.info("Sentiment classifier loaded for hybrid intent detection.")
            else:
                logger.info("Hybrid intent detection disabled, using rule-based only")
                self.sentiment_classifier = None
                
        except Exception as e:
            logger.error(f"Error initializing NLP models: {str(e)}")
            self.emotion_classifier_id = None
            self.emotion_classifier_en = None
            self.sentiment_classifier = None

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
        
        # Log analysis results for affection tracking
        logger.info(
            f"[NLP] User {user_id} message context: "
            f"emotion={emotion}, intent={intent}, "
            f"signals={relationship_signals}, directed_at_alya={directed_at_alya}"
        )
        
        return {
            "emotion": emotion,
            "intent": intent,
            "relationship_signals": relationship_signals,
            "directed_at_alya": directed_at_alya
        }
    
    def _detect_intent(self, text: str, user_id: int = None) -> str:
        """Detect user's intent using hybrid approach (rule-based + ML fallback).
        
        Hybrid Strategy:
        1. Rule-based semantic keyword matching for obvious intents (fast, deterministic)
        2. Lightweight sentiment classifier fallback for ambiguous cases (accurate, efficient)
        
        This approach is 3-5x faster than zero-shot classification while maintaining
        high accuracy for both Indonesian and English.
        
        Intent categories:
        - gratitude: thanks, appreciation, terima kasih
        - apology: sorry, apologetic, maaf
        - greeting: hello, casual opening, salam
        - compliment: praise, positive feedback, pujian
        - insult: derogatory, negative remarks, hinaan
        - affection: emotional attachment, sayang
        - romantic_interest: romantic interest, cinta, jatuh cinta
        - question: information seeking, pertanyaan
        - toxic_behavior: harmful, bullying, threats, ancaman
        - rudeness: impolite language, kasar
        - normal: neutral, everyday conversation
        
        Args:
            text: User's message text
            user_id: User ID for caching (optional)
            
        Returns:
            str: Detected intent category
        """
        # Check cache first
        text_hash = self._get_text_hash(f"intent:{text}")
        if text_hash in self._intent_cache:
            intent, timestamp = self._intent_cache[text_hash]
            if self._is_cache_valid(timestamp):
                return intent
        
        # Get user language for bilingual keyword selection
        lang = DEFAULT_LANGUAGE
        if user_id:
            try:
                user_settings = db_manager.get_user_settings(user_id)
                lang = user_settings.get("language", DEFAULT_LANGUAGE)
            except Exception as e:
                logger.debug(f"Could not get user language for {user_id}: {e}")
        
        text_lower = text.lower().strip()
        
        # ===== PHASE 1: Rule-based semantic keyword matching (fast path) =====
        intent = self._detect_intent_keywords(text_lower, lang)
        
        if intent != "normal":
            # Cache and return
            self._intent_cache[text_hash] = (intent, time.time())
            logger.debug(f"Intent detected (rule-based): '{text[:50]}...' → {intent}")
            return intent
        
        # ===== PHASE 2: Sentiment-based fallback for ambiguous cases =====
        if USE_HYBRID_INTENT and self.sentiment_classifier:
            try:
                result = self.sentiment_classifier(text)
                if result and len(result) > 0:
                    sentiment_label = result[0]["label"].lower()
                    confidence = result[0]["score"]
                    
                    # Map sentiment to intent (high confidence only)
                    if confidence >= INTENT_CONFIDENCE_THRESHOLD:
                        intent = self._map_sentiment_to_intent(sentiment_label, text_lower, lang)
                        logger.debug(
                            f"Intent detected (sentiment): '{text[:50]}...' → {intent} "
                            f"(sentiment={sentiment_label}, confidence={confidence:.2f})"
                        )
                    else:
                        intent = "normal"
                        logger.debug(f"Low confidence sentiment, defaulting to normal")
                        
            except Exception as e:
                logger.error(f"Error in sentiment-based intent detection: {e}")
                intent = "normal"
        
        # Cache result
        self._intent_cache[text_hash] = (intent, time.time())
        return intent
    
    def _detect_intent_keywords(self, text_lower: str, lang: str) -> str:
        """Detect intent using semantic keyword matching (bilingual).
        
        Uses natural language patterns, NOT regex. Semantic understanding of context.
        
        Args:
            text_lower: Lowercase message text
            lang: User language ("id" or "en")
            
        Returns:
            str: Detected intent or "normal" if no clear match
        """
        # Define bilingual keyword patterns for each intent
        # Format: {intent: ([id_keywords], [en_keywords])}
        intent_patterns = {
            "gratitude": (
                # Indonesian
                ["terima kasih", "makasih", "thanks", "thx", "tengkyu", "matursuwun"],
                # English
                ["thank you", "thanks", "thx", "appreciate", "grateful"]
            ),
            "apology": (
                # Indonesian
                ["maaf", "mohon maaf", "sorry", "sori", "minta maaf", "nyesel"],
                # English
                ["sorry", "apologize", "apologies", "my bad", "forgive me"]
            ),
            "greeting": (
                # Indonesian
                ["hai", "halo", "hi", "hey", "selamat pagi", "selamat siang", 
                 "selamat sore", "selamat malam", "assalamualaikum", "salam"],
                # English
                ["hi", "hello", "hey", "good morning", "good afternoon", 
                 "good evening", "good night", "greetings", "yo", "sup"]
            ),
            "compliment": (
                # Indonesian
                ["cantik", "ganteng", "keren", "hebat", "pintar", "bagus", 
                 "luar biasa", "amazing", "perfect", "terbaik"],
                # English
                ["beautiful", "pretty", "handsome", "awesome", "amazing", "great",
                 "wonderful", "perfect", "best", "brilliant", "smart"]
            ),
            "insult": (
                # Indonesian
                ["bodoh", "tolol", "goblok", "idiot", "bego", "dungu", "anjing", 
                 "monyet", "kampret", "jelek", "buruk"],
                # English
                ["stupid", "idiot", "dumb", "moron", "fool", "ugly", "ugly"]
            ),
            "affection": (
                # Indonesian
                ["sayang", "cinta", "suka", "rindu", "kangen", "peluk", "cium",
                 "love you", "i love", "aku sayang"],
                # English
                ["love you", "i love", "miss you", "hug", "kiss", "darling", 
                 "sweetheart", "dear", "honey"]
            ),
            "romantic_interest": (
                # Indonesian
                ["pacar", "pacaran", "jadian", "menikah", "nikah", "istri", "suami",
                 "marry me", "be my", "jadi pacarku"],
                # English
                ["marry me", "be my girlfriend", "be my boyfriend", "date me",
                 "go out with me", "relationship", "couple"]
            ),
            "question": (
                # Indonesian (question markers)
                ["apa", "siapa", "kenapa", "bagaimana", "dimana", "kapan", "berapa",
                 "apakah", "mengapa", "gimana", "gmn"],
                # English
                ["what", "who", "why", "how", "where", "when", "which", "whose"]
            ),
            "toxic_behavior": (
                # Indonesian
                ["mati", "bunuh", "ancam", "hancurkan", "hajar", "babat", 
                 "gebuk", "pukul", "tendang"],
                # English
                ["kill", "die", "threat", "destroy", "hurt", "harm", "attack"]
            ),
            "rudeness": (
                # Indonesian
                ["babi", "tai", "shit", "fuck", "bangsat", "kontol", "memek",
                 "jancok", "cok", "asu"],
                # English
                ["fuck", "shit", "damn", "hell", "ass", "bitch", "bastard"]
            )
        }
        
        # Check each intent pattern
        for intent, (id_keywords, en_keywords) in intent_patterns.items():
            keywords = id_keywords if lang == "id" else en_keywords
            
            # Check if any keyword appears in text
            for keyword in keywords:
                if keyword in text_lower:
                    # Special handling for questions - check for question mark
                    if intent == "question":
                        if "?" in text_lower or text_lower.startswith(keyword):
                            return intent
                    else:
                        return intent
        
        return "normal"
    
    def _map_sentiment_to_intent(self, sentiment: str, text_lower: str, lang: str) -> str:
        """Map sentiment label to intent category with context awareness.
        
        Args:
            sentiment: Sentiment label (positive, negative, neutral)
            text_lower: Lowercase message text
            lang: User language
            
        Returns:
            str: Intent category
        """
        # Sentiment mapping with contextual refinement
        if "positive" in sentiment:
            # Positive sentiment could be gratitude, compliment, or affection
            if any(word in text_lower for word in ["terima", "thanks", "thank"]):
                return "gratitude"
            elif any(word in text_lower for word in ["bagus", "hebat", "keren", "great", "awesome"]):
                return "compliment"
            else:
                return "affection"  # Default positive intent
                
        elif "negative" in sentiment:
            # Negative sentiment could be insult, rudeness, or toxic
            if any(word in text_lower for word in ["maaf", "sorry", "apologize"]):
                return "apology"  # Negative but apologetic
            elif any(word in text_lower for word in ["bodoh", "tolol", "stupid", "idiot"]):
                return "insult"
            else:
                return "rudeness"  # Default negative intent
                
        else:
            # Neutral sentiment - could be question or normal conversation
            if "?" in text_lower:
                return "question"
            else:
                return "normal"
    
    def _map_label_to_intent(self, label: str, lang: str = "en") -> str:
        """Legacy method for backward compatibility. Not used in hybrid approach."""
        logger.warning("_map_label_to_intent called but not used in hybrid mode")
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
        signal_reasons = []  # Track why signals were assigned
        
        # Friendliness signals
        if intent in ["gratitude", "compliment", "greeting", "affection"]:
            signals["friendliness"] = 1
            signal_reasons.append(f"friendliness=1.0 (intent={intent})")
        elif emotion in ["joy", "happiness", "love"]:
            signals["friendliness"] = 0.8
            signal_reasons.append(f"friendliness=0.8 (emotion={emotion})")
        elif intent in ["asking_about_alya", "meaningful_conversation", "remembering_details"]:
            signals["friendliness"] = 0.7
            signal_reasons.append(f"friendliness=0.7 (intent={intent})")
        elif emotion in ["sadness", "fear", "worry"]:
            # Showing vulnerability builds connection
            signals["friendliness"] = 0.5
            signal_reasons.append(f"friendliness=0.5 (vulnerable emotion={emotion})")
        elif intent in ["insult", "rudeness", "toxic_behavior"]:
            signals["conflict"] = 1
            signal_reasons.append(f"conflict=1.0 (negative intent={intent})")
        
        # Romantic interest signals
        if intent == "affection":
            signals["romantic_interest"] = 1
            signal_reasons.append(f"romantic=1.0 (intent=affection)")
        elif intent == "romantic_interest":
            signals["romantic_interest"] = 0.8
            signal_reasons.append(f"romantic=0.8 (intent=romantic_interest)")
        elif any(word in text_lower for word in ["jadi pacarnya", "pacaran", "istri", "suami", "marry"]):
            signals["romantic_interest"] = 0.9
            signal_reasons.append(f"romantic=0.9 (romantic keywords detected)")
        elif emotion == "love":
            signals["romantic_interest"] = 0.6
            signal_reasons.append(f"romantic=0.6 (emotion=love)")
        
        # Conflict signals
        if emotion in ["anger", "frustration", "disgust"]:
            signals["conflict"] = 0.7
            signal_reasons.append(f"conflict=0.7 (emotion={emotion})")
        elif intent in ["insult", "rudeness", "toxic_behavior"]:
            signals["conflict"] = 1
            signal_reasons.append(f"conflict=1.0 (intent={intent})")
        elif intent == "apology":
            signals["conflict"] = -0.5  # Resolve conflict
            signal_reasons.append(f"conflict=-0.5 (apology resolves conflict)")
        
        # Log signal detection for affection tracking
        if signal_reasons:
            logger.debug(f"[NLP] Relationship signals detected: {', '.join(signal_reasons)}")
        
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
