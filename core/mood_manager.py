"""Dynamic Mood System for Alya Bot."""

import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

VALID_MOODS = ["happy", "tsundere", "affectionate", "neutral", "annoyed", "sad"]

MOOD_DECAY_RATES = {
    "happy": 0.15,
    "tsundere": 0.10,
    "affectionate": 0.08,
    "neutral": 0.0,
    "annoyed": 0.20,
    "sad": 0.12
}

MOOD_AFFECTION_MODIFIERS = {
    "happy": 1.2,
    "tsundere": 1.0,
    "affectionate": 1.3,
    "neutral": 1.0,
    "annoyed": 1.5,
    "sad": 0.8
}

MOOD_TRANSITION_THRESHOLD = 8
MOOD_INTENSITY_MIN = 20
MOOD_INTENSITY_MAX = 100

@dataclass
class MoodState:
    mood: str
    intensity: int
    last_change: datetime
    trigger_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mood": self.mood,
            "intensity": self.intensity,
            "last_change": self.last_change.isoformat(),
            "trigger_reason": self.trigger_reason
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoodState':
        return cls(
            mood=data.get("mood", "neutral"),
            intensity=data.get("intensity", 50),
            last_change=datetime.fromisoformat(data.get("last_change", datetime.now().isoformat())),
            trigger_reason=data.get("trigger_reason", "")
        )

