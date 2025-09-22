"""
Database models using SQLAlchemy.
"""
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime, 
    Boolean, JSON, Float, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

Base = declarative_base()


class UserModel(Base):
    """User table model."""
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(64), nullable=True, index=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    language_code = Column(String(10), default="id", index=True)
    
    relationship_level = Column(Integer, default=0, index=True)
    affection_points = Column(Integer, default=0)
    interaction_count = Column(Integer, default=0)
    
    is_admin = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_interaction = Column(DateTime, default=datetime.utcnow, index=True)
    
    preferences = Column(JSON, default=lambda: {})
    
    __table_args__ = (
        Index('idx_user_activity', 'is_active', 'last_interaction'),
        Index('idx_user_relationship', 'relationship_level', 'affection_points'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class MessageModel(Base):
    """Message table model."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False, index=True)  # user, assistant, system
    
    emotion = Column(String(20), nullable=True, index=True)
    sentiment_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(JSON, default=lambda: {})
    
    __table_args__ = (
        Index('idx_message_user_time', 'user_id', 'created_at'),
        Index('idx_message_role_time', 'role', 'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class ConversationContextModel(Base):
    """Conversation context for RAG system."""
    __tablename__ = "conversation_contexts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    topics = Column(JSON, default=lambda: [])
    emotion = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    metadata = Column(JSON, default=lambda: {})
    
    __table_args__ = (
        Index('idx_context_user_time', 'user_id', 'updated_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class MemoryEmbeddingModel(Base):
    """Vector embeddings for RAG memory."""
    __tablename__ = "memory_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding_vector = Column(JSON, nullable=False)  # Store as JSON array
    
    message_id = Column(Integer, nullable=True, index=True)
    context_id = Column(Integer, nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(JSON, default=lambda: {})
    
    __table_args__ = (
        Index('idx_embedding_user', 'user_id'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


# Database setup
def create_database_engine():
    """Create database engine."""
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.debug
    )
    return engine


def create_session_factory():
    """Create session factory."""
    engine = create_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def create_tables():
    """Create all tables."""
    engine = create_database_engine()
    Base.metadata.create_all(bind=engine)
