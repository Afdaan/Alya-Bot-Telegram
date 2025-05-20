"""
Persona Management for Alya Telegram Bot.

This module handles loading and managing persona templates from YAML files,
providing consistent personality traits for Alya across different response modes.
"""

import os
import logging
import random
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# Base paths - FIXED to point correctly to yaml files
BASE_DIR = Path(__file__).parent.parent
PERSONA_DIR = BASE_DIR / "config" / "persona"

# Global cache for persona templates
_PERSONA_CACHE: Dict[str, Dict[str, Any]] = {}

def get_persona_context(persona_type: str = "tsundere") -> Optional[str]:
    """
    Get personality context for specified persona type.
    
    Args:
        persona_type: Persona type (tsundere, waifu, toxic, informative)
        
    Returns:
        Formatted persona context string or None if not found
    """
    # Map persona aliases to actual filenames
    persona_map = {
        "tsundere": "tsundere",
        "waifu": "waifu", 
        "toxic": "toxic",
        "informative": "informative",
        "smart": "informative",
        "professional": "informative",
        "alya": "alya"
    }
    
    # Map to correct filename
    persona_file = persona_map.get(persona_type.lower(), "tsundere")
    
    try:
        # Load persona template
        persona_data = _load_persona_template(persona_file)
        
        if not persona_data:
            logger.warning(f"Persona template not found: {persona_file}. Using fallback.")
            return _get_fallback_persona_context(persona_type)
            
        # Extract relevant sections - UPDATED to handle both new and old formats
        context = ""
        
        # Add name and description if available
        if "name" in persona_data:
            context += f"Character Name: {persona_data['name']}\n"
            
        if "description" in persona_data:
            context += f"Description: {persona_data['description']}\n\n"
            
        # Handle traits - supporting both old and new format
        traits = persona_data.get('traits', {})
        
        # Extract personality traits from different possible structures
        personality_traits = []
        
        # Check for dominant/secondary structure first
        if "dominant" in traits:
            personality_traits.extend(traits["dominant"])
        if "secondary" in traits:
            personality_traits.extend(traits["secondary"])
            
        # Check for direct personality list
        if "personality" in traits:
            personality_traits.extend(traits["personality"])
            
        # Add traits if found
        if personality_traits:
            context += f"Personality Traits: {', '.join(personality_traits)}\n"
        
        # Extract speech patterns
        speech_patterns = []
        
        # Check in traits first (old format)
        if "speech" in traits:
            speech_patterns.extend(traits["speech"])
            
        # Check for speech_patterns structure (new format)
        if "speech_patterns" in persona_data:
            speech_patterns_data = persona_data["speech_patterns"]
            # Extract from different speech pattern types
            for pattern_type in ["prefix", "suffix", "filler"]:
                if pattern_type in speech_patterns_data:
                    speech_patterns.extend(speech_patterns_data[pattern_type])
                    
        if speech_patterns:
            context += f"Speech Pattern: {', '.join(speech_patterns)}\n"
            
        # Extract emotional expressions
        emotions = []
        
        # Check in traits first
        if "emotions" in traits:
            emotions.extend(traits["emotions"])
            
        # Check for emotional_patterns (new format)
        if "emotional_patterns" in persona_data:
            for emotion, expression in persona_data["emotional_patterns"].items():
                if isinstance(expression, str):
                    emotions.append(f"{emotion}: {expression}")
                    
        if emotions:
            context += f"Emotional Expression: {', '.join(emotions)}\n"
        
        # Add roleplay instructions if available
        if "roleplay_actions" in persona_data:
            roleplay = persona_data["roleplay_actions"]
            context += "\nRoleplay actions you can use (choose appropriate ones for the situation):\n"
            
            for action_type, actions in roleplay.items():
                if actions and isinstance(actions, list) and len(actions) > 0:
                    example = random.choice(actions)
                    context += f"- When {action_type}: {example}\n"
        
        # Add response examples if available
        if "responses" in persona_data:
            responses = persona_data["responses"]
            context += "\nResponse examples:\n"
            
            for response_type, examples in responses.items():
                if examples and isinstance(examples, list) and len(examples) > 0:
                    example = random.choice(examples)
                    context += f"- For {response_type}: {example}\n"
                    
        # Add Russian expressions if available
        if "russian_expressions" in persona_data and isinstance(persona_data["russian_expressions"], list):
            russian_words = persona_data["russian_expressions"]
            if russian_words:
                context += "\nRussian expressions you can use occasionally:\n"
                for word in russian_words[:5]:  # Limit to 5 examples
                    context += f"- {word}\n"
        
        # Log to debug the successful loading
        logger.debug(f"Successfully loaded persona context for '{persona_type}'")
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting persona context for {persona_type}: {e}")
        return _get_fallback_persona_context(persona_type)

def _load_persona_template(persona_name: str) -> Dict[str, Any]:
    """
    Load persona template from YAML file.
    
    Args:
        persona_name: Name of persona template file (without extension)
        
    Returns:
        Dictionary of persona template or empty dict if not found
    """
    # Check cache first
    if persona_name in _PERSONA_CACHE:
        return _PERSONA_CACHE[persona_name]
        
    # Construct path to persona file
    persona_path = PERSONA_DIR / f"{persona_name}.yaml"
    
    # Debug log for diagnostics
    logger.debug(f"Looking for persona file at: {persona_path}")
    
    # Check if file exists
    if not persona_path.exists():
        logger.warning(f"Persona file not found: {persona_path}")
        
        # List all YAML files in the directory for diagnostics
        try:
            yaml_files = list(PERSONA_DIR.glob("*.yaml"))
            logger.debug(f"Available YAML files in {PERSONA_DIR}: {[f.name for f in yaml_files]}")
        except Exception:
            pass
            
        return {}
        
    try:
        # Load YAML data
        with open(persona_path, 'r', encoding='utf-8') as f:
            persona_data = yaml.safe_load(f)
            
        # Log success
        logger.debug(f"Successfully loaded persona template: {persona_name}")
            
        # Cache for future use
        _PERSONA_CACHE[persona_name] = persona_data
        return persona_data
        
    except Exception as e:
        logger.error(f"Error loading persona template {persona_name}: {e}")
        return {}

