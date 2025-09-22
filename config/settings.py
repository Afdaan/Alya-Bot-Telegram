"""
Settings and configuration management for Alya Bot v2.
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Bot Configuration
    telegram_bot_token: str = Field(..., description="Telegram Bot Token")
    gemini_api_key: str = Field(..., description="Google Gemini API Key")
    bot_name: str = Field(default="Alya", description="Bot name")
    command_prefix: str = Field(default="!ai", description="Command prefix")
    default_language: str = Field(default="id", description="Default language (id/en)")
    
    # Database Configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=3306, description="Database port")
    db_user: str = Field(default="alya_bot", description="Database user")
    db_password: str = Field(..., description="Database password")
    db_name: str = Field(default="alya_bot_v2", description="Database name")
    
    # HuggingFace Models
    sentiment_model: str = Field(
        default="cardiffnlp/twitter-roberta-base-sentiment-latest",
        description="HuggingFace sentiment model"
    )
    emotion_model: str = Field(
        default="j-hartmann/emotion-english-distilroberta-base",
        description="HuggingFace emotion model"
    )
    
    # Memory System
    max_memory_messages: int = Field(default=100, description="Maximum messages in memory")
    sliding_window_size: int = Field(default=10, description="Sliding window size")
    rag_max_results: int = Field(default=5, description="Maximum RAG results")
    # Rate Limiting
    max_requests_per_minute: int = Field(default=60, description="Rate limit per minute")
    max_message_length: int = Field(default=4000, description="Maximum message length")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Development
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment")
    
    @property
    def database_url(self) -> str:
        """Get database URL for SQLAlchemy."""
        return (
            f"mysql+mysqlconnector://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev", "local")


# Global settings instance
settings = Settings()
