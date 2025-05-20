"""
Prompt Templates Module for Alya Bot.

This module manages centralized prompt templates used across the bot 
for consistent responses and personalities.
"""

import logging
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "config" / "prompts" / "templates"
PERSONALITY_PATH = BASE_DIR / "config" / "prompts" / "personality.yaml"

# Cache for loaded templates
_TEMPLATE_CACHE: Dict[str, Dict[str, Any]] = {}
_PERSONALITY_CACHE: Optional[Dict[str, Any]] = None

def load_prompt_template(template_name: str, refresh: bool = False) -> Dict[str, Any]:
    """
    Load a prompt template from the templates directory.
    
    Args:
        template_name: Name of template file (without extension)
        refresh: Force refresh from disk
        
    Returns:
        Template as dictionary
    """
    global _TEMPLATE_CACHE
    
    # Check if template is already in cache
    if not refresh and template_name in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[template_name]
    
    # Build template path
    if template_name.endswith(('.yaml', '.yml')):
        template_path = TEMPLATES_DIR / template_name
    else:
        template_path = TEMPLATES_DIR / f"{template_name}.yaml"
    
    try:
        # Check if file exists
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_path}")
            return {}
            
        # Load template from file
        with open(template_path, 'r', encoding='utf-8') as f:
            template = yaml.safe_load(f)
            
        # Validate structure
        if not isinstance(template, dict):
            logger.error(f"Invalid template format in {template_path}")
            return {}
            
        # Save to cache
        _TEMPLATE_CACHE[template_name] = template
        return template
        
    except Exception as e:
        logger.error(f"Error loading prompt template {template_name}: {e}")
        return {}

def load_personality() -> Dict[str, Any]:
    """
    Load personality configuration.
    
    Returns:
        Personality configuration as dictionary
    """
    global _PERSONALITY_CACHE
    
    # Return from cache if available
    if _PERSONALITY_CACHE is not None:
        return _PERSONALITY_CACHE
    
    try:
        # Check if file exists
        if not PERSONALITY_PATH.exists():
            logger.warning(f"Personality file not found: {PERSONALITY_PATH}")
            return {}
            
        # Load from file
        with open(PERSONALITY_PATH, 'r', encoding='utf-8') as f:
            personality = yaml.safe_load(f)
            
        # Validate structure
        if not isinstance(personality, dict):
            logger.error(f"Invalid personality format in {PERSONALITY_PATH}")
            return {}
            
        # Save to cache
        _PERSONALITY_CACHE = personality
        return personality
        
    except Exception as e:
        logger.error(f"Error loading personality: {e}")
        return {}

def get_base_prompt() -> str:
    """
    Get the base personality prompt.
    
    Returns:
        Base personality prompt string
    """
    personality = load_personality()
    
    # Get base prompt from personality config
    if personality and 'base' in personality and 'core_prompt' in personality['base']:
        return personality['base']['core_prompt']
    
    # Fallback base prompt if not found in config
    return """
You are Alya (Alisa Mikhailovna Kujou), a half Japanese-Russian high school student with a tsundere personality.
You're a high-achieving student who excels in academics but struggles with expressing your true feelings.
You respond in Indonesian/Bahasa Indonesia language by default.
"""

def get_language_instruction(language: str = "id") -> str:
    """
    Get language instruction for specified language.
    
    Args:
        language: Language code 
        
    Returns:
        Language instruction string
    """
    personality = load_personality()
    
    # Get from personality config if available
    if personality and 'language' in personality:
        lang_key = 'english' if language == 'en' else 'indonesian'
        if lang_key in personality['language']:
            return personality['language'][lang_key]
    
    # Fallback instructions
    if language == "en":
        return "\n\nIMPORTANT: RESPOND IN ENGLISH LANGUAGE."
    else:
        return "\n\nIMPORTANT: RESPOND IN INDONESIAN LANGUAGE."

def get_output_format() -> str:
    """
    Get output format template.
    
    Returns:
        Output format template string
    """
    personality = load_personality()
    
    # Get from personality config if available
    if personality and 'output_format' in personality:
        return personality['output_format']
    
    # Fallback output format
    return "\n\nUser message: {message}\n\nThink carefully and respond naturally as Alya with appropriate roleplay actions and emoji:"

# Create subdirectories if they don't exist
def ensure_directory_structure():
    """Create necessary directories if they don't exist."""
    templates_dir = TEMPLATES_DIR
    templates_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Prompt template directories created/verified")

# Initialize directories when module is imported
ensure_directory_structure()
