"""
Mood Management System for Alya Bot.

This module provides mood detection, tracking, and persona-driven response adaptation
for Alya's conversational context. All mood logic is centralized, deterministic, and
driven by persona YAML configuration for maintainability and natural behavior.
"""

import logging
import time
import random
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any

import yaml
from pathlib import Path

from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

MOODS_CONFIG_PATH = Path(__file__).parent.parent / "config" / "persona" / "moods.yaml"


class MoodType(Enum):
    """Enumerates all supported mood types for Alya."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    CONFUSED = "confused"
    CURIOUS = "curious"
    FLIRTY = "flirty"
    WORRIED = "worried"
    APPRECIATIVE = "appreciative"
    DEMANDING = "demanding"
    APOLOGETIC = "apologetic"
    SURPRISED = "surprised"
    EXCITED = "excited"


class MoodIntensity(Enum):
    """Defines intensity levels for moods."""
    MILD = 0.3
    MODERATE = 0.6
    STRONG = 1.0


class MoodManager:
    """
    Central manager for Alya's mood detection and persona-driven response adaptation.
    All mood triggers, decay, and persona responses are loaded from YAML config.
    """

    def __init__(self) -> None:
        self.config: Dict[str, Any] = self._load_config()
        self.mood_decay_seconds: int = self.config.get("mood_decay", {}).get("seconds", 1800)
        self.mood_decay_rate: float = self.config.get("mood_decay", {}).get("rate", 0.2)
        self.default_mood: Dict[str, float] = self.config.get("default_mood", {})
        self.mood_triggers: Dict[str, List[str]] = self.config.get("mood_triggers", {})
        self.mood_emoji: Dict[str, List[str]] = self.config.get("mood_emoji", {})
        self.persona_settings: Dict[str, Any] = self.config.get("persona_settings", {})
        self.user_moods: Dict[int, Dict[str, Any]] = {}
        self.mood_patterns: Dict[MoodType, List[str]] = self._build_mood_patterns()
        self.mood_responses: Dict[MoodType, Dict[str, List[str]]] = self.config.get("mood_responses", {})
        self.default_persona: str = "tsundere"

    def _load_config(self) -> Dict[str, Any]:
        """Load mood configuration from YAML file."""
        try:
            if not MOODS_CONFIG_PATH.exists():
                logger.error(f"Mood config file not found: {MOODS_CONFIG_PATH}")
                return {}
            with open(MOODS_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info("Mood configuration loaded successfully.")
            return config or {}
        except Exception as exc:
            logger.error(f"Error loading mood config: {exc}")
            return {}

    def _build_mood_patterns(self) -> Dict[MoodType, List[str]]:
        """
        Build mood detection patterns from YAML config.
        Patterns are used for semantic (not regex) matching.
        """
        patterns: Dict[MoodType, List[str]] = {mood: [] for mood in MoodType}
        mood_mapping = {
            "senang": MoodType.HAPPY,
            "sedih": MoodType.SAD,
            "marah": MoodType.ANGRY,
            "takut": MoodType.WORRIED,
            "malu": MoodType.FLIRTY,
        }
        for mood_name, mood_type in mood_mapping.items():
            if mood_name in self.mood_triggers:
                patterns[mood_type] = self.mood_triggers[mood_name]
        # Add default patterns for moods without config
        if not patterns[MoodType.CURIOUS]:
            patterns[MoodType.CURIOUS] = [
                "penasaran", "kenapa", "gimana", "mengapa", "bagaimana", "apa itu", "curious", "why", "how"
            ]
        if not patterns[MoodType.CONFUSED]:
            patterns[MoodType.CONFUSED] = [
                "bingung", "tidak paham", "gak jelas", "confused", "don't understand", "weird"
            ]
        if not patterns[MoodType.APPRECIATIVE]:
            patterns[MoodType.APPRECIATIVE] = [
                "makasih", "terima kasih", "thanks", "appreciate", "grateful"
            ]
        if not patterns[MoodType.DEMANDING]:
            patterns[MoodType.DEMANDING] = [
                "cepat", "harus", "wajib", "sekarang", "buruan", "must", "do it", "now", "urgent"
            ]
        return patterns

    def detect_mood(self, message: str) -> Tuple[MoodType, MoodIntensity]:
        """
        Detect the mood from a user message using semantic matching.
        Args:
            message: User's message text
        Returns:
            Tuple of detected mood type and intensity
        """
        if not message:
            return MoodType.NEUTRAL, MoodIntensity.MILD
        message_lower = message.lower()
        mood_scores: Dict[MoodType, int] = {mood: 0 for mood in MoodType}
        for mood, keywords in self.mood_patterns.items():
            for keyword in keywords:
                if keyword in message_lower:
                    mood_scores[mood] += 1
        max_score = max(mood_scores.values())
        if max_score == 0:
            return MoodType.NEUTRAL, MoodIntensity.MILD
        top_moods = [mood for mood, score in mood_scores.items() if score == max_score]
        detected_mood = random.choice(top_moods)
        if max_score >= 3:
            intensity = MoodIntensity.STRONG
        elif max_score == 2:
            intensity = MoodIntensity.MODERATE
        else:
            intensity = MoodIntensity.MILD
        return detected_mood, intensity

    def get_user_mood(self, user_id: int) -> Dict[str, float]:
        """
        Get user's current mood with decay applied.
        Args:
            user_id: User ID
        Returns:
            Dictionary of mood values after decay
        """
        if user_id not in self.user_moods:
            self.user_moods[user_id] = {
                "moods": self.default_mood.copy(),
                "timestamp": time.time(),
            }
            return self.default_mood.copy()
        user_mood_data = self.user_moods[user_id]
        last_update = user_mood_data.get("timestamp", 0)
        current_time = time.time()
        time_delta = current_time - last_update
        if time_delta > 60:
            decay_minutes = time_delta / 60
            decay_factor = self.mood_decay_rate * decay_minutes
            current_moods = user_mood_data["moods"].copy()
            for mood_name, mood_value in current_moods.items():
                default_value = self.default_mood.get(mood_name, 0.0)
                if mood_value > default_value:
                    new_value = max(default_value, mood_value - decay_factor)
                elif mood_value < default_value:
                    new_value = min(default_value, mood_value + decay_factor)
                else:
                    new_value = default_value
                current_moods[mood_name] = new_value
            self.user_moods[user_id] = {
                "moods": current_moods,
                "timestamp": current_time,
            }
            return current_moods
        return user_mood_data["moods"]

    def update_user_mood(self, user_id: int, detected_mood: MoodType, intensity: MoodIntensity) -> None:
        """
        Update user's mood based on detected mood.
        Args:
            user_id: User ID
            detected_mood: Detected mood type
            intensity: Mood intensity
        """
        current_moods = self.get_user_mood(user_id)
        mood_mapping = {
            MoodType.HAPPY: "senang",
            MoodType.SAD: "sedih",
            MoodType.ANGRY: "marah",
            MoodType.WORRIED: "takut",
            MoodType.FLIRTY: "malu",
        }
        mood_name = mood_mapping.get(detected_mood)
        if not mood_name or mood_name not in current_moods:
            return
        intensity_value = intensity.value
        if mood_name in ("senang", "malu"):
            current_moods[mood_name] = min(1.0, current_moods[mood_name] + (intensity_value * 0.3))
        else:
            current_moods[mood_name] = min(1.0, current_moods[mood_name] + (intensity_value * 0.2))
        self.user_moods[user_id] = {
            "moods": current_moods,
            "timestamp": time.time(),
        }

    def get_dominant_mood(self, moods: Dict[str, float]) -> str:
        """
        Get the dominant mood from mood values.
        Args:
            moods: Dictionary of mood values
        Returns:
            Name of dominant mood
        """
        max_mood = max(moods.items(), key=lambda x: abs(x[1]))
        mood_name, mood_value = max_mood
        if abs(mood_value) < 0.2:
            return "neutral"
        return mood_name

    def get_mood_emoji(self, mood_name: str) -> str:
        """
        Get random emoji for a mood.
        Args:
            mood_name: Name of the mood
        Returns:
            Random emoji for the mood or empty string
        """
        emoji_list = self.mood_emoji.get(mood_name, [])
        return random.choice(emoji_list) if emoji_list else ""

    def get_mood_response(
        self,
        mood: MoodType,
        intensity: MoodIntensity,
        persona: str = "tsundere",
        username: str = "Senpai",
    ) -> Optional[str]:
        """
        Get an appropriate mood-based response.
        Args:
            mood: Detected mood type
            intensity: Mood intensity
            persona: Persona type (tsundere, waifu, etc.)
            username: User's name for personalization
        Returns:
            Mood-appropriate response or None if no matching response
        """
        persona = persona if persona in ["tsundere", "waifu"] else self.default_persona
        if mood not in self.mood_responses:
            return None
        if persona not in self.mood_responses[mood]:
            persona = self.default_persona
            if persona not in self.mood_responses[mood]:
                return None
        responses = self.mood_responses[mood][persona]
        if not responses:
            return None
        response = random.choice(responses)
        response = response.replace("{username}", username)
        mood_mapping = {
            MoodType.HAPPY: "senang",
            MoodType.SAD: "sedih",
            MoodType.ANGRY: "marah",
            MoodType.WORRIED: "takut",
            MoodType.FLIRTY: "malu",
        }
        mood_name = mood_mapping.get(mood)
        if mood_name and random.random() < intensity.value:
            emoji = self.get_mood_emoji(mood_name)
            if emoji and " " in response:
                parts = response.split(" ")
                insert_pos = random.randint(1, len(parts) - 1)
                parts.insert(insert_pos, emoji)
                response = " ".join(parts)
        return response

    def format_response_with_mood(
        self,
        ai_response: str,
        user_message: str,
        persona: str = "tsundere",
        username: str = "Senpai",
        user_id: Optional[int] = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> str:
        """
        Format a response with mood-appropriate additions.
        Args:
            ai_response: Original AI response
            user_message: User's message for mood detection
            persona: Current persona
            username: User's name
            user_id: Optional user ID for mood tracking
            language: Language code for response formatting
        Returns:
            Response with mood-appropriate formatting
        """
        mood, intensity = self.detect_mood(user_message)
        if user_id is not None:
            self.update_user_mood(user_id, mood, intensity)
        if mood != MoodType.NEUTRAL and intensity != MoodIntensity.MILD:
            mood_response = self.get_mood_response(mood, intensity, persona, username)
            if mood_response:
                if intensity == MoodIntensity.STRONG or random.random() < 0.7:
                    if mood in [MoodType.SAD, MoodType.WORRIED, MoodType.ANGRY]:
                        result = f"{mood_response}\n\n{ai_response}"
                    else:
                        result = f"{ai_response}\n\n{mood_response}"
                    return result
        return ai_response


# Singleton instance for global use
mood_manager = MoodManager()


def get_mood_response(
    message: str, persona: str = "tsundere", username: str = "Senpai"
) -> Optional[str]:
    """
    Get mood-appropriate response for a message (convenience function).
    Args:
        message: User's message
        persona: Current persona
        username: User's name
    Returns:
        Mood-appropriate response or None
    """
    mood, intensity = mood_manager.detect_mood(message)
    return mood_manager.get_mood_response(mood, intensity, persona, username)


def format_with_mood(
    ai_response: str,
    user_message: str,
    persona: str = "tsundere",
    username: str = "Senpai",
    user_id: Optional[int] = None,
) -> str:
    """
    Format response with mood (convenience function).
    Args:
        ai_response: Original AI response
        user_message: User's message
        persona: Current persona
        username: User's name
        user_id: Optional user ID for mood tracking
    Returns:
        Formatted response
    """
    return mood_manager.format_response_with_mood(
        ai_response, user_message, persona, username, user_id
    )


def get_user_mood(user_id: int) -> Dict[str, float]:
    """
    Get user's current mood with decay (convenience function).
    Args:
        user_id: User ID
    Returns:
        Dictionary of mood values
    """
    return mood_manager.get_user_mood(user_id)


def get_dominant_mood(user_id: int) -> str:
    """
    Get user's dominant mood (convenience function).
    Args:
        user_id: User ID
    Returns:
        Name of dominant mood
    """
    moods = mood_manager.get_user_mood(user_id)
    return mood_manager.get_dominant_mood(moods)


def update_user_mood(user_id: int, message: str) -> None:
    """
    Update user's mood based on their message (convenience function).
    Args:
        user_id: User ID
        message: User's message text
    """
    detected_mood, intensity = mood_manager.detect_mood(message)
    if detected_mood != MoodType.NEUTRAL:
        mood_manager.update_user_mood(user_id, detected_mood, intensity)