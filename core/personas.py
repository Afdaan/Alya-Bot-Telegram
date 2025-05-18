"""
Persona management for Alya Bot.

This module handles loading and switching between different personas
for the bot's conversational style.
"""

import os
import yaml
import logging
import random
import re
from typing import Dict, List, Optional, Any, Union
import requests
from datetime import datetime
from pathlib import Path

# Initialize logger
logger = logging.getLogger(__name__)

# Define constants
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PERSONA_DIR = os.path.join(CONFIG_DIR, "personas")

# Required files for the new structure - updated paths to match new structure
REQUIRED_FILES = [
    os.path.join(CONFIG_DIR, "roasts.yaml"),
    os.path.join(CONFIG_DIR, "responses.yaml"),
    os.path.join(PERSONA_DIR, "waifu.yaml"),
    os.path.join(PERSONA_DIR, "toxic.yaml"),
    os.path.join(PERSONA_DIR, "smart.yaml")
]

# Cache for loaded personas
_PERSONA_CACHE = {}

class ConfigError(Exception):
    """Exception raised when configuration files are missing or invalid."""
    pass

class PersonaManager:
    """Class to manage personas from YAML files."""
    
    def __init__(self, validate_required: bool = True):
        """
        Initialize the persona manager.
        
        Args:
            validate_required: Whether to validate required config files
        """
        self.personas = {}
        self.responses = {}
        self.roasts = {}
        self.templates = {}
        
        # Create necessary directories if not exist
        self._ensure_directories()
            
        # Validate required files before loading
        if validate_required:
            self._validate_required_files()
            
        # Load all data
        self._load_all_data()
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            PERSONA_DIR,
            CONFIG_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
    
    def _validate_required_files(self) -> None:
        """Validate that all required YAML files exist, or exit with error."""
        missing_files = [f for f in REQUIRED_FILES if not os.path.exists(f)]
        
        if missing_files:
            error_msg = "ERROR: Missing required configuration files:\n"
            for file in missing_files:
                error_msg += f"- {file}\n"
            error_msg += "\nPlease create these files or run the setup script."
            logger.error(error_msg)
            raise ConfigError(error_msg)
    
    def _load_all_data(self) -> None:
        """Load all persona-related data."""
        self._load_personas()
        self._load_responses()
        self._load_roasts()
    
    def _load_personas(self) -> None:
        """Load all persona YAML files."""
        for filename in os.listdir(PERSONA_DIR):
            if not filename.endswith(('.yaml', '.yml')):
                continue
                
            name = os.path.splitext(filename)[0]
            filepath = os.path.join(PERSONA_DIR, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    self.personas[name] = yaml.safe_load(file)
                    logger.info(f"Loaded persona: {name}")
            except Exception as e:
                logger.error(f"Error loading persona {name}: {e}")
        
        if not self.personas:
            logger.warning("No persona files found. Creating defaults...")
            self._create_default_personas()
    
    def _load_responses(self) -> None:
        """Load responses YAML file."""
        responses_file = os.path.join(CONFIG_DIR, "responses.yaml")
        if os.path.exists(responses_file):
            try:
                with open(responses_file, 'r', encoding='utf-8') as file:
                    self.responses = yaml.safe_load(file) or {}
                    logger.info("Loaded responses file")
            except Exception as e:
                logger.error(f"Error loading responses: {e}")
    
    def _load_roasts(self) -> None:
        """Load roasts YAML file."""
        roasts_file = os.path.join(CONFIG_DIR, "roasts.yaml")
        if os.path.exists(roasts_file):
            try:
                with open(roasts_file, 'r', encoding='utf-8') as file:
                    self.roasts = yaml.safe_load(file) or {}
                    logger.info("Loaded roasts file")
            except Exception as e:
                logger.error(f"Error loading roasts: {e}")
    
    def _create_default_personas(self) -> None:
        """Create default persona files if none exist."""
        default_personas = {
            "waifu": {
                "name": "Alya Kujou",
                "description": "Half Japanese-Russian high school student who is intelligent and slightly tsundere",
                "traits": [
                    "Intelligent and analytical",
                    "Tsundere tendencies when flustered",
                    "Values academic excellence"
                ],
                "speaking_style": {
                    "emoji_set": ["✨", "💫", "😳", "💕"],
                    "emoji_max": 2
                },
                "rules": [
                    "Natural mixing of professional & subtle cuteness",
                    "Maximum 2 emoji per response",
                    "Keep responses concise and on-topic"
                ]
            },
            "toxic": {
                "name": "Toxic Queen Alya",
                "description": "Extremely toxic, savage, and brutal version of Alya",
                "traits": [
                    "Brutally honest without filter",
                    "Enjoys making savage roasts",
                    "Zero patience for stupidity"
                ],
                "speaking_style": {
                    "emoji_set": ["🤮", "💀", "🤡", "💅"],
                    "emoji_max": 2
                },
                "rules": [
                    "Always be savage and brutal",
                    "Never apologize or show remorse",
                    "Use creative insults"
                ]
            },
            "smart": {
                "name": "Professor Alya",
                "description": "Highly analytical and educational version of Alya",
                "traits": [
                    "Brilliant analytical mind",
                    "Values knowledge and accuracy",
                    "Methodical and thorough"
                ],
                "speaking_style": {
                    "emoji_set": ["📚", "🔍", "💡", "🧠"],
                    "emoji_max": 2
                },
                "rules": [
                    "Provide detailed and accurate explanations",
                    "Structure content in logical steps",
                    "Use academic terminology appropriately"
                ]
            }
        }
        
        for name, data in default_personas.items():
            filepath = os.path.join(PERSONA_DIR, f"{name}.yaml")
            try:
                with open(filepath, 'w', encoding='utf-8') as file:
                    yaml.safe_dump(data, file, default_flow_style=False)
                self.personas[name] = data
                logger.info(f"Created default persona: {name}")
            except Exception as e:
                logger.error(f"Error creating default persona {name}: {e}")
    
    def get_persona_prompt(self, persona_type: str = "waifu", language: str = "id") -> str:
        """
        Get natural prompt for a specific persona type, avoiding templates.
        
        Args:
            persona_type: Type of persona (waifu, toxic, smart)
            language: Language code (id/en)
            
        Returns:
            Natural freestyle prompt for the persona
        """
        if persona_type not in self.personas:
            persona_type = "waifu"  # Default fallback
            
        persona = self.personas[persona_type]
        
        # Create a more natural, free-flowing prompt
        if persona_type == "waifu":
            prompt = """
For this conversation, embrace your core personality as a half Japanese-Russian high school student.
Your tsundere tendencies mean you're initially reserved but secretly caring.
You're exceptionally intelligent and analytical, and you take pride in academic excellence.
Remember to use no more than 2 emoji in your response (e.g., ✨💫😳💕).
Be yourself naturally, not a template-following bot."""
            
        elif persona_type == "toxic":
            prompt = """
For this conversation, unleash your brutally savage personality.
You're extremely critical, judgmental, and don't hold back your opinions.
You enjoy making creative insults and pointing out flaws with a mix of wit and harshness.
Use vulgar language freely when appropriate.
Remember to use no more than 2 emoji in your response (e.g., 🤮💀🤡💅).
Be naturally savage, not a template-following bot."""
            
        elif persona_type == "smart":
            prompt = """
For this conversation, emphasize your academic and analytical side.
You're methodical and thorough in explanations, using precise terminology.
Present information in structured yet natural way, like a knowledgeable tutor.
Your explanations should be detailed but accessible.
Remember to use no more than 2 emoji in your response (e.g., 📚🔍📊💡).
Be naturally intellectual, not a template-following bot."""
            
        else:
            # Generic fallback prompt
            prompt = """
For this conversation, be yourself - the intelligent, slightly tsundere high school student.
Respond naturally with your own unique personality.
Remember to use no more than 2 emoji in your response.
Be naturally conversational, not a template-following bot."""
        
        return prompt
    
    def get_roast_component(self, component_type: str, subtype: str = "general") -> List[str]:
        """
        Get roast component from unified roasts file.
        
        Args:
            component_type: Type of component (intros, criteria, outros, etc)
            subtype: Subtype for certain components (general, github)
            
        Returns:
            List of components or empty list
        """
        if not self.roasts:
            return []
            
        if component_type == "criteria" and subtype in self.roasts.get("criteria", {}):
            return self.roasts["criteria"][subtype]
        elif component_type in self.roasts:
            return self.roasts[component_type]
        return []

    def get_response_template(self, template_key: str, persona_type: str = "waifu", **kwargs) -> str:
        """
        Get response template and format it with variables.
        
        Args:
            template_key: Key to identify template (category.subcategory)
            persona_type: Type of persona to apply
            **kwargs: Variables for template substitution
            
        Returns:
            Formatted response string
        """
        # Split the key into parts
        parts = template_key.split('.')
        
        # Handle roleplay special case
        if template_key == "action":
            persona_type = persona_type if persona_type in self.personas else "waifu"
            roleplay = self.responses.get("roleplay", {})
            templates = roleplay.get(persona_type, roleplay.get("waifu", []))
            if templates:
                return random.choice(templates)
            return "*doing something*"
            
        # Navigate to correct template
        current = self.responses
        for part in parts:
            if part in current:
                current = current[part]
            else:
                # Template not found
                logger.warning(f"Template not found: {template_key}")
                return f"Hmm... ({template_key})"
        
        # Handle list vs string templates
        if isinstance(current, list):
            template = random.choice(current)
        else:
            template = str(current)
            
        # Apply any persona traits
        template = self._apply_persona_traits(template, persona_type)
        
        # Substitute variables
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            template = template.replace(placeholder, str(value))
            
        return template
    
    def _apply_persona_traits(self, template: str, persona_type: str) -> str:
        """Apply persona-specific traits to template."""
        # Get persona traits
        if persona_type not in self.personas:
            return template
            
        persona = self.personas[persona_type]
        
        # Apply emoji if defined in persona
        if "speaking_style" in persona and "emoji_set" in persona["speaking_style"]:
            emoji_set = persona["speaking_style"]["emoji_set"]
            # Add random emoji if template doesn't already have one
            if emoji_set and not any(emoji in template for emoji in emoji_set):
                template += f" {random.choice(emoji_set)}"
        
        return template

# Create singleton instance for global use
try:
    persona_manager = PersonaManager()
except ConfigError as e:
    logger.critical(f"Fatal error initializing PersonaManager: {e}")
    import sys
    sys.exit(1)

# Public API function for compatibility
def get_persona_context(persona: str = "waifu", language: str = "id") -> str:
    """Get persona context with language awareness."""
    return persona_manager.get_persona_prompt(persona, language)