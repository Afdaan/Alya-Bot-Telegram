"""
Persona Management for Alya Bot.

This module handles persona switching, loading persona definitions from YAML files,
and maintaining user-specific persona preferences.
"""

import os
import yaml
import logging
import random
from typing import Dict, Any, List, Optional, Set, Union
from pathlib import Path
import time

from utils.yaml_loader import load_yaml_file

logger = logging.getLogger(__name__)

# Constants
PERSONA_DIR = Path(__file__).parent.parent / "config" / "persona"
DEFAULT_PERSONA = "tsundere"
PERSONA_CACHE_TTL = 300  # 5 minutes
VALID_PERSONAS = ["tsundere", "waifu", "informative", "roast"]

class PersonaManager:
    """
    Manager for persona configurations and user preferences.
    
    This class handles loading persona definitions, managing user persona preferences,
    and providing persona-specific formatting and responses.
    """
    
    def __init__(self):
        """Initialize persona manager with cache and default values."""
        self.persona_cache = {}
        self.cache_timestamps = {}  # FIX: Add missing initialization of cache_timestamps
        self.user_personas = {}
        self.last_cache_clear = time.time()
        self._load_available_personas()
    
    def _load_available_personas(self):
        """Load available personas from disk."""
        self.available_personas = []
        try:
            for file_path in PERSONA_DIR.glob("*.yaml"):
                # Skip template files, schema file, and non-persona files
                if file_path.name.startswith("_") or file_path.name in ["schema.yaml", "template.yaml"]:
                    continue
                persona_name = file_path.stem
                self.available_personas.append(persona_name)
                
            # Ensure we have at least default persona
            if not self.available_personas:
                logger.warning("No persona files found, falling back to default")
                self.available_personas = [DEFAULT_PERSONA]
        except Exception as e:
            logger.error(f"Error loading personas: {e}")
            self.available_personas = [DEFAULT_PERSONA]
    
    def load_persona(self, persona_name: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load persona definition from YAML file.
        
        Args:
            persona_name: Name of the persona to load
            force_reload: Force reload from disk
            
        Returns:
            Persona definition dictionary
        """
        # Default to tsundere if persona doesn't exist
        if persona_name not in self.available_personas:
            logger.warning(f"Persona {persona_name} not found, using tsundere instead")
            persona_name = "tsundere"
        
        # Check cache
        current_time = time.time()
        if not force_reload and persona_name in self.persona_cache:
            if current_time - self.cache_timestamps.get(persona_name, 0) < PERSONA_CACHE_TTL:
                return self.persona_cache[persona_name]
        
        # Load from file
        persona_path = PERSONA_DIR / f"{persona_name}.yaml"
        persona_data = load_yaml_file(persona_path)
        
        if not persona_data:
            logger.error(f"Failed to load persona {persona_name}")
            # If tsundere also fails, use hardcoded fallback
            if persona_name == "tsundere":
                persona_data = self._get_fallback_persona()
            else:
                # Try to load tsundere as fallback
                return self.load_persona("tsundere")
        
        # Cache persona
        self.persona_cache[persona_name] = persona_data
        self.cache_timestamps[persona_name] = current_time
        
        return persona_data
    
    def _get_fallback_persona(self) -> Dict[str, Any]:
        """
        Get fallback persona if YAML loading fails.
        
        Returns:
            Basic tsundere persona definition
        """
        return {
            "name": "tsundere",
            "description": "Tsundere personality with a mix of harsh and sweet traits",
            "traits": [
                "Initially cold and dismissive but gradually warms up",
                "Hides true feelings behind tough exterior",
                "Often says the opposite of what she means",
                "Uses phrases like 'b-baka' and 'hmph'",
                "Mixes Japanese and Russian expressions when emotional"
            ],
            "expressions": {
                "greeting": ["Hmph, kamu lagi? B-bukan berarti Alya senang atau apa!"],
                "goodbye": ["J-jangan pergi terlalu lama, b-baka!"],
                "thanks": ["Jangan salah paham! Alya bantu bukan karena suka sama kamu!"],
                "confused": ["Bozhe moi... apa sih maksudmu?"],
                "happy": ["*memalingkan wajah* Alya nggak senang kok! Hanya... puas saja."],
                "angry": ["BAKA! Kamu benar-benar menyebalkan!"]
            }
        }
    
    def set_user_persona(self, user_id: int, persona_name: str) -> bool:
        """
        Set a user's preferred persona.
        
        Args:
            user_id: User ID
            persona_name: Persona name to set
            
        Returns:
            True if successful, False otherwise
        """
        if persona_name not in self.available_personas:
            logger.warning(f"Cannot set unknown persona {persona_name}")
            return False
            
        self.user_personas[user_id] = persona_name
        return True
    
    def get_current_persona(self, user_id: int) -> str:
        """
        Get the current persona for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Current persona name (defaults to tsundere)
        """
        return self.user_personas.get(user_id, DEFAULT_PERSONA)
    
    def get_random_expression(self, persona_name: str, expression_type: str) -> str:
        """
        Get a random expression from a persona.
        
        Args:
            persona_name: Persona name
            expression_type: Type of expression (greeting, goodbye, etc)
            
        Returns:
            Random expression or default if not found
        """
        persona = self.load_persona(persona_name)
        expressions = persona.get("expressions", {}).get(expression_type, [])
        
        if not expressions:
            # Check default persona if expression not found
            if persona_name != DEFAULT_PERSONA:
                return self.get_random_expression(DEFAULT_PERSONA, expression_type)
            return f"Alya {expression_type}s."
        
        return random.choice(expressions)
    
    def get_all_personas(self) -> List[Dict[str, Any]]:
        """
        Get all available personas with basic info.
        
        Returns:
            List of persona info dictionaries
        """
        personas = []
        
        for persona_name in self.available_personas:
            persona_data = self.load_persona(persona_name)
            
            personas.append({
                "name": persona_name,
                "display_name": persona_data.get("display_name", persona_name.capitalize()),
                "description": persona_data.get("description", "No description available")
            })
            
        return personas
    
    def reload_all_personas(self) -> int:
        """
        Reload all personas from disk.
        
        Returns:
            Number of personas reloaded
        """
        # Rediscover available personas
        self.available_personas = self._discover_personas()
        
        # Clear cache
        self.persona_cache.clear()
        self.cache_timestamps.clear()
        
        # Pre-load all personas
        count = 0
        for persona_name in self.available_personas:
            self.load_persona(persona_name, force_reload=True)
            count += 1
            
        return count

# Create a singleton instance
persona_manager = PersonaManager()

def get_persona_context(persona_name: str) -> str:
    """
    Get persona context for AI prompt.
    
    Args:
        persona_name: Name of persona
        
    Returns:
        Formatted persona context string
    """
    persona = persona_manager.load_persona(persona_name)
    
    # Extract traits
    traits = persona.get("traits", [])
    traits_text = "\n".join(f"- {trait}" for trait in traits)
    
    # Build context
    context = f"You are using the {persona_name} persona with these traits:\n{traits_text}"
    
    # Add any special instructions
    instructions = persona.get("instructions", "")
    if instructions:
        context += f"\n\n{instructions}"
        
    return context

def get_random_expression(persona_name: str, expression_type: str) -> str:
    """
    Get a random expression from a persona (convenience function).
    
    Args:
        persona_name: Persona name
        expression_type: Type of expression
        
    Returns:
        Random expression
    """
    return persona_manager.get_random_expression(persona_name, expression_type)