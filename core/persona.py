"""
Persona manager for Alya Bot to handle persona loading and response formatting.
Supports multilingual responses through language-specific templates.
"""
import os
import logging
import random
from typing import Dict, List, Any, Optional
import yaml
import datetime

from config.settings import PERSONA_DIR, DEFAULT_PERSONA, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class PersonaManager:
    """Manager for bot personas loaded from YAML files."""
    
    # Define the class attribute _instance here, outside of any method
    _instance = None
    
    def __init__(self) -> None:
        """Initialize the persona manager."""
        self.personas: Dict[str, Dict[str, Any]] = {}
        self.load_personas()
        
    def __new__(cls):
        """Implement singleton pattern to prevent multiple loads of the same files.
        
        Returns:
            Singleton instance
        """
        if cls._instance is None:
            cls._instance = super(PersonaManager, cls).__new__(cls)
            cls._instance.personas = {}
        return cls._instance
        
    def load_personas(self) -> None:
        """Load all persona YAML files from the persona directory."""
        # Skip if already loaded
        if self.personas:
            return
            
        try:
            # Ensure persona directory exists
            if not os.path.exists(PERSONA_DIR):
                logger.error(f"Persona directory {PERSONA_DIR} does not exist")
                return
                
            # Load each YAML file in the directory
            for filename in os.listdir(PERSONA_DIR):
                if filename.endswith('.yml') or filename.endswith('.yaml'):
                    persona_name = filename.split('.')[0]
                    filepath = os.path.join(PERSONA_DIR, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            persona_data = yaml.safe_load(file)
                            self.personas[persona_name] = persona_data
                            logger.info(f"Loaded persona: {persona_name}")
                    except Exception as e:
                        logger.error(f"Error loading persona {persona_name}: {str(e)}")
            
            logger.info(f"Loaded {len(self.personas)} personas")
            
            # Ensure default persona exists
            if DEFAULT_PERSONA not in self.personas:
                logger.warning(f"Default persona '{DEFAULT_PERSONA}' not found")
                
        except Exception as e:
            logger.error(f"Error loading personas: {str(e)}")
            
    def get_persona(self, persona_name: Optional[str] = None) -> Dict[str, Any]:
        """Get a persona by name.
        
        Args:
            persona_name: Name of the persona to load, or None for default
            
        Returns:
            Persona data dictionary
        """
        name = persona_name or DEFAULT_PERSONA
        if name in self.personas:
            return self.personas[name]
        else:
            # Fall back to default
            logger.warning(f"Persona '{name}' not found, using default")
            return self.personas.get(DEFAULT_PERSONA, {})
            
    def get_greeting(self, persona_name: Optional[str] = None, username: str = "user") -> str:
        """Get a time-appropriate greeting message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the greeting template
            
        Returns:
            Formatted greeting message
        """
        persona = self.get_persona(persona_name)
        
        # Get time-appropriate greeting template
        now = datetime.datetime.now()
        hour = now.hour
        
        time_of_day = "default"
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        elif 21 <= hour < 24 or 0 <= hour < 5:
            time_of_day = "night"
        
        # Check if greeting templates are in the new format first
        greeting_templates = persona.get("greeting", {})
        
        # Handle the new format with direct time of day keys
        if isinstance(greeting_templates, dict) and time_of_day in greeting_templates:
            greeting = greeting_templates.get(time_of_day, greeting_templates.get("default", f"Halo {username}!"))
        else:
            # Fall back to old format with nested conversation_contexts structure if needed
            contexts = persona.get("conversation_contexts", {})
            greeting_contexts = contexts.get("greeting", {})
            greeting = greeting_contexts.get(time_of_day, greeting_contexts.get("default", f"Halo {username}!"))
        
        # Replace username
        return greeting.format(username=username)
        
    def get_farewell(self, persona_name: Optional[str] = None, username: str = "user") -> str:
        """Get a random farewell message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the farewell template
            
        Returns:
            Formatted farewell message
        """
        persona = self.get_persona(persona_name)
        
        # Handle farewell templates
        farewell_templates = persona.get("templates", {}).get("farewell", {})
        
        if isinstance(farewell_templates, dict):
            # Time-based farewell
            now = datetime.datetime.now()
            hour = now.hour
            
            farewell_type = "default"
            if 17 <= hour < 24 or 0 <= hour < 5:
                farewell_type = "evening" 
            else:
                farewell_type = "casual"
                
            farewell = farewell_templates.get(farewell_type, farewell_templates.get("default", f"Sampai jumpa, {username}!"))
            return farewell.format(username=username)
        else:
            # Default fallback
            return f"Sampai jumpa, {username}!"
        
    def get_error_message(self, persona_name: Optional[str] = None, 
                           username: str = "user", language: str = None) -> str:
        """Get an error message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the template
            language: Language code ('id' or 'en'), defaults to DEFAULT_LANGUAGE
            
        Returns:
            Formatted error message
        """
        persona = self.get_persona(persona_name)
        error_msg = self._get_language_template(persona, "error_message", language)
        
        if not error_msg:
            error_msg = "Maaf {username}, terjadi kesalahan..."
            
        return error_msg.format(username=username)
        
    def get_help_message(self, persona_name: Optional[str] = None, 
                        username: str = "user", prefix: str = "!ai", 
                        language: str = None) -> str:
        """Get the help message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the template
            prefix: Command prefix to insert in the template
            language: Language code ('id' or 'en'), defaults to DEFAULT_LANGUAGE
            
        Returns:
            Formatted help message
        """
        persona = self.get_persona(persona_name)
        help_msg = self._get_language_template(persona, "help_message", language)
        
        # If no help message in persona, create a basic one
        if not help_msg:
            help_msg = (
                "Halo {username}!\n\n"
                "Kamu bisa menggunakan:\n"
                "• {prefix} [pesan] - Bicara dengan Alya\n"
                "• {prefix} reset - Hapus memori percakapan\n"
                "• /help - Tampilkan bantuan ini\n"
                "• !roast - Minta Alya untuk meledekmu dengan candaan\n"
                "• !gitroast [username] - Minta Alya untuk meledek profil GitHub"
            )
            
        return help_msg.format(username=username, prefix=prefix)
        
    def get_memory_reset_message(self, persona_name: Optional[str] = None, username: str = "user") -> str:
        """Get the memory reset message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the template
            
        Returns:
            Formatted memory reset message
        """
        persona = self.get_persona(persona_name)
        reset_msg = persona.get("templates", {}).get("memory_reset", 
                                                     "Alya sudah melupakan percakapan sebelumnya dengan {username}...")
        return reset_msg.format(username=username)
    
    def get_mood_response(self, mood: str, persona_name: Optional[str] = None, 
                          username: str = "user") -> Optional[str]:
        """Get a random response for a specific mood.
        
        Args:
            mood: The mood for the response (e.g., "tsundere_cold", "dere_caring")
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the template
            
        Returns:
            Formatted mood response or None if mood not found
        """
        persona = self.get_persona(persona_name)
        mood_responses = persona.get("emotions", {}).get(mood, {}).get("responses", [])
        
        if not mood_responses:
            return None
            
        response = random.choice(mood_responses)
        return response.format(username=username)
    
    def get_system_prompt(self, persona_name: Optional[str] = None) -> str:
        """Get the system prompt for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            
        Returns:
            System prompt for Gemini API
        """
        persona = self.get_persona(persona_name)
        system_prompt = persona.get("system_prompt", "")
        
        # If no system prompt, construct a basic one
        if not system_prompt:
            name = persona.get("name", "Alya")
            traits = persona.get("traits", ["helpful", "friendly"])
            traits_str = ", ".join(traits)
            
            system_prompt = (
                f"Kamu adalah {name}. "
                f"Sifatmu: {traits_str}. "
                "Kamu selalu menjawab dalam bahasa Indonesia. "
                "Berikan jawaban yang singkat dan bermanfaat."
            )
            
        return system_prompt

    def get_full_system_prompt(self, persona_name: Optional[str] = None, 
                              language: str = None) -> str:
        """Return the merged system prompt and enhanced instructions from persona YAML.

        Args:
            persona_name: Name of the persona to use, or None for default
            language: Language code ('id' or 'en'), defaults to DEFAULT_LANGUAGE

        Returns:
            Full system prompt string (system_prompt + enhanced_system_instructions)
        """
        persona = self.get_persona(persona_name)
        base_prompt = persona.get("system_prompt", "")
        enhanced = persona.get("enhanced_system_instructions", "")
        
        # If there are language-specific templates in gemini_prompt_template, use them
        lang = language or DEFAULT_LANGUAGE
        lang_prompt = persona.get("gemini_prompt_template", {}).get(lang, {}).get("prompt", "")
        
        # Combine all prompt parts
        if lang_prompt:
            return f"{base_prompt}\n\n{enhanced}\n\n{lang_prompt}".strip()
        else:
            return f"{base_prompt}\n\n{enhanced}".strip()
    
    def get_roleplay_action(self, emotion: str, mood: str = None, 
                           persona_name: Optional[str] = None) -> Optional[str]:
        """Get a roleplay action for the given emotion and mood.
        
        Args:
            emotion: The emotion for the action (e.g., "joy", "anger")
            mood: The mood for the action (e.g., "tsundere_cold"), or None
            persona_name: Name of the persona to use, or None for default
            
        Returns:
            Roleplay action or None if not found
        """
        persona = self.get_persona(persona_name)
        
        # Try to get from mood first if specified
        if mood:
            mood_data = persona.get("emotions", {}).get(mood, {})
            expressions = mood_data.get("expressions", [])
            if expressions:
                return random.choice(expressions)
        
        # Fall back to emotion
        for mood_name, mood_data in persona.get("emotions", {}).items():
            if emotion.lower() in mood_name.lower():
                expressions = mood_data.get("expressions", [])
                if expressions:
                    return random.choice(expressions)
        
        # Generic fallback
        return None
    
    def get_emoji_for_emotion(self, emotion: str, mood: str = None, 
                             persona_name: Optional[str] = None) -> Optional[str]:
        """Get an emoji for the given emotion and mood.
        
        Args:
            emotion: The emotion (e.g., "joy", "anger")
            mood: The mood (e.g., "tsundere_cold"), or None
            persona_name: Name of the persona to use, or None for default
            
        Returns:
            Emoji or None if not found
        """
        persona = self.get_persona(persona_name)
        
        # Try to get from mood first if specified
        if mood:
            mood_data = persona.get("emotions", {}).get(mood, {})
            emojis = mood_data.get("emoji", [])
            if emojis:
                return random.choice(emojis)
        
        # Fall back to emotion-based lookup
        for mood_name, mood_data in persona.get("emotions", {}).items():
            if emotion.lower() in mood_name.lower():
                emojis = mood_data.get("emoji", [])
                if emojis:
                    return random.choice(emojis)
        
        # Generic fallback
        return None
    
    def _get_language_template(self, persona: Dict[str, Any], template_key: str, 
                           language: str = None) -> str:
        """Get a language-specific template from persona.
        
        Args:
            persona: Persona data dictionary
            template_key: Template key to retrieve
            language: Language code ('id' or 'en'), defaults to DEFAULT_LANGUAGE
            
        Returns:
            Template string in the requested language
        """
        language = language or DEFAULT_LANGUAGE
        
        # Try to get from language-specific template first
        lang_templates = persona.get("languages", {}).get(language, {}).get("templates", {})
        template = lang_templates.get(template_key, "")
        
        if not template:
            # Fallback to default language
            fallback_lang = "id" if DEFAULT_LANGUAGE == "id" else "en"
            default_templates = persona.get("languages", {}).get(fallback_lang, {}).get("templates", {})
            template = default_templates.get(template_key, "")
            
        if not template:
            # Legacy fallback (for backward compatibility)
            template = persona.get("templates", {}).get(template_key, "")
            
        return template
        
    def _get_language_speech_pattern(self, persona: Dict[str, Any], pattern_key: str, 
                                   language: str = None) -> str:
        """Get a language-specific speech pattern from persona.
        
        Args:
            persona: Persona data dictionary
            pattern_key: Speech pattern key to retrieve
            language: Language code ('id' or 'en'), defaults to DEFAULT_LANGUAGE
            
        Returns:
            Speech pattern string in the requested language
        """
        language = language or DEFAULT_LANGUAGE
        
        # Try to get from language-specific patterns first
        lang_patterns = persona.get("languages", {}).get(language, {}).get("speech_patterns", {})
        pattern = lang_patterns.get(pattern_key, "")
        
        if not pattern:
            # Fallback to default language
            fallback_lang = "id" if DEFAULT_LANGUAGE == "id" else "en"
            default_patterns = persona.get("languages", {}).get(fallback_lang, {}).get("speech_patterns", {})
            pattern = default_patterns.get(pattern_key, "")
            
        if not pattern:
            # Legacy fallback (for backward compatibility)
            pattern = persona.get("emotional_authenticity", {}).get("speech_patterns", {}).get(pattern_key, "")
            
        return pattern
