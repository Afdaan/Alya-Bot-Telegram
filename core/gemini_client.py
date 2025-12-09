"""
Gemini API client for Alya Bot with key rotation.
Uses google-generativeai SDK v2 with Client() API.
"""
import logging
import random
import asyncio
import hashlib
from typing import Dict, List, Optional, Any

from google import genai

from config.settings import (
    GEMINI_API_KEYS, GEMINI_MODEL, MAX_OUTPUT_TOKENS,
    TEMPERATURE, TOP_K, TOP_P, DEFAULT_LANGUAGE
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API client with key rotation and async support (SDK v2)."""

    def __init__(self) -> None:
        """Initialize the Gemini client with API keys."""
        self.api_keys: List[str] = GEMINI_API_KEYS.copy()
        self.current_key_index: int = 0
        self.model: str = GEMINI_MODEL
        self.recent_response_hashes: Dict[int, List[str]] = {}
        self.persona_manager: Optional[Any] = None
        self.client: Optional[genai.Client] = None
        self._initialize_client()

    def set_persona_manager(self, persona_manager: Any) -> None:
        """Sets the persona manager for the client."""
        self.persona_manager = persona_manager

    def _initialize_client(self) -> None:
        """Initialize the Gemini client with the current API key."""
        if not self.api_keys:
            logger.error("No Gemini API keys available")
            return

        self.current_key_index = random.randint(0, len(self.api_keys) - 1)
        self._configure_client()

    def _configure_client(self) -> None:
        """Configure the Gemini client with the current API key."""
        if not self.api_keys:
            logger.error("No Gemini API keys available")
            return

        try:
            current_key = self.api_keys[self.current_key_index]
            self.client = genai.Client(api_key=current_key)
            logger.info(
                f"Configured Gemini client with API key index {self.current_key_index}"
            )
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")

    def _rotate_key(self) -> bool:
        """Rotate to the next available API key."""
        if not self.api_keys:
            logger.error("No API keys available for rotation")
            return False

        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            try:
                current_key = self.api_keys[self.current_key_index]
                self.client = genai.Client(api_key=current_key)
                logger.info(f"Rotated to API key index {self.current_key_index}")
                return True
            except Exception as e:
                logger.error(
                    f"Failed to rotate to API key index {self.current_key_index}: {e}"
                )

        logger.critical("All Gemini API keys have failed")
        return False

    def _calculate_response_hash(self, response: str) -> str:
        """Calculate a hash for response content to detect duplicates."""
        normalized = " ".join(response.lower().split())
        digest_input = normalized[:100]
        return hashlib.md5(digest_input.encode("utf-8")).hexdigest()

    def _is_duplicate_response(self, response: str, user_id: int) -> bool:
        """Check if response is a duplicate of recent responses for this user."""
        response_hash = self._calculate_response_hash(response)

        if (
            user_id in self.recent_response_hashes
            and response_hash in self.recent_response_hashes[user_id]
        ):
            return True

        if user_id not in self.recent_response_hashes:
            self.recent_response_hashes[user_id] = []

        self.recent_response_hashes[user_id].append(response_hash)
        if len(self.recent_response_hashes[user_id]) > 10:
            self.recent_response_hashes[user_id] = (
                self.recent_response_hashes[user_id][-10:]
            )

        return False

    def _get_safety_settings(self) -> Dict[str, str]:
        """Get safety settings for Gemini API (no blocking)."""
        return {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }

    async def generate_response(
        self,
        user_id: int,
        username: str,
        message: str,
        context: str,
        relationship_level: int,
        is_admin: bool,
        lang: str = DEFAULT_LANGUAGE,
        retry_count: int = 3,
        is_media_analysis: bool = False,
        media_context: Optional[str] = None,
    ) -> str:
        """Generate a response using Gemini with retry and key rotation.

        Args:
            user_id: User ID
            username: User's name
            message: User's message
            context: Conversation context
            relationship_level: User's relationship level with Alya
            is_admin: Whether the user is an admin
            lang: User's preferred language ('id' or 'en')
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
                # Construct prompt using persona manager
                if is_media_analysis:
                    prompt = self.persona_manager.get_media_analysis_prompt(
                        username=username,
                        query=message,
                        media_context=media_context,
                        lang=lang,
                    )
                else:
                    prompt = self.persona_manager.get_chat_prompt(
                        username=username,
                        message=message,
                        context=context,
                        relationship_level=relationship_level,
                        is_admin=is_admin,
                        lang=lang,
                    )

                # Run sync API call in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response_text = await loop.run_in_executor(
                    None, self._generate_content_sync, prompt
                )

                if user_id is not None and response_text:
                    if self._is_duplicate_response(response_text, user_id):
                        logger.warning(
                            f"Duplicate response detected for user {user_id}, "
                            "regenerating..."
                        )

                        for dup_attempt in range(2):
                            temp_boost = 0.1 * (dup_attempt + 1)
                            varied_temp = min(TEMPERATURE + temp_boost, 1.0)

                            varied_prompt = (
                                f"{prompt}\n\n"
                                "IMPORTANT: Provide a DIFFERENT response with "
                                "different phrasing and approach than before."
                            )

                            try:
                                varied_response = await loop.run_in_executor(
                                    None,
                                    self._generate_content_sync,
                                    varied_prompt,
                                    varied_temp,
                                )

                                if not self._is_duplicate_response(
                                    varied_response, user_id
                                ):
                                    response_text = varied_response
                                    logger.info(
                                        f"Generated varied response after "
                                        f"{dup_attempt + 1} attempts"
                                    )
                                    break
                            except Exception as e:
                                logger.error(f"Error generating varied response: {e}")

                return response_text

            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt + 1}: {str(e)}")
                if attempt < retry_count - 1:
                    success = self._rotate_key()
                    if not success:
                        logger.critical("All API keys exhausted")
                        return (
                            "Maaf, Alya punya masalah internal. Coba lagi nanti ya. 😓"
                        )
                else:
                    logger.critical(
                        f"Failed after all retries: {e}"
                    )
                    return (
                        "Aduh, koneksi Alya gagal. Mungkin coba beberapa saat lagi? 😥"
                    )

        return "Duh, Alya coba berkali-kali tapi tetep gagal. Coba lagi nanti ya. 😔"

    def _generate_content_sync(
        self,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        """Synchronous content generation wrapper.

        Args:
            prompt: The prompt to send
            temperature: Optional temperature override

        Returns:
            Generated text response
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": temperature or TEMPERATURE,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "top_p": TOP_P,
                "top_k": TOP_K,
            },
        )

        return response.text
