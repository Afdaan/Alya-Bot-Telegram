"""
Self-hosted LLM client for Alya Bot using GGUF models with llama.cpp.
"""
import logging
import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Perbaiki import - gunakan relative import untuk menghindari circular import
from core.gemini_client import GeminiClient  # Import dengan namespace

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    # Log warning instead of silent fail
    logging.getLogger(__name__).warning(
        "llama-cpp-python not installed. Self-hosted LLM will not be available. "
        "Install with: pip install llama-cpp-python"
    )

from config.settings import (
    LLM_MODEL_PATH, LLM_CONTEXT_SIZE, LLM_N_GPU_LAYERS,
    LLM_N_THREADS, LLM_TEMP, LLM_N_BATCH, LLM_TOP_P
)

logger = logging.getLogger(__name__)

class SelfClient:
    """Client for running local GGUF models via llama.cpp."""
    
    def __init__(self) -> None:
        """Initialize the self-hosted LLM client with local model."""
        self.model_path = LLM_MODEL_PATH
        self.model = None
        self.context_size = LLM_CONTEXT_SIZE
        self.n_gpu_layers = LLM_N_GPU_LAYERS
        self.n_threads = LLM_N_THREADS
        self.n_batch = LLM_N_BATCH
        self.temperature = LLM_TEMP
        self.top_p = LLM_TOP_P
        
        # Inisialisasi model saat initiate class
        if not self._initialize_model():
            logger.critical("Failed to initialize self-hosted LLM model. Bot will likely fail on first request!")
        
    def _initialize_model(self) -> bool:
        """Initialize the local LLM model.
        
        Returns:
            True if model initialized successfully
        """
        # Early return if library not installed
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama-cpp-python library not installed. Please install with: "
                        "pip install llama-cpp-python")
            return False
            
        # Check if model file exists
        if not self.model_path or not os.path.exists(self.model_path):
            logger.error(f"Model path not found: {self.model_path}")
            return False
        
        try:
            # Log model loading start with more info
            logger.info(f"Loading model from {self.model_path}")
            logger.info(f"Model configuration - GPU Layers: {self.n_gpu_layers}, "
                       f"Context: {self.context_size}, Threads: {self.n_threads}, "
                       f"Batch: {self.n_batch}")
            
            # Initialize model with parameters from settings
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.context_size,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=self.n_batch,
                n_threads=self.n_threads,
                verbose=False  # Production should have verbose=False
            )
            
            # Verify model loaded successfully
            if not self.model:
                logger.error("Failed to initialize model - returned None")
                return False
                
            logger.info("Self-hosted LLM model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize local LLM model: {e}", exc_info=True)
            return False
    
    def _format_history_for_openchat(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for OpenChat models.
        
        Args:
            history: List of conversation history entries
            
        Returns:
            Formatted conversation history string
        """
        formatted_messages = []
        
        for message in history:
            role = message.get("role", "")
            content = message.get("content", "")
            
            # Map roles to OpenChat format
            if role == "user":
                formatted_messages.append(f"Human: {content}")
            elif role == "assistant":
                formatted_messages.append(f"Assistant: {content}")
            elif role == "system":
                # For system prompts, we'll use a special format
                formatted_messages.append(f"<|system|>\n{content}\n</s>")
        
        # Join with newlines
        return "\n".join(formatted_messages)
    
    def _format_prompt_for_openchat(
        self,
        user_input: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Format prompt for the OpenChat model.
        
        Args:
            user_input: User's message
            system_prompt: System prompt/instructions
            history: Optional conversation history
            
        Returns:
            Formatted prompt string
        """
        # Start with system prompt
        formatted_prompt = f"<|system|>\n{system_prompt}\n</s>\n"
        
        # Add conversation history if provided
        if history and len(history) > 0:
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                if role == "user":
                    formatted_prompt += f"Human: {content}\n"
                elif role == "assistant":
                    formatted_prompt += f"Assistant: {content}\n"
        
        # Add the current user message
        formatted_prompt += f"Human: {user_input}\n"
        formatted_prompt += "Assistant:"
        
        return formatted_prompt
    
    async def generate_content(
        self, 
        user_input: str, 
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        safe_mode: bool = False  # Not used but kept for API compatibility
    ) -> Optional[str]:
        """
        Generate content using local LLM with llama.cpp.
        
        Args:
            user_input: The user's input message
            system_prompt: System prompt with persona instructions
            history: Optional conversation history
            safe_mode: Not used for local models, but kept for API compatibility
            
        Returns:
            Generated response text or None if generation failed
        """
        # First check if model was properly initialized
        if not self.model:
            logger.error("Local LLM model not initialized - attempting to reinitialize")
            # Try to initialize again
            if not self._initialize_model():
                logger.critical("Could not initialize model - generation failed")
                return None
        
        try:
            # Format prompt for model
            formatted_prompt = self._format_prompt_for_openchat(
                user_input=user_input,
                system_prompt=system_prompt,
                history=history
            )
            
            # Log prompt size (token count estimation)
            logger.debug(f"Prompt size: ~{len(formatted_prompt) // 4} tokens")
            
            # Run model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            # Run in executor to avoid blocking the event loop
            response = await loop.run_in_executor(
                None,
                lambda: self.model.create_completion(
                    prompt=formatted_prompt,
                    max_tokens=1024,  # Adjust as needed
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stop=["Human:", "</s>", "\n\n"]  # Stop generation at specific tokens
                )
            )
            
            if not response or "choices" not in response:
                logger.warning("Empty response from local LLM")
                return None
                
            # Extract response text
            generated_text = response["choices"][0]["text"].strip()
            
            # Remove any remaining prompt fragments
            generated_text = self._clean_response(generated_text)
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Error generating content with local LLM: {e}", exc_info=True)
            return None
    
    def _clean_response(self, response: str) -> str:
        """Clean up model response by removing any artifacts.
        
        Args:
            response: Raw model response
            
        Returns:
            Cleaned response text
        """
        # Remove any remaining prompt artifacts
        return response.replace("Assistant:", "").strip()
