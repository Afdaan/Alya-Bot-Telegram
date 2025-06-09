"""
Gemini API client for Alya Bot with key rotation.
"""
import logging
import random
import time
import asyncio
import hashlib
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
        self.recent_response_hashes: Dict[int, List[str]] = {}  # Last response hashes by user_id
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
    
    def _calculate_response_hash(self, response: str) -> str:
        """Calculate a hash for response content to detect duplicates.
        
        Args:
            response: Response content to hash
            
        Returns:
            MD5 hash of normalized response
        """
        # Normalize response by removing whitespace variation and converting to lowercase
        normalized = ' '.join(response.lower().split())
        # Take first 100 chars to focus on the beginning (most repetitive part)
        digest_input = normalized[:100]
        
        return hashlib.md5(digest_input.encode('utf-8')).hexdigest()
    
    def _is_duplicate_response(self, response: str, user_id: int) -> bool:
        """Check if response is a duplicate of recent responses for this user.
        
        Args:
            response: Response to check
            user_id: User ID
            
        Returns:
            True if response is a duplicate, False otherwise
        """
        # Generate hash for new response
        response_hash = self._calculate_response_hash(response)
        
        # Check if hash exists in recent responses for this user
        if user_id in self.recent_response_hashes and response_hash in self.recent_response_hashes[user_id]:
            return True
            
        # Not a duplicate, store hash
        if user_id not in self.recent_response_hashes:
            self.recent_response_hashes[user_id] = []
            
        # Add to recent hashes and maintain length
        self.recent_response_hashes[user_id].append(response_hash)
        # Keep only the last 10 hashes
        if len(self.recent_response_hashes[user_id]) > 10:
            self.recent_response_hashes[user_id] = self.recent_response_hashes[user_id][-10:]
            
        return False
        
    async def generate_content(
        self, 
        user_input: str, 
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        safe_mode: bool = False,
        user_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate content using Gemini API with automatic key rotation and deduplication.
        
        Args:
            user_input: The user's input message
            system_prompt: System prompt with persona instructions
            history: Optional conversation history
            safe_mode: Whether to use Google's default safety settings
            user_id: User ID for tracking duplicates
            
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
        max_attempts = len(self.api_keys) + 1  # +1 for initial try
        for attempt in range(max_attempts):
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
                if system_prompt and (not history or "role" not in history[0] or history[0]["role"] != "system"):
                    chat_session.send_message(system_prompt, stream=False)
                
                # Generate response
                response = chat_session.send_message(user_input, stream=False).text
                
                # Check for response duplication if user_id provided
                if user_id is not None and response:
                    # Check if this is a duplicate response for this user
                    if self._is_duplicate_response(response, user_id):
                        logger.warning(f"Duplicate response detected for user {user_id}, regenerating...")
                        
                        # Try again with higher temperature for more variation (up to 3 additional attempts)
                        duplicate_attempts = 0
                        max_duplicate_attempts = 3
                        
                        while duplicate_attempts < max_duplicate_attempts:
                            duplicate_attempts += 1
                            
                            # Gradually increase temperature with each attempt
                            temp_boost = 0.1 * duplicate_attempts
                            varied_config = GenerationConfig(
                                temperature=min(TEMPERATURE + temp_boost, 1.0),
                                top_p=TOP_P,
                                top_k=TOP_K,
                                max_output_tokens=MAX_OUTPUT_TOKENS,
                            )
                            
                            # Add variation hint to system prompt
                            varied_prompt = system_prompt
                            if system_prompt:
                                varied_prompt = (f"{system_prompt}\n\n"
                                               f"IMPORTANT: Please provide a different response with "
                                               f"different phrasing and approach than your previous responses.")
                                               
                            try:
                                # Create new model with varied config
                                varied_model = genai.GenerativeModel(
                                    model_name=self.model,
                                    generation_config=varied_config,
                                    safety_settings=safety_settings,
                                )
                                
                                # Start new chat
                                varied_chat = varied_model.start_chat(history=history or [])
                                
                                # Add system prompt with variation hint
                                if varied_prompt and (not history or "role" not in history[0] or history[0]["role"] != "system"):
                                    varied_chat.send_message(varied_prompt, stream=False)
                                    
                                # Generate new response
                                varied_response = varied_chat.send_message(user_input, stream=False).text
                                
                                # Check if this varied response is unique
                                if not self._is_duplicate_response(varied_response, user_id):
                                    response = varied_response
                                    logger.info(f"Generated varied non-duplicate response after {duplicate_attempts} attempts")
                                    break
                                    
                            except Exception as varied_e:
                                logger.error(f"Error generating varied response: {varied_e}")
                        
                        # If we still have a duplicate after all attempts, just use it
                        if duplicate_attempts >= max_duplicate_attempts:
                            logger.warning(f"Could not generate non-duplicate response after {max_duplicate_attempts} attempts, using last response")
                
                return response
                
            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt+1}: {str(e)}")
                if attempt < max_attempts - 1:
                    success = self._rotate_key()
                    if not success:
                        logger.critical("All API keys exhausted. Unable to generate content.")
                        return None
                else:
                    logger.critical(f"Failed to generate content after trying all API keys: {e}")
                    return None
                    
        return None
