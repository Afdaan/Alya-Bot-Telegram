"""
Persona Management for Alya Telegram Bot.

This module handles loading and managing persona templates from YAML files,
providing consistent personality traits for Alya across different response modes.
"""
import logging
import yaml
import os
import random
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Base paths - FIXED to point correctly to yaml files
BASE_DIR = Path(__file__).parent.parent
PERSONA_DIR = BASE_DIR / "config" / "persona"
DEFAULT_PERSONA = "tsundere"

# Global cache for persona templates
_PERSONA_CACHE: Dict[str, Dict[str, Any]] = {}

class PersonaManager:
    """Manager for user-specific personas."""
    
    def __init__(self):
        """Initialize persona manager."""
        # Dictionary to hold persona configurations
        self.personas = {}
        
        # Dictionary to hold user preferences
        self.user_personas = {}
        
        # Default persona name
        self.default_persona = DEFAULT_PERSONA
        
        # Load all available personas
        self._load_all_personas()
    
    def _load_all_personas(self) -> None:
        """Load all persona configurations from YAML files."""
        logger.info("Loading all personas...")
        try:
            # Check if directory exists
            if not PERSONA_DIR.exists():
                logger.error(f"Persona directory not found: {PERSONA_DIR}")
                return
                
            # Find all YAML files
            yaml_files = list(PERSONA_DIR.glob("*.yaml")) + list(PERSONA_DIR.glob("*.yml"))
            
            if not yaml_files:
                logger.warning(f"No persona files found in {PERSONA_DIR}")
                return
                
            # Load each file
            for file_path in yaml_files:
                try:
                    # Skip moods.yaml as it's not a persona file
                    if file_path.stem.lower() == "moods":
                        continue
                    
                    persona_name = file_path.stem.lower()
                    success = self.load_persona(persona_name, str(file_path))
                    if success:
                        logger.info(f"Loaded persona: {persona_name}")
                    else:
                        logger.warning(f"Failed to load persona: {persona_name}")
                except Exception as e:
                    logger.error(f"Error loading persona {file_path.name}: {e}")
                    
            logger.info(f"Loaded {len(self.personas)} personas")
                
        except Exception as e:
            logger.error(f"Error loading all personas: {e}")
                    
    def set_user_persona(self, user_id: int, persona: str) -> bool:
        """
        Set persona for a specific user.
        
        Args:
            user_id: User ID
            persona: Persona name
            
        Returns:
            True if set successfully, False otherwise
        """
        if persona not in self.personas and persona != "random":
            logger.warning(f"Tried to set unknown persona: {persona}")
            return False
            
        # Handle random persona
        if persona == "random":
            available = list(self.personas.keys())
            if not available:
                logger.warning("No personas available for random selection")
                return False
                
            self.user_personas[user_id] = random.choice(available)
        else:
            self.user_personas[user_id] = persona
            
        logger.debug(f"Set persona for user {user_id} to {self.user_personas[user_id]}")
        return True
    
    def get_user_persona(self, user_id: int) -> str:
        """
        Get persona for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Persona name
        """
        return self.user_personas.get(user_id, self.default_persona)
    
    def get_current_persona(self, user_id: int) -> str:
        """
        Get current persona for a user.
        
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
            List of persona names
        """
        return list(self.personas.keys())
    
    def load_persona(self, persona_name: str, file_path: str) -> bool:
        """
        Load persona configuration from a file.
        
        Args:
            persona_name: Name of the persona
            file_path: Path to persona configuration file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Persona file not found: {file_path}")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Validate config
            if not isinstance(config, dict):
                logger.error(f"Invalid persona format in {file_path}")
                return False
                
            # Store in personas dictionary
            self.personas[persona_name] = config
            logger.debug(f"Loaded persona: {persona_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading persona {persona_name}: {e}")
            return False
            
    def get_persona_config(self, persona_name: str) -> Optional[Dict[str, Any]]:
        """
        Get persona configuration.
        
        Args:
            persona_name: Name of the persona
            
        Returns:
            Persona configuration dictionary or None if not found
        """
        return self.personas.get(persona_name)
    
    def set_persona(self, user_id: int, persona_name: str) -> bool:
        """
        Set persona for a user (alias for set_user_persona).
        
        Args:
            user_id: User ID
            persona_name: Persona name
            
        Returns:
            True if set successfully, False otherwise
        """
        return self.set_user_persona(user_id, persona_name)

# Create singleton instance
persona_manager = PersonaManager()

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
            logger.warning(f"No persona data found for: {persona_type}")
            return _get_fallback_persona_context(persona_type)
            
        # Extract relevant sections - UPDATED to handle both new and old formats
        context = ""
        
        # Add name and description if available
        if "name" in persona_data:
            context += f"Name: {persona_data['name']}\n"
            
        if "description" in persona_data:
            context += f"{persona_data['description']}\n\n"
            
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
            sp = persona_data["speech_patterns"]
            
            if "prefix" in sp and sp["prefix"]:
                speech_patterns.append(f"Often starts sentences with: {', '.join(sp['prefix'][:3])}")
                
            if "suffix" in sp and sp["suffix"]:
                speech_patterns.append(f"Often ends sentences with: {', '.join(sp['suffix'][:3])}")
                
            if "filler" in sp and sp["filler"]:
                speech_patterns.append(f"Uses phrases like: {', '.join(sp['filler'][:3])}")
                    
        if speech_patterns:
            context += f"Speech Pattern: {'; '.join(speech_patterns)}\n"
            
        # Extract emotional expressions
        emotions = []
        
        # Check in traits first
        if "emotions" in traits:
            emotions.extend(traits["emotions"])
            
        # Check for emotional_patterns (new format)
        if "emotional_patterns" in persona_data:
            for emotion, pattern in persona_data["emotional_patterns"].items():
                if isinstance(pattern, str):
                    emotions.append(f"When {emotion}: {pattern}")
                    
        if emotions:
            context += f"Emotional Expression: {'; '.join(emotions[:3])}\n"
        
        # Add roleplay instructions if available
        if "roleplay_actions" in persona_data:
            context += "Roleplay actions:\n"
            
            # Get up to 3 random action categories
            categories = list(persona_data["roleplay_actions"].keys())
            selected_categories = random.sample(categories, min(3, len(categories)))
            
            for category in selected_categories:
                actions = persona_data["roleplay_actions"][category]
                if actions:
                    example = random.choice(actions)
                    context += f"- When {category}: {example}\n"
        
        # Add response examples if available
        if "responses" in persona_data:
            context += "\nResponse examples:\n"
            
            # Get up to 2 random response categories
            categories = list(persona_data["responses"].keys())
            selected_categories = random.sample(categories, min(2, len(categories)))
            
            for category in selected_categories:
                responses = persona_data["responses"][category]
                if responses:
                    example = random.choice(responses)
                    # Clean up placeholders
                    example = example.replace("{username}", "user")
                    context += f"- When {category}: {example}\n"
                    
        # Add Russian expressions if available
        if "russian_expressions" in persona_data and isinstance(persona_data["russian_expressions"], list):
            expressions = persona_data["russian_expressions"]
            if expressions:
                # Select a few random expressions
                selected = random.sample(expressions, min(3, len(expressions)))
                context += f"\nOccasionally uses Russian expressions like: {', '.join(selected)}\n"
        
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
            yaml_files = list(PERSONA_DIR.glob("*.yaml")) + list(PERSONA_DIR.glob("*.yml"))
            logger.debug(f"Available persona files: {[f.name for f in yaml_files]}")
        except Exception:
            logger.debug("Could not list available persona files")
            
        return {}
        
    try:
        # Load YAML data
        with open(persona_path, 'r', encoding='utf-8') as f:
            persona_data = yaml.safe_load(f)
            
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
        # Find all YAML files
        yaml_files = list(PERSONA_DIR.glob("*.yaml")) + list(PERSONA_DIR.glob("*.yml"))
        
        for file_path in yaml_files:
            try:
                # Skip moods.yaml as it's not a persona file
                if file_path.stem.lower() == "moods":
                    continue
                    
                persona_name = file_path.stem.lower()
                persona_data = _load_persona_template(persona_name)
                if persona_data:
                    personas[persona_name] = persona_data
            except Exception as e:
                logger.error(f"Error loading persona {file_path.name}: {e}")
                
        return personas
        
    except Exception as e:
        logger.error(f"Error loading all personas: {e}")
        return {}

def init_personas() -> bool:
    """
    Initialize persona system by pre-loading all persona configurations.
    
    This function loads all persona YAML files from the config/persona directory
    and initializes the persona_manager with them.
    
    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        logger.info("Initializing persona system...")
        
        # Ensure persona directory exists
        if not PERSONA_DIR.exists():
            logger.error(f"Persona directory not found: {PERSONA_DIR}")
            return False
            
        # Find all YAML files
        persona_files = list(PERSONA_DIR.glob("*.yaml")) + list(PERSONA_DIR.glob("*.yml"))
        
        if not persona_files:
            logger.warning(f"No persona files found in {PERSONA_DIR}")
            return False
            
        # Load all personas
        loaded_count = 0
        for persona_file in persona_files:
            try:
                # Skip moods.yaml as it's not a persona file
                if persona_file.stem.lower() == "moods":
                    continue
                    
                # Load the persona
                persona_name = persona_file.stem.lower()
                success = persona_manager.load_persona(persona_name, str(persona_file))
                
                if success:
                    loaded_count += 1
                    logger.info(f"Loaded persona: {persona_name}")
                else:
                    logger.warning(f"Failed to load persona: {persona_name}")
            except Exception as e:
                logger.error(f"Error loading persona {persona_file.name}: {e}")
        
        logger.info(f"Initialized {loaded_count} personas successfully")
        return loaded_count > 0
    except Exception as e:
        logger.error(f"Error initializing personas: {e}", exc_info=True)
        return False