"""
Test persona service.
"""
import pytest
from app.infrastructure.persona import YAMLPersonaService
from app.domain.entities import EmotionType


@pytest.mark.asyncio
async def test_load_default_persona():
    """Test loading default persona."""
    service = YAMLPersonaService(personas_dir="personas")
    persona = await service.load_persona("alya")
    
    assert persona.name == "alya"
    assert "id" in persona.base_instructions
    assert "en" in persona.base_instructions
    assert len(persona.personality_traits.get("id", [])) > 0


@pytest.mark.asyncio 
async def test_get_response_template():
    """Test getting response template."""
    service = YAMLPersonaService(personas_dir="personas")
    persona = await service.load_persona("alya")
    
    template = await service.get_response_template(
        persona, 
        EmotionType.HAPPY, 
        "id"
    )
    
    assert isinstance(template, str)
    assert len(template) > 0


@pytest.mark.asyncio
async def test_load_nonexistent_persona():
    """Test loading non-existent persona returns default."""
    service = YAMLPersonaService(personas_dir="personas")
    persona = await service.load_persona("nonexistent")
    
    # Should return default persona
    assert persona.name == "alya"
