"""
SQLAlchemy models for database storage.
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    """User model for storing user information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="id")
    last_interaction = Column(DateTime, default=datetime.now)
    
    # Stored as JSON in db
    preferences = Column(JSON, default=lambda: {})
    topics_discussed = Column(JSON, default=lambda: [])
    relationship_score = Column(Integer, default=0)
    
    def __repr__(self) -> str:
        """String representation of User object."""
        return f"<User(id={self.id}, username={self.username})>"


class Conversation(Base):
    """Model for storing conversation history."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True)  # True for user messages, False for bot
    timestamp = Column(DateTime, default=datetime.now)
    
    # Stored as JSON in db - holds emotions, topics, etc.
    metadata = Column(JSON, default=lambda: {})
    
    def __repr__(self) -> str:
        """String representation of Conversation object."""
        sender = "User" if self.is_user else "Bot"
        return f"<Conversation(id={self.id}, user_id={self.user_id}, sender={sender})>"


class ConversationSummary(Base):
    """Model for storing summarized conversation history."""
    
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)  # The summarized content
    message_count = Column(Integer, default=0)  # How many messages were summarized
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self) -> str:
        """String representation of ConversationSummary object."""
        return f"<ConversationSummary(id={self.id}, user_id={self.user_id})>"
