"""
Emotion System for Alya Bot.

This module provides a sophisticated, human-like emotional response system
for Alya, allowing dynamic mood transitions and contextually appropriate reactions.
"""

import logging
import random
import re
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import time

from config.settings import PERSONALITY_STRENGTH
from core.personas import get_persona_context, persona_manager

logger = logging.getLogger(__name__)

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
        # High intensity emotions last longer
        max_duration = {
            EmotionIntensity.MILD: 30,      # 30 seconds
            EmotionIntensity.MODERATE: 120,  # 2 minutes
            EmotionIntensity.STRONG: 300,    # 5 minutes
            EmotionIntensity.EXTREME: 600    # 10 minutes
        }
        return self.age < max_duration.get(self.intensity, 60)
    
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
        
        current_value = intensity_values.get(self.intensity, 2)
        decay_amount = self.age * self.decay_rate / 60  # Decay per minute
        
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
        """Initialize the emotion engine with pattern detectors and responses."""
        # Current emotional states by user_id
        self.user_emotions: Dict[int, EmotionalState] = {}
        
        # Keywords that trigger emotional responses - expanded for more natural detection
        self.emotion_triggers = {
            # Happy triggers
            EmotionType.HAPPY: [
                r'(?i)(good|great|nice|awesome|amazing|excellent|wonderful|love|like|thank|thx|makasih|terima kasih)',
                r'(?i)(senang|suka|bahagia|bagus|keren|mantap|thanks|thx|makasih|gembira)',
                r'😊|😄|😁|😀|😃|🥰|❤️|💕|👍|🙏',
            ],
            
            # Sad triggers
            EmotionType.SAD: [
                r'(?i)(sad|sorry|unfortunate|bad|poor|maaf|sedih|kecewa|sakit|menyesal)',
                r'(?i)(apologize|forgive|regret|minta maaf|maafin|sedih|kasihan|terluka)',
                r'😢|😭|😞|😔|😥|☹️|💔|😿',
            ],
            
            # Angry triggers
            EmotionType.ANGRY: [
                r'(?i)(angry|mad|upset|annoyed|irritated|terrible|worst|hate|stupid|idiot|dumb|marah)',
                r'(?i)(kesal|bodoh|tolol|goblok|benci|buruk|jelek|menyebalkan|gak suka|ga suka)',
                r'😠|😡|🤬|👿|💢|😤',
            ],
            
            # Surprised triggers 
            EmotionType.SURPRISED: [
                r'(?i)(wow|whoa|omg|amazing|incredible|unbelievable|seriously|really|kaget)',
                r'(?i)(terkejut|serius|beneran|masa sih|kok bisa|astaga|astagfirullah|anjir)',
                r'😲|😮|😯|😱|😵|🤯|❗|❓',
            ],
            
            # Afraid triggers
            EmotionType.AFRAID: [
                r'(?i)(afraid|scared|fear|worry|anxious|nervous|takut|khawatir|cemas|ngeri)',
                r'(?i)(scary|horror|terrifying|menyeramkan|serem|horor|berbahaya)',
                r'😨|😰|😱|😖|🙀|😿',
            ],
            
            # Disgusted triggers
            EmotionType.DISGUSTED: [
                r'(?i)(gross|disgusting|eww|yuck|jijik|jorok|kotor|menjijikkan|najis|bau)',
                r'🤢|🤮|👎|💩',
            ],
            
            # Curious triggers
            EmotionType.CURIOUS: [
                r'(?i)(how|what|why|when|where|who|which|kenapa|bagaimana|siapa|kapan|dimana)',
                r'(?i)(curious|wonder|interested|tell me|explain|penasaran|jelaskan|ceritakan)',
                r'🤔|🧐|❓|🔍',
            ],
            
            # Embarrassed triggers
            EmotionType.EMBARRASSED: [
                r'(?i)(embarrassed|awkward|shy|blush|malu|canggung|bingung|kaku|maluuu)',
                r'😳|🙈|😅|😬|☺️',
            ],
            
            # Proud triggers
            EmotionType.PROUD: [
                r'(?i)(proud|achievement|accomplish|success|well done|bagus|hebat|berhasil)',
                r'(?i)(bangga|sukses|pencapaian|prestasi|keren|mantap)',
                r'🏆|🎖️|🥇|🌟|✨',
            ],
            
            # Grateful triggers
            EmotionType.GRATEFUL: [
                r'(?i)(thank|appreciate|grateful|terima kasih|makasih|thanks|thx|trims)',
                r'(?i)(makasih|tengkyu|thank you|thanks|thx|terimakasih)',
                r'🙏|❤️|💕',
            ],
            
            # Concerned triggers
            EmotionType.CONCERNED: [
                r'(?i)(worried|concerned|hope|care|peduli|khawatir|semoga|mudah-mudahan)',
                r'(?i)(harap|berharap|cemas|wish|pray|doa)',
                r'😟|🙁|🤞|🙏',
            ],
            
            # Enthusiastic triggers
            EmotionType.ENTHUSIASTIC: [
                r'(?i)(excited|can\'t wait|looking forward|semangat|ga sabar|tidak sabar)',
                r'(?i)(gak sabar|antusias|excited|pengen banget|segera)',
                r'🤩|🥳|🎉|💃|🕺|⭐|🔥',
            ],
        }
        
        # Roleplay actions for different emotions by persona type
        self.emotion_actions = self._load_emotion_actions()
    
    def _load_emotion_actions(self) -> Dict[str, Dict[EmotionType, List[str]]]:
        """
        Load emotion-specific roleplay actions for different personas.
        
        Returns:
            Dictionary mapping persona to emotion actions
        """
        # Default actions if files don't exist
        default_actions = {
            "tsundere": {
                EmotionType.HAPPY: [
                    "*trying to hide a smile*",
                    "*slight blush while looking away*",
                ],
                EmotionType.SAD: [
                    "*looks down with a slight frown*",
                    "*sighs softly*",
                ],
                EmotionType.ANGRY: [
                    "*crosses arms firmly*",
                    "*narrows eyes*",
                ],
                EmotionType.SURPRISED: [
                    "*eyes widen momentarily*",
                    "*takes a step back*",
                ],
                EmotionType.EMBARRASSED: [
                    "*face turns visibly red*",
                    "*fidgets nervously*",
                ],
            },
            "waifu": {
                EmotionType.HAPPY: [
                    "*smiles brightly*",
                    "*claps hands excitedly*",
                ],
                EmotionType.SAD: [
                    "*eyes glisten with emotion*",
                    "*holds hands to chest*",
                ],
                EmotionType.SURPRISED: [
                    "*covers mouth with hand*",
                    "*gasps softly*",
                ],
            },
            "informative": {
                EmotionType.CURIOUS: [
                    "*adjusts glasses thoughtfully*",
                    "*taps chin while thinking*",
                ],
            }
        }
        
        # In a real system, we'd load these from persona YAML files
        # For now using defaults with basic coverage for main personas
        return default_actions
    
    def detect_emotion(self, message: str) -> Tuple[Optional[EmotionType], EmotionIntensity]:
        """
        Detect potential emotion from message content.
        
        Args:
            message: User message text
            
        Returns:
            Tuple of (detected_emotion, intensity)
        """
        if not message:
            return None, EmotionIntensity.MILD
            
        # Check all emotion patterns
        detected_emotions = []
        
        for emotion_type, patterns in self.emotion_triggers.items():
            for pattern in patterns:
                matches = re.findall(pattern, message)
                if matches:
                    # Calculate intensity based on number and strength of matches
                    intensity = min(len(matches), 3)  # 1-3 scale
                    detected_emotions.append((emotion_type, intensity))
        
        if not detected_emotions:
            return None, EmotionIntensity.MILD
            
        # If multiple emotions detected, pick strongest one
        detected_emotions.sort(key=lambda x: x[1], reverse=True)
        emotion_type, intensity_score = detected_emotions[0]
        
        # Map score to intensity enum
        intensity_mapping = {
            1: EmotionIntensity.MILD,
            2: EmotionIntensity.MODERATE,
            3: EmotionIntensity.STRONG
        }
        
        return emotion_type, intensity_mapping.get(intensity_score, EmotionIntensity.MODERATE)
    
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
        if not emotion_type:
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
        
        # Add flavor text based on emotion and persona
        if persona == "tsundere":
            if emotion.primary == EmotionType.HAPPY:
                return f"{action} B-bukan berarti Alya senang atau apa..."
            elif emotion.primary == EmotionType.CONCERNED:
                return f"{action} B-bukan berarti Alya khawatir tentangmu..."
            elif emotion.primary == EmotionType.EMBARRASSED:
                return f"{action} J-jangan salah paham!"
        elif persona == "waifu":
            if emotion.primary == EmotionType.HAPPY:
                return f"{action} Alya senang sekali~!"
            elif emotion.primary == EmotionType.CONCERNED:
                return f"{action} Alya peduli padamu, {username}-kun..."
                
        # Default just return the action
        return action
    
    def enhance_response_with_emotion(
        self, response: str, user_id: int, persona: str = "tsundere"
    ) -> str:
        """
        Enhance a response with emotional context.
        
        Args:
            response: Original response text
            user_id: User ID for emotional context
            persona: Current persona
            
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
