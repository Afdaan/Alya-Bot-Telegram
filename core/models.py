"""
Re-export file for backward compatibility.
All core model functionality has been moved to the models/ folder.

This file acts as a bridge to maintain backwards compatibility while allowing
better code organization in the models/ directory. It re-exports commonly used
functions and provides deprecation warnings for old import patterns.

Note: New code should import directly from core.models.{module} instead.
"""

import logging
import warnings
from typing import Dict, Any, Optional, Union

from core.models.chat import get_chat_response, generate_response, generate_chat_response
from core.models.gemini import (
    initialize_gemini,
    get_current_gemini_key,
    convert_safety_settings,
    generate_image_analysis,
    generate_text_analysis
)
from core.models.safety import check_content_safety
from utils.rate_limiter import gemini_limiter

# Setup logger
logger = logging.getLogger(__name__)

# Maintain commonly used exports
__all__ = [
    'get_chat_response',
    'generate_response',
    'generate_chat_response',
    'initialize_gemini',
    'get_current_gemini_key', 
    'convert_safety_settings',
    'generate_image_analysis',
    'generate_text_analysis',
    'check_content_safety',
]

# Show deprecation warnings for direct imports
def __getattr__(name: str) -> Any:
    """Handle deprecated direct imports with warning."""
    if name in globals():
        warnings.warn(
            f"Direct import from core.models is deprecated. "
            f"Use core.models.chat or core.models.gemini instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return globals()[name]
    raise AttributeError(f"module 'core.models' has no attribute '{name}'")

# Backwards compatibility for old function calls
async def generate_chat_response(
    message: str,
    user_id: int,
    persona_context: Optional[str] = None,
    language: Optional[str] = None
) -> str:
    """
    Legacy wrapper for generate_response.
    
    Args:
        message: User message to respond to
        user_id: User ID for context
        persona_context: Optional persona context
        language: Optional language code
        
    Returns:
        Generated response text
        
    Note:
        This function is deprecated. Use core.models.chat.generate_response instead.
    """
    warnings.warn(
        "generate_chat_response is deprecated. Use generate_response from core.models.chat",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Apply rate limiting
    allowed, wait_time = await gemini_limiter.acquire_with_feedback(user_id)
    if not allowed:
        return f"Rate limit exceeded. Please wait {wait_time:.1f} seconds."
    
    try:
        # Handle legacy calls by adapting to new interface
        from core.models.chat import generate_response
        return await generate_response(
            message=message,
            username=None,  # Will be fetched from context
            user_id=user_id,
            context_data={
                "persona": persona_context,
                "language": language
            }
        )
    except Exception as e:
        logger.error(f"Error in legacy generate_chat_response: {e}")
        return f"Error generating response: {str(e)[:100]}..."

# Initialize required components
def init_models() -> None:
    """Initialize all model components."""
    try:
        # Initialize Gemini
        initialize_gemini()
        logger.info("Models initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing models: {e}")
        raise

# Run initialization when module is imported
init_models()