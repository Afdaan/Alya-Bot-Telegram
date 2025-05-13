"""
Helper Utilities for Alya Telegram Bot.

This module provides general utility functions, including image generation.
"""

import logging
import requests
from io import BytesIO
from typing import Optional

from config.settings import STABILITY_API_KEY

logger = logging.getLogger(__name__)

# =========================
# Image Generation
# =========================

async def generate_image(prompt: str) -> Optional[BytesIO]:
    """
    Generate an image using Stability AI API.
    
    Args:
        prompt: Text description for image generation
        
    Returns:
        BytesIO object containing the generated image, or None if generation failed
    """
    # Check if API key is configured
    if not STABILITY_API_KEY:
        logger.warning("Stability API key not configured")
        return None
        
    try:
        # API endpoint for Stable Diffusion XL
        endpoint = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        # Configure request headers and parameters
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {STABILITY_API_KEY}"
        }
        
        # Generation parameters
        payload = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
        }
        
        # Make API request
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload
        )
        
        # Handle API errors
        if response.status_code != 200:
            logger.error(f"Error generating image: {response.status_code} - {response.text}")
            return None
            
        # Process response
        data = response.json()
        image_data = data["artifacts"][0]["base64"]
        image_bytes = BytesIO(bytes(image_data, 'utf-8'))
        
        return image_bytes
    
    except Exception as e:
        logger.error(f"Error in generate_image: {e}")
        return None