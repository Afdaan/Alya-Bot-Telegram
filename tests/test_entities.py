"""
Test domain entities.
"""
import pytest
from datetime import datetime

from app.domain.entities import User, Message, RelationshipLevel, EmotionType


def test_user_creation():
    """Test user entity creation."""
    user = User(
        id=12345,
        username="test_user",
        first_name="Test",
        last_name="User",
        language_code="id"
    )
    
    assert user.id == 12345
    assert user.username == "test_user"
    assert user.first_name == "Test"
    assert user.relationship_level == RelationshipLevel.STRANGER
    assert user.affection_points == 0
    assert user.is_admin is False


def test_message_creation():
    """Test message entity creation."""
    message = Message(
        user_id=12345,
        content="Hello Alya!",
        role="user",
        emotion=EmotionType.HAPPY,
        sentiment_score=0.8
    )
    
    assert message.user_id == 12345
    assert message.content == "Hello Alya!"
    assert message.role == "user"
    assert message.emotion == EmotionType.HAPPY
    assert message.sentiment_score == 0.8


def test_relationship_levels():
    """Test relationship level enum."""
    assert RelationshipLevel.STRANGER.value == 0
    assert RelationshipLevel.ACQUAINTANCE.value == 1
    assert RelationshipLevel.FRIEND.value == 2
    assert RelationshipLevel.CLOSE_FRIEND.value == 3
    assert RelationshipLevel.INTIMATE.value == 4


def test_emotion_types():
    """Test emotion type enum."""
    emotions = [
        EmotionType.HAPPY,
        EmotionType.SAD,
        EmotionType.ANGRY,
        EmotionType.SURPRISED,
        EmotionType.FEARFUL,
        EmotionType.DISGUSTED,
        EmotionType.NEUTRAL
    ]
    
    assert len(emotions) == 7
    assert EmotionType.NEUTRAL.value == "neutral"
