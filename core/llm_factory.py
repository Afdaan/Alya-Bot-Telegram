"""
LLM provider factory for Alya Bot.
"""
import logging
from typing import Optional, Dict, Any

from config.settings import LLM_PROVIDER
from core.gemini_client import GeminiClient
from core.self_client import SelfClient

logger = logging.getLogger(__name__)

def get_llm_client() -> Any:
    """Get LLM client based on configuration.
    
    Returns:
        LLM client instance (GeminiClient or SelfClient)
    """
    provider = LLM_PROVIDER.lower()
    
    if provider == "gemini":
        logger.info("Using Gemini API as LLM provider")
        return GeminiClient()
    elif provider == "self":
        logger.info("Using self-hosted LLM as provider")
        return SelfClient()
    else:
        logger.warning(f"Unknown LLM provider '{provider}'. Falling back to Gemini.")
        return GeminiClient()
