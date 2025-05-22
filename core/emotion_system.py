"""
Emotion System for Alya Bot.

This module provides emotion detection, tracking, and response generation
based on user interaction patterns and message content.
"""

import logging
import os
import json
import random
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)

# Try to import optional dependencies with fallback behavior
try:
    import torch
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("SentenceTransformer and/or PyTorch not available. Emotion analysis will use fallback mode.")
    EMBEDDINGS_AVAILABLE = False

import re
import yaml
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity

from core.personas import get_persona_context, persona_manager
from config.settings import DEFAULT_LANGUAGE

# Update path to moods configuration file
MOODS_CONFIG_PATH = Path(__file__).parent.parent / "config" / "persona" / "moods.yaml"

# Emotion types following human-like emotional model
class EmotionType(Enum):
    """Primary emotion types following psychological models."""
    NEUTRAL = "neutral"        # Default neutral state
    HAPPY = "happy"            # Feeling joy/delight
    SAD = "sad"                # Feeling down/somber
    ANGRY = "angry"            # Feeling irritated/annoyed/upset
    SURPRISED = "surprised"    # Feeling unexpected shock/excitement
    AFRAID = "afraid"          # Feeling fear/anxiety
    DISGUSTED = "disgusted"    # Feeling repulsed/aversion
    CURIOUS = "curious"        # Feeling inquisitive/interested
    EMBARRASSED = "embarrassed"  # Feeling shy/awkward
    PROUD = "proud"            # Feeling satisfaction/achievement
    GRATEFUL = "grateful"      # Feeling thankful/appreciative
    CONCERNED = "concerned"    # Feeling worried/caring
    ENTHUSIASTIC = "enthusiastic"  # Feeling excited/energetic

class EmotionIntensity(Enum):
    """Intensity levels for emotions."""
    MILD = "mild"          # Slight hint of emotion
    MODERATE = "moderate"  # Clear but controlled emotion  
    STRONG = "strong"      # Obvious and significant emotion
    EXTREME = "extreme"    # Very pronounced emotion

@dataclass
class EmotionalState:
    """Class representing Alya's current emotional state."""
    
    primary: EmotionType = EmotionType.NEUTRAL
    secondary: Optional[EmotionType] = None
    intensity: EmotionIntensity = EmotionIntensity.MODERATE
    timestamp: float = field(default_factory=time.time)
    trigger: str = ""
    decay_rate: float = 0.2  # How quickly emotion returns to neutral (0-1)
    
    @property
    def age(self) -> float:
        """Get age of emotional state in seconds."""
        return time.time() - self.timestamp
        
    @property
    def is_active(self) -> bool:
        """Check if emotion is still active based on decay."""
        # Get decay seconds from config
        from core.mood_manager import mood_manager
        decay_seconds = mood_manager.mood_decay_seconds
        
        # High intensity emotions last longer based on intensity
        max_duration = {
            EmotionIntensity.MILD: decay_seconds * 0.3,       # 30% of decay time
            EmotionIntensity.MODERATE: decay_seconds * 0.6,   # 60% of decay time
            EmotionIntensity.STRONG: decay_seconds * 0.8,     # 80% of decay time
            EmotionIntensity.EXTREME: decay_seconds           # Full decay time
        }
        return self.age < max_duration.get(self.intensity, decay_seconds * 0.5)
    
    @property
    def current_intensity(self) -> EmotionIntensity:
        """Get current intensity considering decay over time."""
        if not self.is_active:
            return EmotionIntensity.MILD
            
        # Calculate decay based on age
        intensity_values = {
            EmotionIntensity.MILD: 1,
            EmotionIntensity.MODERATE: 2,
            EmotionIntensity.STRONG: 3,
            EmotionIntensity.EXTREME: 4
        }
        
        # Get decay rate from config
        from core.mood_manager import mood_manager
        decay_rate = mood_manager.mood_decay_rate
        
        current_value = intensity_values.get(self.intensity, 2)
        decay_amount = self.age * decay_rate / 60  # Decay per minute
        
        # Decay but never below MILD
        new_value = max(1, current_value - decay_amount)
        
        # Convert back to enum
        for emotion_type, value in intensity_values.items():
            if value >= new_value:
                return emotion_type
                
        return EmotionIntensity.MILD

