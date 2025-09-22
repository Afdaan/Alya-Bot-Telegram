"""
Domain entities for Alya Bot v2.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class EmotionType(str, Enum):
    """Emotion types for sentiment analysis."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"


class RelationshipLevel(int, Enum):
    """Relationship progression levels."""
    STRANGER = 0
    ACQUAINTANCE = 1
    FRIEND = 2
    CLOSE_FRIEND = 3
    INTIMATE = 4


@dataclass
class User:
    """User domain entity."""
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "id"
    relationship_level: RelationshipLevel = RelationshipLevel.STRANGER
    affection_points: int = 0
    interaction_count: int = 0
    is_admin: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Message domain entity."""
    id: Optional[int] = None
    user_id: int = 0
    content: str = ""
    role: str = "user"  # user, assistant, system
    emotion: Optional[EmotionType] = None
    sentiment_score: Optional[float] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Conversation context for RAG system."""
    user_id: int
    messages: List[Message] = field(default_factory=list)
    current_emotion: Optional[EmotionType] = None
    topics: List[str] = field(default_factory=list)
    relationship_level: RelationshipLevel = RelationshipLevel.STRANGER
    summary: Optional[str] = None


@dataclass
class PersonaConfig:
    """Persona configuration from YAML."""
    name: str
    base_instructions: Dict[str, str] = field(default_factory=dict)
    personality_traits: Dict[str, List[str]] = field(default_factory=dict)
    relationship_levels: Dict[str, List[str]] = field(default_factory=dict)
    response_formats: Dict[str, str] = field(default_factory=dict)
    russian_phrases: Dict[str, Dict[str, str]] = field(default_factory=dict)
    emotion_responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AIResponse:
    """AI model response."""
    content: str
    emotion: Optional[EmotionType] = None
    confidence: float = 0.0
    tokens_used: int = 0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