class MoodManager:
    def __init__(self):
        self.mood_history_limit = 10
    
    def calculate_mood(
        self,
        current_mood: str,
        current_intensity: int,
        affection_delta: int,
        emotion_context: Dict[str, Any],
        relationship_level: int,
        last_mood_change: datetime
    ) -> MoodState:
        decayed_mood, decayed_intensity = self._apply_mood_decay(
            current_mood, 
            current_intensity, 
            last_mood_change
        )
        
        new_mood, new_intensity, trigger = self._determine_mood_transition(
            current_mood=decayed_mood,
            current_intensity=decayed_intensity,
            affection_delta=affection_delta,
            emotion_context=emotion_context,
            relationship_level=relationship_level
        )
        
        new_intensity = max(MOOD_INTENSITY_MIN, min(MOOD_INTENSITY_MAX, new_intensity))
        
        return MoodState(
            mood=new_mood,
            intensity=new_intensity,
            last_change=datetime.now() if new_mood != current_mood else last_mood_change,
            trigger_reason=trigger
        )
    
    def _apply_mood_decay(
        self, 
        mood: str, 
        intensity: int, 
        last_change: datetime
    ) -> Tuple[str, int]:
        if mood == "neutral":
            return mood, 50
        
        hours_elapsed = (datetime.now() - last_change).total_seconds() / 3600
        decay_rate = MOOD_DECAY_RATES.get(mood, 0.1)
        decay_amount = int(decay_rate * hours_elapsed * 10)
        new_intensity = intensity - decay_amount
        
        if new_intensity < MOOD_INTENSITY_MIN:
            return "neutral", 50
        
        return mood, new_intensity
    
    def _determine_mood_transition(
        self,
        current_mood: str,
        current_intensity: int,
        affection_delta: int,
        emotion_context: Dict[str, Any],
        relationship_level: int
    ) -> Tuple[str, int, str]:
        emotion = emotion_context.get("emotion", "neutral")
        intent = emotion_context.get("intent", "")
        signals = emotion_context.get("relationship_signals", {})
        
        new_mood = current_mood
        new_intensity = current_intensity
        trigger = ""
        
        if affection_delta >= 10:
            if relationship_level >= 3:
                new_mood = "affectionate"
                new_intensity = min(80, current_intensity + 20)
                trigger = "strong_positive_interaction"
            elif relationship_level >= 1:
                new_mood = "happy"
                new_intensity = min(75, current_intensity + 15)
                trigger = "positive_interaction"
            else:
                if intent in ["compliment", "affection", "romantic_interest"]:
                    new_mood = "tsundere"
                    new_intensity = min(70, current_intensity + 15)
                    trigger = "embarrassed_by_compliment"
                else:
                    new_mood = "happy"
                    new_intensity = min(70, current_intensity + 10)
                    trigger = "pleasant_interaction"
        
        elif affection_delta >= 5:
            if signals.get("romantic_interest", 0) > 0.5 and relationship_level < 2:
                new_mood = "tsundere"
                new_intensity = min(65, current_intensity + 10)
                trigger = "romantic_signal_detected"
            else:
                new_mood = "happy"
                new_intensity = min(70, current_intensity + 10)
                trigger = "good_interaction"
        
        # New block: Handle lighter positive emotions (amusement, optimism, etc.) even with low affection delta
        elif affection_delta > 0 and emotion in ["amusement", "optimism", "relief", "pride", "caring", "approval", "happy", "joy"]:
             new_mood = "happy"
             new_intensity = min(65, current_intensity + 5)
             trigger = f"positive_emotion_{emotion}"
        
        elif affection_delta <= -8:
            if intent in ["insult", "toxic_behavior", "rudeness"]:
                new_mood = "annoyed"
                new_intensity = min(85, current_intensity + 25)
                trigger = "insulted_or_toxic"
            else:
                new_mood = "sad"
                new_intensity = min(70, current_intensity + 15)
                trigger = "hurt_feelings"
        
        elif affection_delta <= -3:
            new_mood = "annoyed"
            new_intensity = min(65, current_intensity + 10)
            trigger = "negative_interaction"
        
        if emotion in ["sad", "worried", "disappointed"] and affection_delta >= 0:
            new_mood = "affectionate"
            new_intensity = min(70, current_intensity + 10)
            trigger = "user_needs_comfort"
        
        if current_mood == "annoyed" and intent in ["gratitude", "apology"]:
            new_mood = "neutral"
            new_intensity = 50
            trigger = "user_apologized"
        
        return new_mood, new_intensity, trigger
    
    def get_affection_modifier(self, mood: str, affection_delta: int) -> float:
        base_modifier = MOOD_AFFECTION_MODIFIERS.get(mood, 1.0)
        
        if mood == "affectionate" and affection_delta < 0:
            return 0.5
        
        if mood == "annoyed" and affection_delta < 0:
            return 1.8
        
        return base_modifier
    
    def get_mood_prompt_modifier(self, mood: str, intensity: int, lang: str = "en") -> str:
        if intensity >= 80:
            intensity_desc = "very strong"
        elif intensity >= 60:
            intensity_desc = "strong"
        elif intensity >= 40:
            intensity_desc = "moderate"
        else:
            intensity_desc = "mild"
        
        mood_prompts = {
            "happy": f"You're in a {intensity_desc} cheerful mood. Be playful, energetic, and use cute Russian expressions. Show your happiness through your words and tone.",
            "tsundere": f"You're feeling {intensity_desc} tsundere (defensive and embarrassed). Act defensive when complimented, deny your feelings while showing you care. Use expressions like 'бака' (baka) when flustered. Be contradictory - say one thing but mean another.",
            "affectionate": f"You're in a {intensity_desc} warm and caring mood. Show genuine affection and tenderness. Use romantic Russian expressions. Be supportive and loving, but still maintain your personality.",
            "neutral": "You're in a balanced, normal mood. Respond naturally without strong emotional coloring.",
            "annoyed": f"You're {intensity_desc} irritated. Be sharp, sarcastic, and use harsh Russian expressions like 'дурак' (durak) or 'сука' (suka). Show your annoyance but don't be cruel.",
            "sad": f"You're feeling {intensity_desc} down or melancholic. Be vulnerable, seek comfort, and show your softer side. Use gentle Russian expressions. It's okay to show weakness."
        }
        
        base_prompt = mood_prompts.get(mood, mood_prompts["neutral"])
        
        return f"\n\n**CURRENT MOOD: {mood.upper()} (Intensity: {intensity}/100)**\n{base_prompt}"
    
    def get_mood_russian_expressions(self, mood: str) -> List[str]:
        mood_expressions = {
            "happy": ["рада", "хорошо", "милый", "спасибо", "да", "конечно"],
            "tsundere": ["бака", "дурак", "что", "ну", "не", "ладно"],
            "affectionate": ["люблю", "милый", "красивый", "спасибо", "моя", "мой"],
            "neutral": ["да", "нет", "хорошо", "может", "ладно", "понимаешь"],
            "annoyed": ["сука", "дурак", "гадость", "нет", "что ты делаешь", "ненавижу"],
            "sad": ["боюсь", "извини", "плохо", "грустный", "боже", "может"]
        }
        return mood_expressions.get(mood, mood_expressions["neutral"])
    
    def add_to_mood_history(
        self, 
        mood_history: List[Dict[str, Any]], 
        new_mood_state: MoodState
    ) -> List[Dict[str, Any]]:
        mood_entry = new_mood_state.to_dict()
        updated_history = mood_history.copy() if mood_history else []
        updated_history.append(mood_entry)
        
        if len(updated_history) > self.mood_history_limit:
            updated_history = updated_history[-self.mood_history_limit:]
        
        return updated_history
    
    def validate_mood(self, mood: str) -> bool:
        return mood in VALID_MOODS
