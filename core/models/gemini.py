"""Gemini API configuration and utilities."""

import logging
from typing import Dict, Any, List
import google.generativeai as genai

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_BACKUP_API_KEYS,
    SAFETY_SETTINGS
)

logger = logging.getLogger(__name__)

def initialize_gemini() -> None:
    """Initialize Gemini API configuration."""
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API initialized")

def get_current_gemini_key() -> str:
    """Get current active Gemini API key."""
    return GEMINI_API_KEY

def convert_safety_settings() -> List[Dict[str, Any]]:
    """Convert safety settings to Gemini format."""
    return [
        {"category": category, "threshold": setting}
        for category, setting in SAFETY_SETTINGS.items()
    ]

# Initialize Gemini on module import
initialize_gemini()
