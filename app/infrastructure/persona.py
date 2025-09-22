"""
YAML persona management service.
"""
import os
import logging
from typing import Dict, Any, Optional
import yaml
from pathlib import Path

from ..domain.entities import PersonaConfig, EmotionType
from ..domain.services import PersonaService

logger = logging.getLogger(__name__)


class YAMLPersonaService(PersonaService):
    """YAML-based persona management service."""
    
    def __init__(self, personas_dir: str = "personas"):
        self.personas_dir = Path(personas_dir)
        self.personas_cache: Dict[str, PersonaConfig] = {}
        self._load_all_personas()
    
    def _load_all_personas(self):
        """Load all persona YAML files."""
        if not self.personas_dir.exists():
            logger.warning(f"Personas directory {self.personas_dir} does not exist")
            return
        
        for yaml_file in self.personas_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                persona_name = yaml_file.stem
                persona = PersonaConfig(
                    name=persona_name,
                    base_instructions=data.get("base_instructions", {}),
                    personality_traits=data.get("personality_traits", {}),
                    relationship_levels=data.get("relationship_levels", {}),
                    response_formats=data.get("response_formats", {}),
                    russian_phrases=data.get("russian_phrases", {}),
                    emotion_responses=data.get("emotion_responses", {})
                )
                
                self.personas_cache[persona_name] = persona
                logger.info(f"Loaded persona: {persona_name}")
                
            except Exception as e:
                logger.error(f"Error loading persona {yaml_file}: {e}")
    
    async def load_persona(self, name: str) -> PersonaConfig:
        """Load persona configuration."""
        if name in self.personas_cache:
            return self.personas_cache[name]
        
        # Try to load if not in cache
        yaml_file = self.personas_dir / f"{name}.yaml"
        if yaml_file.exists():
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                persona = PersonaConfig(
                    name=name,
                    base_instructions=data.get("base_instructions", {}),
                    personality_traits=data.get("personality_traits", {}),
                    relationship_levels=data.get("relationship_levels", {}),
                    response_formats=data.get("response_formats", {}),
                    russian_phrases=data.get("russian_phrases", {}),
                    emotion_responses=data.get("emotion_responses", {})
                )
                
                self.personas_cache[name] = persona
                return persona
                
            except Exception as e:
                logger.error(f"Error loading persona {name}: {e}")
        
        # Return default persona if not found
        return self._get_default_persona()
    
    async def get_response_template(
        self, 
        persona: PersonaConfig, 
        emotion: EmotionType,
        language: str = "id"
    ) -> str:
        """Get response template for emotion."""
        emotion_responses = persona.emotion_responses.get(language, {})
        if emotion.value in emotion_responses:
            return emotion_responses[emotion.value]
        
        # Fallback to default response format
        return persona.response_formats.get(language, "Respond naturally as Alya.")
    
    def _get_default_persona(self) -> PersonaConfig:
        """Get default Alya persona."""
        return PersonaConfig(
            name="alya",
            base_instructions={
                "id": "Kamu adalah Alya, gadis tsundere yang suka menggunakan bahasa Rusia saat emosional.",
                "en": "You are Alya, a tsundere girl who uses Russian phrases when emotional."
            },
            personality_traits={
                "id": [
                    "Tsundere dengan sifat dingin di luar tapi hangat di dalam",
                    "Suka menggunakan kata-kata Rusia saat emosional",
                    "Pintar dan berprestasi",
                    "Agak pemalu soal perasaan",
                    "Perhatian tapi tidak mau mengakui"
                ],
                "en": [
                    "Tsundere with cold exterior but warm inside",
                    "Uses Russian phrases when emotional", 
                    "Smart and accomplished",
                    "Shy about feelings",
                    "Caring but won't admit it"
                ]
            },
            relationship_levels={
                "id": [
                    "Bersikap formal dan dingin",
                    "Mulai sedikit akrab tapi masih tsundere",
                    "Lebih terbuka dan ekspresif",
                    "Sangat dekat dan perhatian",
                    "Sangat intim dan jujur tentang perasaan"
                ],
                "en": [
                    "Formal and cold behavior",
                    "Slightly friendly but still tsundere",
                    "More open and expressive", 
                    "Very close and caring",
                    "Very intimate and honest about feelings"
                ]
            },
            russian_phrases={
                "id": {
                    "дурак": "bodoh/idiot",
                    "что": "apa",
                    "правда": "benarkah",
                    "хорошо": "baik/oke"
                },
                "en": {
                    "дурак": "idiot/fool",
                    "что": "what", 
                    "правда": "really",
                    "хорошо": "good/okay"
                }
            }
        )