class EmotionEngine:
    """
    Engine for managing Alya's emotions and generating appropriate responses.
    
    This class handles emotion detection, tracking emotional state over time,
    and generating contextually appropriate emotional responses.
    """
    
    def __init__(self):
        """Initialize dengan embedding model untuk deteksi emosi dan load config."""
        # Load the embedding model
        if EMBEDDINGS_AVAILABLE:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Load configurations
        self.config = self._load_config()
        
        # User emotion states storage
        self.user_emotions = {}
        
        # Example mapping for emotions
        self.emotion_examples = {
            EmotionType.HAPPY: [
                "Aku senang sekali hari ini", 
                "Berita bagus banget itu",
                "Ini kabar yang sangat menyenangkan",
                "Aku sangat bahagia mendengarnya"
            ],
            EmotionType.SAD: [
                "Aku sedih mendengarnya", 
                "Itu kabar buruk sekali",
                "Aku merasa kecewa dengan hal itu",
                "Ini berita yang menyedihkan"
            ],
            EmotionType.ANGRY: [
                "Aku kesal dengan hal itu", 
                "Ini sangat menjengkelkan",
                "Aku marah mendengarnya",
                "Hal ini membuatku sangat kesal"
            ],
            EmotionType.SURPRISED: [
                "Wow, aku tidak menyangka", 
                "Itu sangat mengejutkan",
                "Aku tidak percaya itu terjadi",
                "Sungguh mengagetkan"
            ],
            EmotionType.EMBARRASSED: [
                "Aku malu sekali", 
                "Ini memalukan",
                "Aku merasa tidak nyaman dengan hal itu",
                "Aku merasa malu"
            ],
            EmotionType.CURIOUS: [
                "Aku penasaran tentang hal itu", 
                "Ini menarik untuk dipelajari",
                "Aku ingin tahu lebih banyak",
                "Ini topik yang menarik"
            ]
        }
        
        # Generate embeddings for emotion examples
        self.emotion_embeddings = self._prepare_emotion_embeddings()
        
        # Store emotion actions for different personas
        self.emotion_actions = self._load_emotion_actions()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configurations from YAML file."""
        try:
            if not os.path.exists(MOODS_CONFIG_PATH):
                logger.error(f"Mood config file not found: {MOODS_CONFIG_PATH}")
                return {}
                
            with open(MOODS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            logger.info("Successfully loaded mood configuration for emotion system")
            return config or {}
        except Exception as e:
            logger.error(f"Error loading emotion config: {e}")
            return {}

    def _prepare_emotion_embeddings(self) -> Dict[EmotionType, List[float]]:
        """Generate embeddings untuk contoh-contoh emosi."""
        embeddings = {}
        if EMBEDDINGS_AVAILABLE:
            for emotion, examples in self.emotion_examples.items():
                embeddings[emotion] = self.model.encode(examples)
        return embeddings

    def detect_emotion(self, message: str) -> Tuple[EmotionType, EmotionIntensity]:
        """Deteksi emosi berdasarkan semantic similarity."""
        if not message or len(message) < 3:
            return EmotionType.NEUTRAL, EmotionIntensity.MILD
            
        if not EMBEDDINGS_AVAILABLE:
            return EmotionType.NEUTRAL, EmotionIntensity.MILD
            
        message_embedding = self.model.encode(message)
        best_emotion = EmotionType.NEUTRAL
        highest_score = 0.0

        for emotion, example_embeddings in self.emotion_embeddings.items():
            similarities = cosine_similarity([message_embedding], example_embeddings)[0]
            max_similarity = max(similarities)
            if max_similarity > highest_score:
                highest_score = max_similarity
                best_emotion = emotion

        # If score is too low, default to neutral
        if highest_score < 0.5:
            return EmotionType.NEUTRAL, EmotionIntensity.MILD
            
        intensity = self._map_score_to_intensity(highest_score)
        return best_emotion, intensity

    def _map_score_to_intensity(self, score: float) -> EmotionIntensity:
        """Map similarity score ke intensitas emosi."""
        if score > 0.8:
            return EmotionIntensity.STRONG
        elif score > 0.65:
            return EmotionIntensity.MODERATE
        else:
            return EmotionIntensity.MILD
    
    def _load_emotion_actions(self) -> Dict[str, Dict[EmotionType, List[str]]]:
        """Load emotion actions for different personas."""
        # This would ideally come from persona yamls
        # For now we'll create some default actions
        actions = {
            "tsundere": {
                EmotionType.HAPPY: [
                    "*wajah sedikit merona* B-bukan berarti aku senang atau apa...",
                    "*memalingkan wajah dengan senyum tipis* Hmph! Terserah...",
                    "*mencoba menyembunyikan senyuman* Y-ya... itu cukup bagus..."
                ],
                EmotionType.SAD: [
                    "*mengalihkan pandangan* Ini bukan apa-apa... Aku baik-baik saja...",
                    "*menghela napas pelan* B-bukan berarti aku sedih...",
                    "*merapikan rambut dengan gerakan kaku* Aku tidak peduli..."
                ],
                EmotionType.EMBARRASSED: [
                    "*wajah memerah* A-apa yang kau katakan!?",
                    "*memalingkan wajah dengan cepat* J-jangan menatapku seperti itu!",
                    "*merapikan rok dengan gugup* B-bodoh! Jangan salah paham!"
                ]
            },
            "waifu": {
                EmotionType.HAPPY: [
                    "*tersenyum cerah* Alya senang sekali~!",
                    "*mata berbinar* Itu membuatku sangat bahagia!",
                    "*bertepuk tangan kecil* Yay! Itu berita yang menyenangkan!"
                ],
                EmotionType.SAD: [
                    "*mata berkaca-kaca* Itu... sangat menyedihkan...",
                    "*menunduk pelan* Alya merasa sedih mendengarnya...",
                    "*menggigit bibir pelan* Maaf... itu berita yang menyedihkan..."
                ],
                EmotionType.EMBARRASSED: [
                    "*pipi merona merah* E-eh? A-alya tidak tahu harus berkata apa...",
                    "*menutupi wajah dengan tangan* Mou~ Kamu membuatku malu!",
                    "*memilin ujung rambut dengan gugup* A-alya malu sekali..."
                ]
            }
        }
        return actions

    def update_emotional_state(self, user_id: int, message: str) -> None:
        """
        Update user's emotional state based on message.
        
        Args:
            user_id: User ID
            message: User's message text
        """
        # Detect emotion from current message
        emotion_type, intensity = self.detect_emotion(message)
        
        # If no emotion detected, return
        if emotion_type == EmotionType.NEUTRAL:
            return
            
        # Get current emotional state or create new one
        current_state = self.user_emotions.get(user_id)
        
        if not current_state or not current_state.is_active:
            # Create new emotional state
            self.user_emotions[user_id] = EmotionalState(
                primary=emotion_type,
                intensity=intensity,
                timestamp=time.time(),
                trigger=message[:50]  # Store first 50 chars as trigger
            )
        else:
            # Update existing emotional state
            # If same emotion, possibly intensify
            if current_state.primary == emotion_type:
                # Intensify if new intensity is higher
                if intensity_value(intensity) > intensity_value(current_state.intensity):
                    current_state.intensity = intensity
                    
                # Refresh timestamp
                current_state.timestamp = time.time()
                current_state.trigger = message[:50]
            else:
                # Different emotion - consider as secondary or replacement
                # If new emotion is stronger, make it primary
                if intensity_value(intensity) > intensity_value(current_state.intensity):
                    # Demote current primary to secondary
                    current_state.secondary = current_state.primary
                    current_state.primary = emotion_type
                    current_state.intensity = intensity
                else:
                    # Make new emotion secondary
                    current_state.secondary = emotion_type
                
                current_state.timestamp = time.time()
                current_state.trigger = message[:50]
            
            # Update decay rate from config
            from core.mood_manager import mood_manager
            current_state.decay_rate = mood_manager.mood_decay_rate
    
    def get_current_emotion(self, user_id: int) -> EmotionalState:
        """
        Get user's current emotional state.
        
        Args:
            user_id: User ID
            
        Returns:
            Current emotional state
        """
        # Get current state or create neutral one
        state = self.user_emotions.get(user_id)
        
        if not state or not state.is_active:
            # Return neutral state if none exists or expired
            return EmotionalState()
            
        return state
    
    def get_emotion_emojis(self, emotion: EmotionType, count: int = 1) -> List[str]:
        """
        Get emojis for an emotion from YAML config.
        
        Args:
            emotion: Emotion type
            count: Number of emojis to return
            
        Returns:
            List of emoji strings
        """
        # Map emotion to mood name
        mood_mapping = {
            EmotionType.HAPPY: 'senang',
            EmotionType.SAD: 'sedih',
            EmotionType.ANGRY: 'marah',
            EmotionType.AFRAID: 'takut',
            EmotionType.EMBARRASSED: 'malu'
        }
        
        mood_name = mood_mapping.get(emotion)
        if not mood_name:
            return []
            
        # Get emojis from config
        mood_emoji = self.config.get('mood_emoji', {})
        emoji_list = mood_emoji.get(mood_name, [])
        
        if not emoji_list:
            return []
            
        # Get random emojis
        result = []
        for _ in range(min(count, len(emoji_list))):
            emoji = random.choice(emoji_list)
            emoji_list.remove(emoji)  # Avoid duplicates
            result.append(emoji)
            
        return result
    
    def get_emotional_response(self, user_id: int, persona: str = "tsundere") -> Optional[str]:
        """
        Get an appropriate emotional response based on user's emotional state.
        
        Args:
            user_id: User ID
            persona: Current persona
            
        Returns:
            Emotional response text or None if not applicable
        """
        # Get current emotional state
        emotion = self.get_current_emotion(user_id)
        
        # If neutral or expired emotion, no special response
        if emotion.primary == EmotionType.NEUTRAL or not emotion.is_active:
            return None
            
        # Get actions for this persona and emotion
        persona_actions = self.emotion_actions.get(persona, {})
        emotion_actions = persona_actions.get(emotion.primary, [])
        
        # If no specific actions, try generic ones
        if not emotion_actions and persona != "tsundere":
            # Fall back to tsundere actions
            emotion_actions = self.emotion_actions.get("tsundere", {}).get(emotion.primary, [])
            
        # If still no actions, return None
        if not emotion_actions:
            return None
            
        # Choose a random action
        action = random.choice(emotion_actions)
        
        # Maybe add emotion emoji
        emojis = self.get_emotion_emojis(emotion.primary)
        emoji_suffix = f" {emojis[0]}" if emojis and random.random() < 0.7 else ""
        
        # Check for Russian expression probability
        russian_expression = self._get_russian_expression(persona)
        russian_suffix = f" {russian_expression}" if russian_expression else ""
        
        # Add flavor text based on emotion and persona
        if persona == "tsundere":
            if emotion.primary == EmotionType.HAPPY:
                return f"{action} B-bukan berarti Alya senang atau apa...{emoji_suffix}{russian_suffix}"
            elif emotion.primary == EmotionType.CONCERNED:
                return f"{action} B-bukan berarti Alya khawatir tentangmu...{emoji_suffix}{russian_suffix}"
            elif emotion.primary == EmotionType.EMBARRASSED:
                return f"{action} J-jangan salah paham!{emoji_suffix}{russian_suffix}"
        elif persona == "waifu":
            if emotion.primary == EmotionType.HAPPY:
                return f"{action} Alya senang sekali~!{emoji_suffix}{russian_suffix}"
            elif emotion.primary == EmotionType.CONCERNED:
                return f"{action} Alya peduli padamu...{emoji_suffix}{russian_suffix}"
                
        # Default just return the action
        return f"{action}{emoji_suffix}{russian_suffix}"
    
    def _get_russian_expression(self, persona: str) -> Optional[str]:
        """Get a Russian expression based on personality and randomness."""
        # Check persona settings
        persona_config = self.config.get('persona_settings', {}).get(persona, {})
        chance = persona_config.get('russian_expression_chance', 0)
        
        # Determine if we use expression
        if random.random() * 100 > chance:
            return None
            
        # Get expressions from persona
        try:
            from core.personas import persona_manager
            persona_data = persona_manager.get_persona_config(persona)
            if not persona_data:
                return None
                
            expressions = persona_data.get('russian_expressions', [])
            if expressions:
                return random.choice(expressions)
        except Exception as e:
            logger.error(f"Error getting Russian expressions: {e}")
            
        return None
    
    def enhance_response_with_emotion(
        self, response: str, user_id: int, persona: str = "tsundere", language: str = DEFAULT_LANGUAGE
    ) -> str:
        """
        Enhance a response with emotional context.
        
        Args:
            response: Original response text
            user_id: User ID for emotional context
            persona: Current persona
            language: Language code for response formatting
            
        Returns:
            Emotion-enhanced response
        """
        # Get current emotional state
        emotion = self.get_current_emotion(user_id)
        
        # If neutral or mild emotion, return original
        if emotion.primary == EmotionType.NEUTRAL or emotion.intensity == EmotionIntensity.MILD:
            return response
            
        # Get emotional action
        emotional_action = self.get_emotional_response(user_id, persona)
        if not emotional_action:
            return response
            
        # Add emotional action to response
        # Check if response already has roleplay actions
        if "*" in response:
            # Already has roleplay, add emotion to beginning
            if random.random() < 0.7:  # 70% chance at the beginning
                return f"{emotional_action} {response}"
            else:
                return f"{response} {emotional_action}"
        else:
            # No roleplay, add emotion with higher probability at beginning
            if random.random() < 0.8:  # 80% chance at the beginning
                return f"{emotional_action} {response}"
            else:
                return f"{response} {emotional_action}"

# Helper function for comparing intensities
def intensity_value(intensity: EmotionIntensity) -> int:
    """Convert intensity enum to numeric value for comparison."""
    mapping = {
        EmotionIntensity.MILD: 1,
        EmotionIntensity.MODERATE: 2,
        EmotionIntensity.STRONG: 3,
        EmotionIntensity.EXTREME: 4
    }
    return mapping.get(intensity, 1)

# Create a singleton instance
emotion_engine = EmotionEngine()

# Convenience functions
def detect_emotion(message: str) -> Tuple[Optional[EmotionType], EmotionIntensity]:
    """Detect emotion from message text."""
    return emotion_engine.detect_emotion(message)

def update_emotion(user_id: int, message: str) -> None:
    """Update user's emotional state."""
    emotion_engine.update_emotional_state(user_id, message)

def get_emotion(user_id: int) -> EmotionalState:
    """Get user's current emotional state."""
    return emotion_engine.get_current_emotion(user_id)

def enhance_response(response: str, user_id: int, persona: str = "tsundere") -> str:
    """Enhance response with emotional context."""
    return emotion_engine.enhance_response_with_emotion(response, user_id, persona)