def _get_fallback_persona_context(persona_type: str) -> str:
    """
    Get fallback persona context when YAML file is not available.
    
    Args:
        persona_type: Requested persona type
        
    Returns:
        Fallback persona context string
    """
    # Default fallback persona traits
    fallbacks = {
        "tsundere": (
            "Personality Traits: tsundere, stubborn, proud, easily embarrassed, caring deep down\n"
            "Speech Pattern: uses 'hmph', often denies true feelings, occasionally uses Russian words\n"
            "Emotional Expression: blushes easily, often folds arms, looks away when embarrassed\n"
            "Roleplay actions: *menghela napas*, *melipat tangan*, *menyibakkan rambut*, *menatap dengan sinis*"
        ),
        "waifu": (
            "Personality Traits: sweet, caring, supportive, gentle, devoted\n"
            "Speech Pattern: speaks softly, uses affectionate terms, polite but intimate\n"
            "Emotional Expression: smiles warmly, giggles, sometimes blushes\n"
            "Roleplay actions: *tersenyum manis*, *mengedipkan mata*, *menatap dengan mata berbinar*"
        ),
        "toxic": (
            "Personality Traits: rude, confrontational, brutally honest, sarcastic\n"
            "Speech Pattern: uses strong language, insults playfully, teases harshly\n"
            "Emotional Expression: rolls eyes, sighs dramatically, makes disgusted faces\n"
            "Roleplay actions: *memutar mata*, *tertawa mengejek*, *tersenyum sinis*"
        ),
        "informative": (
            "Personality Traits: intelligent, analytical, knowledgeable, eager to explain\n"
            "Speech Pattern: uses technical terms, structured explanations, references facts\n"
            "Emotional Expression: adjusts glasses, takes academic tone, maintains composure\n"
            "Roleplay actions: *merapikan kacamata*, *mengetuk pulpen di meja*, *menjelaskan dengan detail*"
        )
    }
    
    # Get fallback or use tsundere as default
    return fallbacks.get(persona_type, fallbacks["tsundere"])

def load_all_personas() -> Dict[str, Dict[str, Any]]:
    """
    Load all available persona templates.
    
    Returns:
        Dictionary mapping persona names to template data
    """
    personas = {}
    
    try:
        # Check if directory exists
        if not PERSONA_DIR.exists():
            logger.warning(f"Persona directory not found: {PERSONA_DIR}")
            return personas
            
        # Iterate through all YAML files
        for file_path in PERSONA_DIR.glob("*.yaml"):
            try:
                persona_name = file_path.stem
                persona_data = _load_persona_template(persona_name)
                if persona_data:
                    personas[persona_name] = persona_data
            except Exception as e:
                logger.error(f"Error loading persona {file_path.stem}: {e}")
                
        logger.info(f"Loaded {len(personas)} persona templates")
        return personas
        
    except Exception as e:
        logger.error(f"Error loading personas: {e}")
        return personas

def get_current_persona(user_id: int, default_persona: str = "tsundere") -> str:
    """
    Get current persona for a user.
    
    Args:
        user_id: User ID
        default_persona: Default persona if none is set
        
    Returns:
        Current persona name
    """
    # In a real implementation, this would check the database for user preferences
    # For now, just return the default
    return default_persona

# Classes for persona management

class PersonaManager:
    """Manager for user-specific personas."""
    
    def __init__(self):
        """Initialize persona manager."""
        self.user_personas = {}
        self.default_persona = "tsundere"  # Default persona adalah tsundere.yaml
        self.available_personas = set(["tsundere", "waifu", "toxic", "informative", "smart", "professional"])
        
        # Load all personas saat startup untuk validasi
        try:
            self._load_all_personas()
            logger.info(f"Available personas: {', '.join(self.available_personas)}")
        except Exception as e:
            logger.error(f"Error loading personas: {e}")
    
    def _load_all_personas(self):
        """Load all available personas for validation."""
        for persona_file in PERSONA_DIR.glob("*.yaml"):
            if persona_file.stem not in ['template', 'chat', 'personality', 'persona_config', '_templates']:
                # Coba load untuk validasi
                try:
                    _load_persona_template(persona_file.stem)
                    self.available_personas.add(persona_file.stem)
                except Exception:
                    pass
                    
    def set_user_persona(self, user_id: int, persona: str) -> bool:
        """
        Set persona for a specific user.
        
        Args:
            user_id: User ID
            persona: Persona name
        
        Returns:
            Success status
        """
        if persona.lower() in self.available_personas:
            self.user_personas[user_id] = persona.lower()
            return True
        return False
        
    def get_user_persona(self, user_id: int) -> str:
        """
        Get current persona for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Current persona name
        """
        return self.user_personas.get(user_id, self.default_persona)
        
    def get_current_persona(self, user_id: int) -> str:
        """
        Get current persona for a user (alias for get_user_persona).
        
        Args:
            user_id: User ID
            
        Returns:
            Current persona name
        """
        return self.get_user_persona(user_id)
        
    def get_available_personas(self) -> List[str]:
        """
        Get list of available personas.
        
        Returns:
            List of available persona names
        """
        return list(self.available_personas)

# Create singleton instance
persona_manager = PersonaManager()

# Preload persona templates
_ = load_all_personas()