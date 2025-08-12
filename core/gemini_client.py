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
        self.persona_manager = None # Will be set later
        self._initialize_client()
        
    def set_persona_manager(self, persona_manager: Any) -> None:
        """Sets the persona manager for the client."""
        self.persona_manager = persona_manager

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
        
    async def generate_response(
        self,
        user_id: int,
        username: str,
        message: str,
        context: str,
        relationship_level: int,
        is_admin: bool,
        lang: str = 'id', # Add lang parameter
        retry_count: int = 3,
        is_media_analysis: bool = False,
        media_context: Optional[str] = None
    ) -> str:
        """Generate a response using Gemini, with retry and key rotation logic.
        
        Args:
            user_id: User ID
            username: User's name
            message: User's message
            context: Conversation context
            relationship_level: User's relationship level with Alya
            is_admin: Whether the user is an admin
            lang: The user's preferred language ('id' or 'en')
            retry_count: Number of retries
            is_media_analysis: Flag for media analysis prompts
            media_context: Context from media analysis
            
        Returns:
            Generated response text
        """
        if not self.persona_manager:
            raise ValueError("Persona manager not set for GeminiClient")

        for attempt in range(retry_count):
            try:
                # Construct the prompt using the persona manager
                if is_media_analysis:
                    prompt = self.persona_manager.get_media_analysis_prompt(
                        username=username,
                        query=message,
                        media_context=media_context,
                        lang=lang
                    )
                else:
                    prompt = self.persona_manager.get_chat_prompt(
                        username=username,
                        message=message,
                        context=context,
                        relationship_level=relationship_level,
                        is_admin=is_admin,
                        lang=lang
                    )

                generation_config = GenerationConfig(
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    top_k=TOP_K,
                )
                
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
                
                response_obj = model.generate_content(prompt)
                response = response_obj.text
                
                if user_id is not None and response:
                    if self._is_duplicate_response(response, user_id):
                        logger.warning(f"Duplicate response detected for user {user_id}, regenerating...")
                        
                        duplicate_attempts = 0
                        max_duplicate_attempts = 2 # Try 2 more times
                        
                        while duplicate_attempts < max_duplicate_attempts:
                            duplicate_attempts += 1
                            temp_boost = 0.1 * duplicate_attempts
                            varied_config = GenerationConfig(
                                temperature=min(TEMPERATURE + temp_boost, 1.0),
                                top_p=TOP_P,
                                top_k=TOP_K,
                                max_output_tokens=MAX_OUTPUT_TOKENS,
                            )
                            
                            varied_prompt = (f"{prompt}\n\n"
                                           f"IMPORTANT: Please provide a different response with "
                                           f"different phrasing and approach than your previous responses.")
                                           
                            try:
                                varied_model = genai.GenerativeModel(
                                    model_name=self.model,
                                    generation_config=varied_config,
                                    safety_settings=safety_settings,
                                )
                                varied_response_obj = varied_model.generate_content(varied_prompt)
                                varied_response = varied_response_obj.text
                                
                                if not self._is_duplicate_response(varied_response, user_id):
                                    response = varied_response
                                    logger.info(f"Generated varied non-duplicate response after {duplicate_attempts} attempts")
                                    break
                                    
                            except Exception as varied_e:
                                logger.error(f"Error generating varied response: {varied_e}")
                        
                        if duplicate_attempts >= max_duplicate_attempts:
                            logger.warning(f"Could not generate non-duplicate response after {max_duplicate_attempts} attempts, using last response")

                return response
                
            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt+1}: {str(e)}")
                if attempt < retry_count - 1:
                    success = self._rotate_key()
                    if not success:
                        logger.critical("All API keys exhausted. Unable to generate content.")
                        return "Maaf, sepertinya Alya lagi ada masalah internal. Coba lagi nanti ya. 😓"
                else:
                    logger.critical(f"Failed to generate content after trying all API keys: {e}")
                    return "Aduh, maaf banget, semua koneksi Alya ke pusat data lagi gagal. Mungkin bisa coba beberapa saat lagi? 😥"
                    
        return "Duh, Alya coba berkali-kali tapi tetep gagal. Kayaknya ada yang gak beres. Coba lagi nanti ya. 😔"
