"""
Database models for Alya Bot.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from database.session import Base

class User(Base):
    """User model for storing user information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    relationship_level = Column(Integer, default=0)
    relationship_progress = Column(Float, default=0.0)
    affection_points = Column(Integer, default=0)
    last_mood = Column(String, nullable=True)
    
    # Define relationships
    conversations = relationship("Conversation", back_populates="user")
    summaries = relationship("ConversationSummary", back_populates="user")

class Conversation(Base):
    """Conversation model for storing message history."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Define relationships
    user = relationship("User", back_populates="conversations")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API use."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }

class ConversationSummary(Base):
    """Summary of conversation for long-term memory."""
    
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    summary = Column(Text)
    key_topics = Column(Text)  # JSON-encoded list of topics
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Define relationships
    user = relationship("User", back_populates="summaries")
    
    def get_topics(self) -> List[str]:
        """Get key topics as list."""
        if not self.key_topics:
            return []
        return json.loads(self.key_topics)
    
    def set_topics(self, topics: List[str]) -> None:
        """Set key topics from list."""
        self.key_topics = json.dumps(topics)