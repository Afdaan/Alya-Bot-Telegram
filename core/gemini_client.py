"""
Gemini API client for Alya Bot with key rotation.
"""
import logging
import random
import time
import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Any, Tuple

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.types.generation_types import GenerationConfig

from config.settings import (
    GEMINI_API_KEYS, GEMINI_MODEL, MAX_OUTPUT_TOKENS,
    TEMPERATURE, TOP_K, TOP_P
)

logger = logging.getLogger(__name__)
class GeminiClient:
    """A client for interacting with Google's Gemini API with key rotation."""

    def __init__(self) -> None:
        """Initialize the Gemini client with API keys."""
        self.api_keys: List[str] = GEMINI_API_KEYS.copy()
        self.current_key_index: int = 0
        self.model: str = GEMINI_MODEL
        self.working_keys: List[str] = []
        self._initialize_client()
        
    def _initialize_client(self) -> None:
        """Initialize the Gemini client with the current API key."""
        if not self.api_keys:
            logger.error("No Gemini API keys available")
            return
            
        # Start with a random key for better distribution
        self.current_key_index = random.randint(0, len(self.api_keys) - 1)
        self._configure_client()
        
    def _configure_client(self) -> None:
        """Configure the Gemini client with the current API key."""
        if not self.api_keys:
            logger.error("No Gemini API keys available")
            return
            
        try:
            current_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=current_key)
            self.working_keys = self.api_keys.copy()
            logger.info(f"Configured Gemini client with API key index {self.current_key_index}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            
    def _rotate_key(self) -> bool:
        """Rotate to the next available API key."""
        if not self.api_keys:
            logger.error("No API keys available for rotation")
            return False
            
        # Try each key until we find a working one or exhaust all options
        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            try:
                current_key = self.api_keys[self.current_key_index]
                genai.configure(api_key=current_key)
                logger.info(f"Rotated to API key index {self.current_key_index}")
                return True
            except Exception as e:
                logger.error(f"Failed to rotate to API key index {self.current_key_index}: {e}")
                
        logger.critical("All Gemini API keys have failed")
        return False
        
    async def generate_content(
        self, 
        user_input: str, 
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        safe_mode: bool = False
    ) -> Optional[str]:
        """
        Generate content using Gemini API with automatic key rotation.
        
        Args:
            user_input: The user's input message
            system_prompt: System prompt with persona instructions
            history: Optional conversation history
            safe_mode: Whether to use Google's default safety settings
            
        Returns:
            Generated response text or None if generation failed
        """
        if not self.api_keys:
            logger.error("No Gemini API keys available")
            return None
            
        # Prepare generation config
        generation_config = GenerationConfig(
            temperature=TEMPERATURE,
            top_p=TOP_P,
            top_k=TOP_K,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        
        # Use our custom safety settings by default
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # If safe_mode is explicitly requested, use Google's default safety settings
        if safe_mode:
            safety_settings = None
            
        # Try to generate content, with key rotation on failure
        for attempt in range(len(self.api_keys) + 1):  # +1 for initial try
            try:
                # Initialize model
                model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
                
                # Prepare chat
                chat_session = model.start_chat(history=history or [])
                
                # Add system prompt if not in history
                if not history or "role" not in history[0] or history[0]["role"] != "system":
                    chat_session.send_message(system_prompt, stream=False)
                
                # Generate response
                response = chat_session.send_message(user_input, stream=False)
                return response.text
                
            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt+1}: {str(e)}")
                if attempt < len(self.api_keys):
                    success = self._rotate_key()
                    if not success:
                        logger.critical("All API keys exhausted. Unable to generate content.")
                        return None
                else:
                    logger.critical(f"Failed to generate content after trying all API keys: {e}")
                    return None
                    
        return None
