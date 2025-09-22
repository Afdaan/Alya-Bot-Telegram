#!/usr/bin/env python3
"""
Development script to test bot components.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from app.infrastructure.services import HuggingFaceSentimentService, GeminiAIService
from app.infrastructure.persona import YAMLPersonaService
from app.domain.entities import User, RelationshipLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sentiment_service():
    """Test sentiment analysis service."""
    logger.info("Testing sentiment service...")
    
    service = HuggingFaceSentimentService()
    
    test_messages = [
        "Aku senang banget hari ini!",
        "Aku sedih dan kecewa...",
        "Halo, apa kabar?",
        "Aku marah sekali!",
        "Wah, kaget aku!"
    ]
    
    for message in test_messages:
        emotion = await service.analyze_emotion(message)
        sentiment = await service.get_sentiment_score(message)
        logger.info(f"'{message}' -> Emotion: {emotion}, Sentiment: {sentiment}")


async def test_persona_service():
    """Test persona service."""
    logger.info("Testing persona service...")
    
    service = YAMLPersonaService()
    persona = await service.load_persona("alya")
    
    logger.info(f"Persona loaded: {persona.name}")
    logger.info(f"Base instructions (ID): {persona.base_instructions.get('id', 'Not found')[:100]}...")


async def test_ai_service():
    """Test AI service."""
    logger.info("Testing AI service...")
    
    try:
        ai_service = GeminiAIService()
        persona_service = YAMLPersonaService()
        
        persona = await persona_service.load_persona("alya")
        test_user = User(
            id=12345,
            first_name="Test",
            language_code="id",
            relationship_level=RelationshipLevel.FRIEND
        )
        
        response = await ai_service.generate_response(
            message="Halo Alya! Apa kabar?",
            context="",
            persona=persona,
            user=test_user
        )
        
        logger.info(f"AI Response: {response.content}")
        
    except Exception as e:
        logger.warning(f"AI service test skipped (probably missing API key): {e}")


async def main():
    """Run all tests."""
    logger.info("🧪 Running Alya Bot v2 Component Tests...")
    
    await test_sentiment_service()
    await test_persona_service()
    await test_ai_service()
    
    logger.info("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
