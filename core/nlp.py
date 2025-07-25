"""
NLP utilities for Alya Bot, including emotion detection and personality modeling.
"""
import logging
import os
import random
import re
import difflib
from typing import Dict, List, Optional, Tuple, Any
from transformers import pipeline
from pathlib import Path
import hashlib
import time

from config.settings import (
    EMOTION_DETECTION_MODEL, 
    SENTIMENT_MODEL,
    NLP_MODELS_DIR,
    SUPPORTED_EMOTIONS,
    EMOTION_CONFIDENCE_THRESHOLD,
    FEATURES,
    MAX_CONTEXT_MESSAGES,
    SLIDING_WINDOW_SIZE
)
from database.database_manager import db_manager, DatabaseManager

logger = logging.getLogger(__name__)

class NLPEngine:
    """NLP engine for various text processing tasks including emotion detection and personality."""
    
    def __init__(self):
        """Initialize NLP models and caches."""
        self.emotion_classifier = None
        self.sentiment_analyzer = None
        self.emotion_memory: Dict[int, str] = {}
        self.conversation_context: Dict[int, Dict[str, Any]] = {}
        
        # Add caching for performance
        self._emotion_cache: Dict[str, Tuple[str, float]] = {}  # text_hash -> (emotion, timestamp)
        self._sentiment_cache: Dict[str, Tuple[str, float, float]] = {}  # text_hash -> (sentiment, score, timestamp)
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._max_cache_size = 1000  # Maximum cache entries
        
        self._initialize_models()
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text caching."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - timestamp < self._cache_ttl
    
    def _cleanup_cache(self, cache_dict: Dict[str, Tuple]) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, value in cache_dict.items()
            if current_time - value[-1] > self._cache_ttl
        ]
        for key in expired_keys:
            cache_dict.pop(key, None)
        
        # Limit cache size
        if len(cache_dict) > self._max_cache_size:
            # Remove oldest entries
            sorted_items = sorted(cache_dict.items(), key=lambda x: x[1][-1])
            for key, _ in sorted_items[:len(cache_dict) - self._max_cache_size]:
                cache_dict.pop(key, None)
    
    def _initialize_models(self) -> None:
        """Initialize NLP models if enabled."""
        try:
            # Only load models if features are enabled
            if FEATURES.get("emotion_detection", False):
                logger.info("Initializing emotion detection model...")
                
                # Check if using local model or hosted model
                emotion_model_path = EMOTION_DETECTION_MODEL
                if not any(prefix in EMOTION_DETECTION_MODEL for prefix in ['/', 'http', '\\']):
                    # If not an absolute path or URL, check if we have a local version
                    local_emotion_path = os.path.join(NLP_MODELS_DIR, "emotion-model")
                    if os.path.exists(local_emotion_path):
                        emotion_model_path = local_emotion_path
                        logger.info(f"Using local emotion model: {emotion_model_path}")
                    else:
                        logger.info(f"Using hosted emotion model: {emotion_model_path}")
                
                self.emotion_classifier = pipeline(
                    task="text-classification",
                    model=emotion_model_path,
                    top_k=3  # Get top 3 emotions for better context
                )
                logger.info("Emotion detection model initialized")
                
                # Add sentiment analyzer for more nuance
                logger.info("Initializing sentiment analyzer...")
                
                # Similar check for sentiment model
                sentiment_model_path = SENTIMENT_MODEL
                if not any(prefix in SENTIMENT_MODEL for prefix in ['/', 'http', '\\']):
                    local_sentiment_path = os.path.join(NLP_MODELS_DIR, "sentiment-model")
                    if os.path.exists(local_sentiment_path):
                        sentiment_model_path = local_sentiment_path
                        logger.info(f"Using local sentiment model: {sentiment_model_path}")
                    else:
                        logger.info(f"Using hosted sentiment model: {sentiment_model_path}")
                
                self.sentiment_analyzer = pipeline(
                    task="sentiment-analysis",
                    model=sentiment_model_path
                )
                logger.info("Sentiment analyzer initialized")
                
        except Exception as e:
            logger.error(f"Error initializing NLP models: {str(e)}")
            self.emotion_classifier = None
            self.sentiment_analyzer = None
    
    def detect_emotion(self, text: str, user_id: int = None) -> Optional[str]:
        """Detect the emotion in a text with user context awareness.
        
        Args:
            text: Input text
            user_id: User ID for context tracking
            
        Returns:
            Detected emotion label or None if unavailable
        """
        # Check if feature is enabled and model is loaded
        if not FEATURES.get("emotion_detection", False) or not self.emotion_classifier:
            return None
            
        try:
            # Cleanup cache
            self._cleanup_cache(self._emotion_cache)
            
            # Check cache first
            text_hash = self._get_text_hash(text)
            if text_hash in self._emotion_cache:
                cached_emotion, timestamp = self._emotion_cache[text_hash]
                if self._is_cache_valid(timestamp):
                    logger.debug(f"Cache hit for emotion: {cached_emotion} (text hash: {text_hash})")
                    return cached_emotion
            
            MAX_CHARS = 450  # Roughly estimate chars instead of tokens for simplicity
            if len(text) > MAX_CHARS:
                logger.debug(f"Text too long ({len(text)} chars), truncating to {MAX_CHARS} chars")
                text = text[:MAX_CHARS] + "..."
                
            # Get prediction
            result = self.emotion_classifier(text)
            
            if result and len(result[0]) > 0:
                # Get top emotions
                emotions = [(item['label'].lower(), item['score']) for item in result[0]]
                
                # Filter emotions with sufficient confidence
                valid_emotions = [(label, score) for label, score in emotions 
                                  if score >= EMOTION_CONFIDENCE_THRESHOLD 
                                  and label in SUPPORTED_EMOTIONS]
                
                if valid_emotions:
                    # Get the strongest emotion
                    top_emotion, top_score = max(valid_emotions, key=lambda x: x[1])
                    
                    # Track emotion for this user
                    if user_id is not None:
                        self.emotion_memory[user_id] = top_emotion
                        
                    # Update cache
                    self._emotion_cache[text_hash] = (top_emotion, time.time())
                    
                    logger.debug(f"Detected emotion: {top_emotion} with score {top_score}")
                    return top_emotion
            
            # If no strong emotion detected, try to use previous emotion for continuity
            if user_id is not None and user_id in self.emotion_memory:
                return self.emotion_memory[user_id]
                
            logger.debug("No significant emotion detected")
            return "neutral"
        except Exception as e:
            logger.error(f"Error detecting emotion: {str(e)}")
            return None
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Analyze the sentiment of text.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (sentiment label, confidence score)
        """
        if not self.sentiment_analyzer:
            return "NEUTRAL", 0.5
            
        try:
            # Cleanup cache
            self._cleanup_cache(self._sentiment_cache)
            
            # Check cache first
            text_hash = self._get_text_hash(text)
            if text_hash in self._sentiment_cache:
                cached_sentiment, cached_score, timestamp = self._sentiment_cache[text_hash]
                if self._is_cache_valid(timestamp):
                    logger.debug(f"Cache hit for sentiment: {cached_sentiment} (text hash: {text_hash})")
                    return cached_sentiment, cached_score
            
            # Truncate text to avoid sequence length errors (most models have 512 token limit)
            MAX_CHARS = 450
            if len(text) > MAX_CHARS:
                logger.debug(f"Text too long for sentiment analysis ({len(text)} chars), truncating to {MAX_CHARS} chars")
                text = text[:MAX_CHARS] + "..."
                
            result = self.sentiment_analyzer(text)
            if result and len(result) > 0:
                sentiment = result[0]['label']
                score = result[0]['score']
                
                # Update cache
                self._sentiment_cache[text_hash] = (sentiment, score, time.time())
                
                return sentiment, score
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            
        return "NEUTRAL", 0.5
            
    def get_message_context(self, text: str, user_id: int = None) -> Dict[str, Any]:
        """Get comprehensive context information from a message.
        
        Args:
            text: Input text
            user_id: User ID for contextual tracking
            
        Returns:
            Dictionary with context information
        """
        # Initialize context
        context = {
            "emotion": "neutral",
            "intent": "statement",
            "relationship_signals": {
                "friendliness": 0.0,
                "romantic_interest": 0.0,
                "conflict": 0.0,
            },
            "intensity": 0.5,
            "semantic_topics": [],
            "linguistic_style": {},
        }
        
        # Detect emotion with context
        emotion = self.detect_emotion(text, user_id)
        if emotion:
            context["emotion"] = emotion
        
        # Analyze sentiment for additional context
        sentiment, score = self.analyze_sentiment(text)
        context["sentiment"] = {
            "label": sentiment,
            "score": score
        }
        
        # Determine conversation intent
        context["intent"] = self._detect_intent(text)
        
        # Analyze relationship signals
        context["relationship_signals"] = self._analyze_relationship_signals(text)
        
        # Estimate emotional intensity
        context["intensity"] = self._estimate_emotional_intensity(text, emotion or "neutral")
        
        # Extract semantic topics
        context["semantic_topics"] = self._extract_semantic_topics(text)
        
        # Analyze linguistic style
        context["linguistic_style"] = self._analyze_linguistic_style(text)
        
        # Store in conversation context
        if user_id is not None:
            self.conversation_context[user_id] = context
            
        return context
    
    def _detect_intent(self, text: str) -> str:
        """Detect the user's conversational intent.
        
        Args:
            text: Input text
            
        Returns:
            Intent classification
        """
        # Advanced intent detection using both keywords and patterns
        text = text.lower()
        
        # Intent detection patterns
        intent_patterns = {
            "help_request": [
                r'\b(help|tolong|bantuan|bantu)\b',
                r'\b(bagaimana|caranya|cara)\b.+(melakukan|membuat)',
                r'\b(bisa|boleh).+(membantu|tolong)'
            ],
            "gratitude": [
                r'\b(thanks|thank you|thx|terima kasih|makasih|thks|ty)\b',
                r'\b(appreciate|menghargai)\b'
            ],
            "greeting": [
                r'\b(hello|hi|hey|halo|hai|pagi|siang|sore|malam|ohayou|konnichiwa|konbanwa)\b',
                r'^(hi|halo|hai|yo)[\s\.,!]*$'
            ],
            "question": [
                r'\?',
                r'\b(apa|bagaimana|kenapa|siapa|kapan|dimana|mengapa|gimana|apakah)\b',
                r'\b(can you|could you|would you|bisakah|bolehkah|maukah)\b'
            ],
            "apology": [
                r'\b(sorry|maaf|apologize|apologise|gomen)\b',
                r'\b(my bad|salahku)\b'
            ],
            "affection": [
                r'\b(love|suka|cinta|sayang|like you|menyukaimu|mencintaimu|suki|daisuki|aishiteru)\b',
                r'\b(peduli|care)\b.+(kamu|kau|you)',
                r'\b(kangen|miss)\b'
            ],
            "command": [
                r'^[/!].+',
                r'\b(tolong|please)\b.+(lakukan|buat|create|make|do)'
            ],
            "opinion_request": [
                r'\b(menurutmu|pendapatmu|what do you think|how do you feel)\b',
                r'\b(agree|setuju|disagree|tidak setuju)\b'
            ],
            # Add departure/leaving intent detection
            "departure": [
                r'\b(pergi|leave|leaving|berangkat|meninggalkan|tinggal)\b',
                r'\b(goodbye|selamat tinggal|sampai jumpa|dadah|bye|pamit)\b',
                r'\b(pulang|go home|keluar)\b'
            ]
        }
        
        # Check each pattern
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return intent
        
        # Default to statement if no pattern matches
        return "statement"
    
    def _analyze_relationship_signals(self, text: str) -> Dict[str, float]:
        """Analyze signals about relationship from text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of relationship signals and their strengths
        """
        text = text.lower()
        
        # Enhanced signal detection with weighted keywords and context
        signals = {
            "friendliness": 0.0,
            "romantic_interest": 0.0,
            "conflict": 0.0,
            "formality": 0.5,  # Middle ground as default
            "intimacy": 0.0,
        }
        
        # Friendliness markers with weights
        friendly_words = {
            "teman": 0.2, "friend": 0.2, "kawan": 0.2, "baik": 0.1, "senang": 0.1, "nice": 0.1,
            "asik": 0.15, "seru": 0.15, "fun": 0.15, "enjoy": 0.15,
            "berteman": 0.25
        }
        
        # Romantic interest markers with weights
        romantic_words = {
            "suka": 0.2, "love": 0.3, "cinta": 0.3, "sayang": 0.3, 
            "cantik": 0.15, "manis": 0.15, "cute": 0.15, "beautiful": 0.15, "pretty": 0.15,
            "pacar": 0.4, "girlfriend": 0.4, "boyfriend": 0.4,
            "nikah": 0.5, "marry": 0.5, "wedding": 0.5,
            "date": 0.2, "dating": 0.2, "kencan": 0.2
        }
        
        # Conflict markers with weights
        conflict_words = {
            "marah": 0.3, "kesal": 0.2, "benci": 0.4, "hate": 0.4, 
            "jelek": 0.2, "bodoh": 0.2, "stupid": 0.2, "idiot": 0.3,
            "jangan": 0.1, "berisik": 0.2, "noisy": 0.2, 
            "diam": 0.15, "shut up": 0.3, "fuck": 0.5
        }
        
        # Formality signals
        formal_words = {
            "anda": 0.8, "bapak": 0.8, "ibu": 0.8, "saudara": 0.7,
            "terima kasih": 0.6, "mohon": 0.7, "berkenan": 0.8,
            "maaf": 0.6, "tolong": 0.5
        }
        
        informal_words = {
            "lo": -0.7, "lu": -0.7, "gue": -0.7, "gw": -0.7,
            "elu": -0.7, "ngga": -0.5, "gak": -0.5, "yoi": -0.6,
            "sih": -0.3, "dong": -0.4, "banget": -0.3,
            "bro": -0.6, "sis": -0.6, "gan": -0.6, "cuy": -0.7
        }
        
        # Intimacy signals
        intimacy_words = {
            "hanya kamu": 0.7, "only you": 0.7, "secret": 0.4, "rahasia": 0.4,
            "private": 0.5, "pribadi": 0.5, "percaya": 0.3, "trust": 0.3,
            "just us": 0.6, "berdua": 0.6, "together": 0.4, "bersama": 0.4
        }
        
        # Process friendliness
        for word, weight in friendly_words.items():
            if word in text:
                signals["friendliness"] += weight
                
        # Process romantic interest
        for word, weight in romantic_words.items():
            if word in text:
                signals["romantic_interest"] += weight
        
        # Process conflict
        for word, weight in conflict_words.items():
            if word in text:
                signals["conflict"] += weight
                
        # Process formality (positive = formal, negative = informal)
        base_formality = 0.5  # Start neutral
        
        for word, weight in formal_words.items():
            if word in text:
                base_formality += (weight - 0.5) * 0.5  # Adjust toward formal
                
        for word, weight in informal_words.items():
            if word in text:
                base_formality += (weight + 0.5) * 0.5  # Adjust toward informal
        
        # Ensure formality is between 0 and 1
        signals["formality"] = max(0.0, min(1.0, base_formality))
        
        # Process intimacy
        for word, weight in intimacy_words.items():
            if word in text:
                signals["intimacy"] += weight
        
        # Cap all values at 1.0
        for key in signals:
            signals[key] = min(signals[key], 1.0)
                
        return signals
    
    def _estimate_emotional_intensity(self, text: str, emotion: str) -> float:
        """Estimate the intensity of an emotion in text.
        
        Args:
            text: Input text
            emotion: Detected emotion
            
        Returns:
            Intensity score (0.0-1.0)
        """
        # Enhanced estimation using multiple signals
        intensity = 0.5  # Default medium intensity
        
        # 1. Punctuation signals
        exclamations = text.count('!')
        intensity += min(exclamations * 0.1, 0.3)
        
        question_marks = text.count('?')
        if question_marks > 2:
            intensity += min((question_marks - 1) * 0.05, 0.2)
            
        # 2. ALL CAPS indicates higher intensity
        words = text.split()
        caps_words = sum(1 for word in words if word.isupper() and len(word) > 1)
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        
        if caps_words >= 2 or caps_ratio > 0.5:
            intensity += 0.2
            
        # 3. Repetition indicates intensity (e.g., "very very")
        for word in ["very", "sangat", "really", "banget", "sekali", "amat"]:
            count = len(re.findall(fr'\b{word}\b', text.lower()))
            if count > 1:
                intensity += min(count * 0.05, 0.15)
                
        # 4. Emotion-specific intensifiers
        emotion_intensifiers = {
            "joy": ["excited", "thrilled", "overjoyed", "ecstatic", "senang sekali", "bahagia"],
            "sadness": ["devastated", "heartbroken", "despair", "sedih sekali", "hancur"],
            "anger": ["furious", "enraged", "livid", "marah sekali", "murka", "kesal"],
            "fear": ["terrified", "petrified", "horrified", "takut sekali", "ketakutan"],
            "surprise": ["shocked", "astounded", "flabbergasted", "terkejut", "kaget"],
        }
        
        # Check for emotion-specific intensifiers
        if emotion in emotion_intensifiers:
            for word in emotion_intensifiers[emotion]:
                if word in text.lower():
                    intensity += 0.15
                    break
        
        # 5. Repetitive punctuation like "!!!" or "???"
        if re.search(r'[!?]{3,}', text):
            intensity += 0.2
            
        # 6. Emoji repetition
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251" 
            "]+"
        )
        
        emojis = emoji_pattern.findall(text)
        if len(emojis) > 2:
            intensity += min((len(emojis) - 2) * 0.05, 0.3)
        
        # Limit to range 0.0-1.0
        return min(max(intensity, 0.0), 1.0)
    
    def _extract_semantic_topics(self, text: str) -> List[str]:
        """Extract key semantic topics from text using more natural detection.
        
        Args:
            text: Input text
            
        Returns:
            List of detected semantic topics
        """
        # Towards a more semantic approach rather than keyword-based
        topics = []
        
        # 1. Use a more comprehensive topic model (this is just a placeholder)
        # In production would use embeddings similarity to topic vectors
        
        # Common conversation categories
        topic_categories = {
            "academic": {
                "patterns": [
                    r'\b(sekolah|pelajaran|kelas|nilai|ujian|tugas|belajar|pr|guru)\b',
                    r'\b(school|study|class|exam|teacher|homework|assignment)\b',
                    r'\b(matematika|fisika|kimia|biologi|sejarah|geografi)\b'
                ],
                "topics": ["school work", "academics", "studying"]
            },
            "personal_feelings": {
                "patterns": [
                    r'\b(perasaan|rasa|suka|cinta|sayang|sedih|senang|bahagia|marah)\b',
                    r'\b(feel|feeling|happy|sad|angry|love|like|emotion)\b',
                    r'\b(hati|pikiran|mood|perasaan|emosi)\b'
                ],
                "topics": ["emotions", "feelings", "personal state"]
            },
            "relationship": {
                "patterns": [
                    r'\b(pacar|hubungan|cinta|suka|sayang|kencan|date|pasangan|jalan|berdua)\b',
                    r'\b(boyfriend|girlfriend|relationship|dating|couple|together|love)\b',
                    r'\b(romantis|peluk|cium|kangen|rindu|sayang)\b'
                ],
                "topics": ["relationships", "romance", "dating"]
            },
            "daily_life": {
                "patterns": [
                    r'\b(makan|tidur|bangun|jalan|main|hobby|film|musik|lagu|baca|buku)\b',
                    r'\b(eat|sleep|walk|play|hobby|movie|music|song|read|book)\b',
                    r'\b(restoran|cafe|mall|taman|rumah|kamar)\b'
                ],
                "topics": ["daily activities", "entertainment", "lifestyle"]
            },
            "future_plans": {
                "patterns": [
                    r'\b(rencana|plan|masa depan|future|cita-cita|mimpi|harapan|goal)\b',
                    r'\b(kuliah|kerja|karir|bisnis|university|job|career|business)\b',
                    r'\b(nanti|besok|minggu depan|bulan depan|tahun depan)\b'
                ],
                "topics": ["future plans", "goals", "aspirations"]
            }
        }
        
        # Check each topic category
        text_lower = text.lower()
        for category, data in topic_categories.items():
            for pattern in data["patterns"]:
                if re.search(pattern, text_lower):
                    topics.extend(data["topics"])
                    break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = [topic for topic in topics if not (topic in seen or seen.add(topic))]
        
        # 2. Sentiment Analysis Integration (if model available)
        if self.sentiment_analyzer:
            sentiment, _ = self.analyze_sentiment(text)
            if sentiment.lower() in ["positive", "neutral", "negative"]:
                sentiment_topic = f"{sentiment.lower()} tone"
                unique_topics.append(sentiment_topic)
        
        # 3. Conversation Analysis
        if "?" in text:
            unique_topics.append("question")
        if len(text) > 100:
            unique_topics.append("detailed message")
        elif len(text) < 20:
            unique_topics.append("brief message")
            
        return unique_topics[:3]  # Limit to top 3 topics
    
    def _analyze_linguistic_style(self, text: str) -> Dict[str, float]:
        """Analyze the linguistic style of text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of linguistic style features
        """
        style = {
            "formality": 0.5,  # 0=very informal, 1=very formal
            "complexity": 0.5,  # 0=simple, 1=complex
            "directness": 0.5,  # 0=indirect, 1=direct
            "emotionality": 0.5,  # 0=neutral, 1=emotional
            "politeness": 0.5,  # 0=rude, 1=polite
        }
        
        # Basic linguistic analysis
        words = text.split()
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        
        # Complexity based on sentence length and word length
        sentences = text.split('.')
        avg_sentence_length = len(words) / max(len(sentences), 1)
        
        # Longer words and sentences suggest higher complexity
        style["complexity"] = min(1.0, (avg_word_length / 5) * 0.5 + (avg_sentence_length / 20) * 0.5)
        
        # Emotionality based on punctuation and emotional words
        emotional_markers = ["!", "?", "wow", "omg", "wtf", "amazing", "terrible",
                           "awesome", "horrible", "love", "hate", "keren", "woah"]
        
        emotional_count = sum(1 for marker in emotional_markers if marker in text.lower())
        style["emotionality"] = min(1.0, emotional_count * 0.1 + text.count("!") * 0.05)
        
        # Politeness based on polite words
        polite_words = ["please", "thank", "tolong", "terima kasih", "maaf", "mohon"]
        polite_count = sum(1 for word in polite_words if word in text.lower())
        style["politeness"] = min(1.0, 0.5 + polite_count * 0.1)
        
        # Directness based on direct statements or hedging
        hedging_words = ["maybe", "perhaps", "mungkin", "sepertinya", "kayaknya", "kira-kira"]
        direct_words = ["definitely", "absolutely", "pasti", "jelas", "harus"]
        
        hedging_count = sum(1 for word in hedging_words if word in text.lower())
        direct_count = sum(1 for word in direct_words if word in text.lower())
        
        style["directness"] = min(1.0, 0.5 - hedging_count * 0.1 + direct_count * 0.1)
        
        return style
        
    def suggest_mood_for_response(self, user_context: Dict[str, Any], 
                                  relationship_level: int) -> str:
        """Suggest an appropriate response mood based on context.
        
        Args:
            user_context: User message context
            relationship_level: Current relationship level
            
        Returns:
            Suggested mood for response
        """
        # Extract key context elements
        emotion = user_context.get("emotion", "neutral")
        intent = user_context.get("intent", "statement")
        intensity = user_context.get("intensity", 0.5)
        relationship_signals = user_context.get("relationship_signals", {})
        
        # Use softmax-like probabilities to select mood based on multiple factors
        mood_probs = {
            "tsundere_cold": 0.0,
            "tsundere_defensive": 0.0,
            "dere_caring": 0.0,
            "academic_serious": 0.0,
            "surprised_genuine": 0.0,
            "happy_genuine": 0.0,
            "apologetic_sincere": 0.0
        }
        
        # Base mood probabilities by relationship level
        if relationship_level == 0:  # Stranger
            mood_probs["tsundere_cold"] = 0.5
            mood_probs["tsundere_defensive"] = 0.3
            mood_probs["academic_serious"] = 0.2
        elif relationship_level == 1:  # Acquaintance
            mood_probs["tsundere_cold"] = 0.3
            mood_probs["tsundere_defensive"] = 0.3
            mood_probs["academic_serious"] = 0.2
            mood_probs["dere_caring"] = 0.1
            mood_probs["happy_genuine"] = 0.1
        elif relationship_level == 2:  # Friend
            mood_probs["tsundere_defensive"] = 0.3
            mood_probs["dere_caring"] = 0.3
            mood_probs["happy_genuine"] = 0.2
            mood_probs["academic_serious"] = 0.1
            mood_probs["tsundere_cold"] = 0.1
        else:  # Close Friend (3+)
            mood_probs["dere_caring"] = 0.4
            mood_probs["happy_genuine"] = 0.3
            mood_probs["tsundere_defensive"] = 0.2
            mood_probs["academic_serious"] = 0.1
        
        # Adjust by user's emotion
        emotion_adjustments = {
            "joy": {"happy_genuine": 0.3, "dere_caring": 0.2},
            "sadness": {"dere_caring": 0.4, "tsundere_cold": -0.2},
            "anger": {"tsundere_defensive": 0.3, "tsundere_cold": 0.2, "dere_caring": -0.1},
            "fear": {"dere_caring": 0.4, "academic_serious": 0.1},
            "surprise": {"surprised_genuine": 0.5, "academic_serious": 0.1},
            "neutral": {}  # No adjustment
        }
        
        # Apply emotion-based adjustments
        for mood, adj in emotion_adjustments.get(emotion, {}).items():
            if mood in mood_probs:
                mood_probs[mood] += adj
        
        # Adjust by intent
        intent_adjustments = {
            "help_request": {"dere_caring": 0.3, "academic_serious": 0.2},
            "gratitude": {"happy_genuine": 0.3, "dere_caring": 0.2, "tsundere_defensive": -0.2},
            "greeting": {"happy_genuine": 0.2},
            "question": {"academic_serious": 0.3},
            "apology": {"dere_caring": 0.2, "tsundere_defensive": -0.1},
            "affection": {"tsundere_defensive": 0.3 if relationship_level < 2 else -0.1,
                         "dere_caring": 0.3 if relationship_level >= 2 else 0.1,
                         "happy_genuine": 0.2 if relationship_level >= 2 else 0.0}
        }
        
        # Apply intent-based adjustments
        for mood, adj in intent_adjustments.get(intent, {}).items():
            if mood in mood_probs:
                mood_probs[mood] += adj
        
        # Adjust by relationship signals
        if relationship_signals.get("romantic_interest", 0) > 0.4:
            if relationship_level < 2:
                mood_probs["tsundere_defensive"] += 0.3
            else:
                mood_probs["dere_caring"] += 0.3
                
        if relationship_signals.get("conflict", 0) > 0.3:
            mood_probs["tsundere_cold"] += 0.3
            mood_probs["dere_caring"] -= 0.2
            
        # Add randomness for more natural variation
        for mood in mood_probs:
            mood_probs[mood] += random.uniform(0, 0.1)
            # Ensure all probabilities remain positive
            mood_probs[mood] = max(0.0, mood_probs[mood])
            
        # Select mood based on highest probability
        selected_mood = max(mood_probs.items(), key=lambda x: x[1])[0]
            
        return selected_mood

    def suggest_emojis(self, message: str, mood: str, count: int = 4) -> List[str]:
        """Suggest contextually appropriate emojis based on message and mood.
        
        Args:
            message: Text message to analyze for context
            mood: Current emotional mood
            count: Maximum number of emojis to suggest
            
        Returns:
            List of emoji strings appropriate for the context
        """
        # Dictionary of mood-emoji mapping with contextual awareness
        mood_emoji_mapping = {
            # Basic moods
            "neutral": ["✨", "💭", "🌸", "💫"],
            "happy": ["😊", "💕", "✨", "🌟"],
            "sad": ["😔", "💔", "🥺", "💧"],
            "surprised": ["😳", "⁉️", "🙀", "❗"],
            "angry": ["😤", "💢", "😠", "🔥"],
            
            # Complex moods
            "dere_caring": ["💕", "🥰", "💖", "✨"],
            "tsundere_cold": ["😒", "💢", "❄️", "🙄"],
            "tsundere_defensive": ["😳", "💥", "🔥", "❗"],
            "academic_serious": ["📝", "🎓", "📚", "🧐"],
            "apologetic_sincere": ["🙇‍♀️", "😔", "🙏", "💔"],
            "happy_genuine": ["🥰", "💓", "✨", "🌟"],
            "surprised_genuine": ["😳", "⁉️", "💫", "❗"],
        }
        
        # Topic-based emoji mappings
        topic_emoji_mapping = {
            "school": ["📚", "✏️", "🎓", "📝", "🧠"],
            "relationship": ["💕", "💘", "💞", "💓", "💗"],
            "food": ["🍜", "🍙", "🍱", "🍵", "🍡"],
            "entertainment": ["🎮", "🎵", "🎬", "📺", "🎧"],
            "personal": ["💭", "💫", "✨", "💝", "🌟"],
            "anime": ["✨", "🌸", "💫", "🎌", "🌟"],
            "tech": ["💻", "📱", "⚙️", "🤖", "🔍"],
        }
        
        # Detect topics in message
        topics = self._extract_semantic_topics(message)
        
        # Build candidate emoji pool
        emoji_candidates = []
        
        # 1. Add mood-based emojis (highest priority)
        mood_key = mood.split('_')[0] if '_' in mood else mood
        if mood in mood_emoji_mapping:
            emoji_candidates.extend(mood_emoji_mapping[mood])
        elif mood_key in mood_emoji_mapping:
            emoji_candidates.extend(mood_emoji_mapping[mood_key])
        
        # 2. Add topic-based emojis
        for topic in topics:
            if topic in topic_emoji_mapping:
                emoji_candidates.extend(topic_emoji_mapping[topic])
        
        # 3. Add default emojis if needed
        if not emoji_candidates:
            emoji_candidates = ["✨", "💫", "🌸", "💭"]
        
        # Ensure uniqueness and randomness
        unique_candidates = list(set(emoji_candidates))
        if len(unique_candidates) >= count:
            return random.sample(unique_candidates, count)
        else:
            return random.choices(unique_candidates, k=count)  # Allow repetition if needed

    def get_emotion_description(self, emotion: str) -> str:
        """Get a natural language description for an emotion.
        
        Args:
            emotion: Emotion identifier string
            
        Returns:
            Natural language description of the emotion
        """
        emotion_descriptions = {
            # Basic emotions
            "neutral": ["sedang tenang", "dalam mode normal", "santai"],
            "happy": ["terlihat senang", "sedang bahagia", "tampak ceria"],
            "sad": ["terlihat sedih", "agak murung", "sedikit kecewa"],
            "surprised": ["sangat terkejut", "mata terbelalak", "tercengang"],
            "angry": ["agak kesal", "sedikit marah", "tidak senang"],
            
            # Complex emotions
            "tsundere_cold": ["bersikap dingin", "pura-pura tidak peduli", "menjaga jarak"],
            "tsundere_defensive": ["jadi defensif", "malu-malu", "tidak jujur pada perasaan"],
            "dere_caring": ["jadi perhatian", "sangat peduli", "mulai lembut"],
            "academic_serious": ["mode serius", "penuh konsentrasi", "fokus analitis"],
            "happy_genuine": ["sangat bahagia", "benar-benar senang", "gembira sekali"],
            "surprised_genuine": ["benar-benar kaget", "sangat terkejut", "tak menyangka"],
            "apologetic_sincere": ["merasa bersalah", "ingin minta maaf", "menyesal"]
        }
        
        if emotion in emotion_descriptions:
            return random.choice(emotion_descriptions[emotion])
        
        # Handle compound emotions by splitting
        if "_" in emotion:
            parts = emotion.split("_")
            if parts[0] in emotion_descriptions:
                return random.choice(emotion_descriptions[parts[0]])
                
        return emotion.replace("_", " ")  # Fallback

    def analyze_conversation_flow(self, user_id: int, current_message: str) -> Dict[str, Any]:
        """
        Analyze conversation flow and context continuity.
        
        Args:
            user_id: User's telegram ID
            current_message: Current message content
            
        Returns:
            Dictionary with conversation flow analysis
        """
        try:
            flow_analysis = {
                "is_continuation": False,
                "topic_shift": False,
                "emotional_shift": False,
                "conversation_depth": 0,
                "user_engagement_level": "low"
            }
            
            # Get previous context if available
            previous_context = self.conversation_context.get(user_id, {})
            current_context = self.get_message_context(current_message, user_id)
            
            if previous_context:
                # Check if conversation is continuing on same topic
                prev_topics = set(previous_context.get("semantic_topics", []))
                current_topics = set(current_context.get("semantic_topics", []))
                
                topic_overlap = 0.0  # Initialize with default value
                if prev_topics and current_topics:
                    topic_overlap = len(prev_topics.intersection(current_topics)) / len(prev_topics.union(current_topics))
                    flow_analysis["is_continuation"] = topic_overlap > 0.3
                    flow_analysis["topic_shift"] = topic_overlap < 0.2
                
                # Check emotional consistency
                prev_emotion = previous_context.get("emotion", "neutral")
                current_emotion = current_context.get("emotion", "neutral")
                
                # Define emotional distance
                emotional_distances = {
                    ("happy", "sad"): 0.8,
                    ("angry", "happy"): 0.7,
                    ("excited", "bored"): 0.9,
                    ("love", "angry"): 0.8,
                    ("neutral", "angry"): 0.5,
                    ("neutral", "happy"): 0.3,
                }
                
                distance = emotional_distances.get((prev_emotion, current_emotion), 0.2)
                flow_analysis["emotional_shift"] = distance > 0.6
                
                # Calculate conversation depth based on message complexity and context
                prev_intensity = previous_context.get("intensity", 0.5)
                current_intensity = current_context.get("intensity", 0.5)
                
                avg_intensity = (prev_intensity + current_intensity) / 2
                flow_analysis["conversation_depth"] = min(1.0, avg_intensity + topic_overlap)
            else:
                # No previous context, set default values
                flow_analysis["conversation_depth"] = 0.3  # Default moderate depth
            
            # Analyze user engagement level
            message_length = len(current_message)
            question_count = current_message.count('?')
            exclamation_count = current_message.count('!')
            
            engagement_score = 0
            if message_length > 50:
                engagement_score += 0.3
            if question_count > 0:
                engagement_score += 0.2 * min(question_count, 3)
            if exclamation_count > 0:
                engagement_score += 0.1 * min(exclamation_count, 2)
            if current_context.get("intensity", 0) > 0.6:
                engagement_score += 0.3
                
            if engagement_score > 0.7:
                flow_analysis["user_engagement_level"] = "high"
            elif engagement_score > 0.4:
                flow_analysis["user_engagement_level"] = "medium"
            else:
                flow_analysis["user_engagement_level"] = "low"
                
            return flow_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing conversation flow: {e}")
            return {
                "is_continuation": False,
                "topic_shift": False,
                "emotional_shift": False,
                "conversation_depth": 0,
                "user_engagement_level": "low"
            }

class ContextManager:
    """Manages conversation context and memory with DB-backed sliding window."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize context manager with DB manager."""
        self.db_manager = db_manager
        self.summaries: Dict[int, List[Dict[str, Any]]] = {}

    def get_context_window(self, user_id: int) -> List[Dict[str, Any]]:
        """Get last messages from DB and summaries for context window.

        Args:
            user_id: The user ID to get context for

        Returns:
            List of conversation messages formatted for Gemini API
        """
        messages = self.db_manager.get_conversation_history(user_id, limit=MAX_CONTEXT_MESSAGES)
        summaries = self.get_conversation_summaries(user_id)

        context_window = []
        # Add summaries as system message if any
        if summaries:
            for summary in summaries:
                context_window.append({
                    "role": "user",
                    "parts": [{"text": f"Ringkasan percakapan sebelumnya: {summary['content']}"}]
                })
        # Add last messages
        for msg in messages:
            role = msg.get("role", "user")
            # Gemini expects "user" or "model"
            if role == "assistant":
                role = "model"
            elif role != "user":
                role = "user"
            content = msg.get("content", "")
            context_window.append({
                "role": role,
                "parts": [{"text": content}]
            })
        return context_window

    def get_conversation_summaries(self, user_id: int) -> List[Dict[str, Any]]:
        """Get conversation summaries for a user (from DB or memory).

        Args:
            user_id: The user ID

        Returns:
            List of summaries (dict with 'content')
        """
        # Example: If you store summaries in a DB table, fetch here.
        # For now, fallback to in-memory summaries if available.
        return self.summaries.get(user_id, [])

    def add_summary(self, user_id: int, summary: Dict[str, Any]) -> None:
        """Add a summary for a user (in-memory or persist to DB)."""
        if user_id not in self.summaries:
            self.summaries[user_id] = []
        self.summaries[user_id].append(summary)

    def apply_sliding_window(self, user_id: int) -> None:
        """Apply sliding window: keep recent messages, summarize the rest."""
        # Get all messages for user
        all_messages = self.db_manager.get_conversation_history(user_id, limit=1000)
        if len(all_messages) > SLIDING_WINDOW_SIZE:
            to_summarize = all_messages[:-SLIDING_WINDOW_SIZE]
            if to_summarize:
                summary_content = self._summarize_messages(to_summarize)
                if summary_content:
                    self.add_summary(user_id, {"content": summary_content})
            # Delete old messages from DB, keep only recent ones
            self.db_manager.apply_sliding_window(user_id, keep_recent=SLIDING_WINDOW_SIZE)

    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Summarize a list of messages (simple join or use LLM for prod)."""
        # For now, join first/last and key points (replace with LLM summary for prod)
        if not messages:
            return ""
        first = messages[0].get("content", "")
        last = messages[-1].get("content", "")
        return f"Ringkasan: Mulai dari '{first[:40]}...' hingga '{last[:40]}...'."
