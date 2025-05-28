"""
SQLAlchemy models for the Alya bot database.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, synonym


from database.session import Base

class User(Base):
    """User model for storing user information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="id")
    last_interaction = Column(DateTime, default=datetime.now)
    
    preferences = Column(JSON, default=lambda: {})
    topics_discussed = Column(JSON, default=lambda: [])
    relationship_level = Column(Integer, default=0)
    
    def __repr__(self) -> str:
        """String representation of User object."""
        return f"<User(id={self.id}, username={self.username})>"

class Conversation(Base):
    """Model for storing conversation messages."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    content = Column(Text, nullable=False)  # Use 'content' as it exists in DB
    is_user = Column(Boolean, default=True)
    # Renamed 'metadata' to 'message_metadata' to avoid conflict with SQLAlchemy's reserved name
    message_metadata = Column(Text, default="{}")  # JSON stored as text
    timestamp = Column(DateTime, default=datetime.now)
    
    # Make message a synonym for content (reverse mapping)
    message = synonym('content')
    
    # Simple mapper args without complexity
    __mapper_args__ = {
        'polymorphic_identity': 'conversation'
    }
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as parsed dict."""
        try:
            return json.loads(self.message_metadata) if self.message_metadata else {}
        except json.JSONDecodeError:
            return {}
    
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata from dict."""
        self.message_metadata = json.dumps(metadata) if metadata else "{}"

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
