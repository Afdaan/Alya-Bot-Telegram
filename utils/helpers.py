import logging
import requests
from io import BytesIO

from config.settings import STABILITY_API_KEY

logger = logging.getLogger(__name__)

async def generate_image(prompt: str):
    """Generate an image using Stability AI API."""
    if not STABILITY_API_KEY:
        logger.warning("Stability API key not configured")
        return None
        
    try:
        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {STABILITY_API_KEY}"
            },
            json={
                "text_prompts": [{"text": prompt}],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
            },
        )
        
        if response.status_code != 200:
            logger.error(f"Error generating image: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        image_data = data["artifacts"][0]["base64"]
        image_bytes = BytesIO(bytes(image_data, 'utf-8'))
        
        return image_bytes
    except Exception as e:
        logger.error(f"Error in generate_image: {e}")
        return None