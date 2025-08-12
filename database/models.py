"""Enterprise-grade SQLAlchemy models for Alya Bot MySQL database."""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Index, BigInteger, SmallInteger
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.dialects.mysql import LONGTEXT, MEDIUMTEXT

from database.session import Base


class User(Base):
    """User model for storing Telegram user information with relationship tracking."""
    
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(32), nullable=True, index=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    language_code = Column(String(10), default="id", index=True)
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    last_interaction = Column(DateTime, default=datetime.now, index=True)
    
    is_active = Column(Boolean, default=True, index=True)
    is_banned = Column(Boolean, default=False, index=True)
    ban_reason = Column(String(500), nullable=True)
    
    preferences = Column(JSON, default=lambda: {
        "notification_enabled": True,
        "persona": "waifu",
        "timezone": "Asia/Jakarta"
    })
    
    relationship_level = Column(SmallInteger, default=0, index=True)
    affection_points = Column(Integer, default=0)
    interaction_count = Column(Integer, default=0, index=True)
    topics_discussed = Column(JSON, default=lambda: [])
    
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    summaries = relationship("ConversationSummary", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_active_interaction', 'is_active', 'last_interaction'),
        Index('idx_user_relationship_level', 'relationship_level', 'affection_points'),
        Index('idx_user_stats', 'interaction_count', 'relationship_level'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, level={self.relationship_level})>"
    
    def get_display_name(self) -> str:
        if self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.id}"


class Conversation(Base):
    """Enhanced conversation model with analytics and RAG support."""
    
    __tablename__ = "conversations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    content = Column(MEDIUMTEXT, nullable=False)
    role = Column(String(20), default='user', index=True)
    
    message_type = Column(String(20), default='text', index=True)
    is_user = Column(Boolean, default=True, index=True)
    message_hash = Column(String(32), index=True)
    
    message_metadata = Column(JSON, default=lambda: {})
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    sentiment_score = Column(SmallInteger, nullable=True)
    toxicity_score = Column(SmallInteger, nullable=True)
    emotion_category = Column(String(20), nullable=True, index=True)
    
    processed_for_rag = Column(Boolean, default=False, index=True)
    embedding_id = Column(String(64), nullable=True, index=True)
    
    user = relationship("User", back_populates="conversations")
    
    message = synonym('content')
    timestamp = synonym('created_at')
    
    __table_args__ = (
        Index('idx_conv_user_created', 'user_id', 'created_at'),
        Index('idx_conv_user_role', 'user_id', 'role'),
        Index('idx_conv_type_sentiment', 'message_type', 'sentiment_score'),
        Index('idx_conv_processed_rag', 'processed_for_rag', 'created_at'),
        Index('idx_conv_emotion', 'emotion_category', 'created_at'),
        Index('idx_conv_dedup', 'user_id', 'message_hash', 'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Conversation(id={self.id}, user_id={self.user_id}, role={self.role}, content='{content_preview}')>"
    
    def get_metadata(self) -> Dict[str, Any]:
        try:
            return self.message_metadata if isinstance(self.message_metadata, dict) else {}
        except (TypeError, ValueError):
            return {}
    
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        self.message_metadata = metadata if metadata else {}
    
    def is_recent(self, minutes: int = 5) -> bool:
        from datetime import timedelta
        return (datetime.now() - self.created_at) <= timedelta(minutes=minutes)


class ConversationSummary(Base):
    """Model for storing AI-generated conversation summaries for long-term memory."""
    
    __tablename__ = "conversation_summaries"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete='CASCADE'), nullable=False, index=True)
    
    content = Column(LONGTEXT, nullable=False)
    summary_type = Column(String(20), default='auto', index=True)
    
    message_count = Column(Integer, default=0)
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    
    model_used = Column(String(50), nullable=True)
    summary_metadata = Column(JSON, default=lambda: {})
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    user = relationship("User", back_populates="summaries")
    
    __table_args__ = (
        Index('idx_summary_user_created', 'user_id', 'created_at'),
        Index('idx_summary_type_date', 'summary_type', 'created_at'),
        Index('idx_summary_date_range', 'date_range_start', 'date_range_end'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:100] + "..." if len(self.content) > 100 else self.content
        return f"<ConversationSummary(id={self.id}, user_id={self.user_id}, messages={self.message_count}, content='{content_preview}')>"
    
    def get_summary_metadata(self) -> Dict[str, Any]:
        try:
            return self.summary_metadata if isinstance(self.summary_metadata, dict) else {}
        except (TypeError, ValueError):
            return {}


class ApiUsage(Base):
    """Model for tracking API usage and costs."""
    
    __tablename__ = "api_usage"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete='CASCADE'), nullable=True, index=True)
    
    api_provider = Column(String(20), nullable=False, index=True)
    api_method = Column(String(50), nullable=False)
    model_name = Column(String(50), nullable=True)
    
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    estimated_cost_cents = Column(Integer, default=0)
    
    request_metadata = Column(JSON, default=lambda: {})
    response_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    __table_args__ = (
        Index('idx_usage_provider_date', 'api_provider', 'created_at'),
        Index('idx_usage_user_provider', 'user_id', 'api_provider'),
        Index('idx_usage_cost_tracking', 'estimated_cost_cents', 'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )
    
    def __repr__(self) -> str:
        return f"<ApiUsage(id={self.id}, provider={self.api_provider}, user_id={self.user_id}, cost={self.estimated_cost_cents}¢>"
