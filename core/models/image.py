"""Image analysis functionality using Gemini."""

import logging
from typing import Optional
import PIL.Image
import google.generativeai as genai

from config.settings import IMAGE_MODEL, GENERATION_CONFIG
from .gemini import convert_safety_settings

logger = logging.getLogger(__name__)

async def generate_image_analysis(image_path: str, custom_prompt: Optional[str] = None) -> str:
    """
    Generate analysis of image using Gemini.
    
    Args:
        image_path: Path to image file
        custom_prompt: Optional custom prompt for analysis
        
    Returns:
        Analysis text result
    """
    try:
        # Load image
        image = PIL.Image.open(image_path)
        
        # Create model instance
        model = genai.GenerativeModel(
            model_name=IMAGE_MODEL,
            generation_config=GENERATION_CONFIG,
            safety_settings=convert_safety_settings()
        )
        
        # Default prompt if none provided
        default_prompt = """
        Analisis gambar ini dengan detail secara menyeluruh.
        Jelaskan apa yang kamu lihat, termasuk objek, warna, suasana, dan konteks.
        Berikan analisis yang lengkap namun ringkas.
        """
        
        # Generate analysis
        response = model.generate_content(
            [custom_prompt or default_prompt, image]
        )
        
        if not response or not response.text:
            raise RuntimeError("Empty response from Gemini")
            
        return response.text[:4000]  # Limit length
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return f"<i>Tidak dapat menganalisis gambar: {str(e)[:100]}...</i>"

async def generate_document_analysis(text_content: str) -> str:
    """
    Generate analysis of document text using Gemini.
    
    Args:
        text_content: Document text to analyze
        
    Returns:
        Analysis result
    """
    try:
        # Truncate long text
        truncated_text = text_content[:8000] + "..." if len(text_content) > 8000 else text_content
        
        # Create model instance
        model = genai.GenerativeModel(
            model_name=IMAGE_MODEL,
            generation_config=GENERATION_CONFIG,
            safety_settings=convert_safety_settings()
        )
        
        prompt = f"""
        Analisis dokumen berikut dengan detail dan rangkum dengan jelas:
        
        ```
        {truncated_text}
        ```
        """
        
        # Generate analysis
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            raise RuntimeError("Empty response from Gemini")
            
        return response.text[:4000]  # Limit length
        
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return f"<i>Tidak dapat menganalisis dokumen: {str(e)[:100]}...</i>"
