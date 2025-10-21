"""
Persona manager for Alya Bot to handle persona loading and response formatting.
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
    _instance = None

    def __init__(self) -> None:
        """Initialize the persona manager."""
        self.personas: Dict[str, Dict[str, Any]] = {}
        self.persona_data: Dict[str, Any] = {}  # Store full YAML for default persona
        self.load_personas()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PersonaManager, cls).__new__(cls)
            cls._instance.personas = {}
            cls._instance.persona_data = {}
        return cls._instance

    def load_personas(self) -> None:
        if self.personas:
            return
        try:
            if not os.path.exists(PERSONA_DIR):
                logger.error(f"Persona directory {PERSONA_DIR} does not exist")
                return
            for filename in os.listdir(PERSONA_DIR):
                if filename.endswith('.yml') or filename.endswith('.yaml'):
                    persona_name = filename.split('.')[0]
                    filepath = os.path.join(PERSONA_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            persona_data = yaml.safe_load(file)
                            self.personas[persona_name] = persona_data
                            if persona_name == DEFAULT_PERSONA:
                                self.persona_data = persona_data  # Store full YAML for default
                            logger.info(f"Loaded persona: {persona_name}")
                    except Exception as e:
                        logger.error(f"Error loading persona {persona_name}: {str(e)}")
            logger.info(f"Loaded {len(self.personas)} personas")
            if DEFAULT_PERSONA not in self.personas:
                logger.warning(f"Default persona '{DEFAULT_PERSONA}' not found")
        except Exception as e:
            logger.error(f"Error loading personas: {str(e)}")

    def get_persona(self, persona_name: Optional[str] = None) -> Dict[str, Any]:
        name = persona_name or DEFAULT_PERSONA
        if name in self.personas:
            return self.personas[name]
        else:
            logger.warning(f"Persona '{name}' not found, using default")
            return self.personas.get(DEFAULT_PERSONA, {})

    def get_section(self, section: str, persona_name: Optional[str] = None) -> Any:
        """Get a section from the persona YAML as a dict or value."""
        persona = self.get_persona(persona_name)
        return persona.get(section, None)

    def get_full_persona(self, persona_name: Optional[str] = None) -> Dict[str, Any]:
        """Return the full persona YAML as a dict."""
        return self.get_persona(persona_name)

    def get_greeting(self, persona_name: Optional[str] = None, username: str = "user") -> str:
        """Get a time-appropriate greeting message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the greeting template
            
        Returns:
            Formatted greeting message
        """
        persona = self.get_persona(persona_name)
        
        # Get current hour
        current_hour = datetime.datetime.now().hour
        
        # Determine time of day
        if 5 <= current_hour < 12:
            time_of_day = "morning"
        elif 12 <= current_hour < 18:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
            
        # Get greeting from persona, with fallback
        greetings = persona.get("greetings", {})
        greeting_template = greetings.get(time_of_day, "Hello, {username}")
        
        return greeting_template.format(username=username)
        
    def get_error_message(self, username: str = "user", lang: str = DEFAULT_LANGUAGE, persona_name: Optional[str] = None) -> str:
        """Get a generic error message for the given persona.
        
        Args:
            username: Username to insert in the error template
            lang: Language for the error message
            persona_name: Name of the persona to use, or None for default
            
        Returns:
            Formatted error message
        """
        persona = self.get_persona(persona_name)
        errors = persona.get("errors", {})
        
        # Get language-specific errors, fallback to default language or Alya-style generic message
        lang_errors = errors.get(lang, errors.get(DEFAULT_LANGUAGE, {}))
        
        # Use Alya-style error message as fallback instead of generic one
        if lang == DEFAULT_LANGUAGE:
            default_error = "Eh... что?! Ada yang error nih... 😳\n\nB-bukan salahku ya! Sistemnya lagi bermasalah... дурак технологии! 💫\n\nCoba lagi nanti, {username}-kun!"
        else:
            default_error = "Eh... что?! Something went wrong... 😳\n\nI-It's not my fault! The system is having issues... дурак технологии! 💫\n\nTry again later, {username}!"
            
        error_template = lang_errors.get("generic", default_error)
        
        return error_template.format(username=username)
    
    def get_chat_prompt(
        self,
        username: str,
        message: str,
        context: str,
        relationship_level: int,
        is_admin: bool,
        lang: str = DEFAULT_LANGUAGE,
        extra_sections: Optional[List[str]] = None
    ) -> str:
        """Construct a detailed chat prompt for Gemini, using multiple persona sections if needed.

        Args:
            username: User's name
            message: User's message
            context: Conversation context
            relationship_level: User's relationship level with Alya
            is_admin: Whether the user is an admin
            lang: The user's preferred language
            extra_sections: List of section names to include in prompt (besides system_prompt)
        Returns:
            The full prompt for Gemini
        """
        persona = self.get_persona()  # Use default persona for chat
        
        # Initialize prompt construction
        prompt_parts = []
        
        logger.debug(
            f"[Persona] Constructing chat prompt for user '{username}' "
            f"(level {relationship_level}, admin={is_admin}, lang={lang})"
        )
        
        # Always start with system_prompt if available
        system_prompt = persona.get("system_prompt", "").strip()
        if system_prompt:
            prompt_parts.append(system_prompt)
            logger.debug(f"[Persona] Added system_prompt ({len(system_prompt)} chars)")
        else:
            logger.warning("[Persona] No system_prompt found in persona YAML")
        
        # Inject connection_dynamics based on relationship level
        connection_dynamics = persona.get("connection_dynamics", {})
        if connection_dynamics:
            logger.debug(
                f"[Persona] Found connection_dynamics with "
                f"{len(connection_dynamics)} phases in YAML"
            )
            
            level_behavior = self._get_level_behavior(connection_dynamics, relationship_level)
            
            if level_behavior:
                # Serialize behavior config to YAML format for structured injection
                behavior_yaml = yaml.dump(level_behavior, allow_unicode=True, default_flow_style=False)
                prompt_parts.append(
                    f"\n# Current Relationship Level Behavior\n{behavior_yaml}"
                )
                logger.info(
                    f"[Persona] Successfully injected connection_dynamics for level {relationship_level}"
                )
            else:
                logger.warning(
                    f"[Persona] Failed to extract level behavior for level {relationship_level}. "
                    f"Gemini will use generic persona without level-specific guidance."
                )
        else:
            logger.warning(
                "[Persona] No connection_dynamics found in persona YAML. "
                "Level-based behavior adaptation is disabled."
            )
        
        # Optionally add extra sections (e.g. emotional_processing, smart_alya_enhancement, etc)
        if extra_sections:
            logger.debug(f"[Persona] Processing {len(extra_sections)} extra sections")
            for section in extra_sections:
                section_data = persona.get(section)
                if section_data:
                    section_yaml = yaml.dump(section_data, allow_unicode=True, default_flow_style=False)
                    prompt_parts.append(
                        f"\n# {section.replace('_', ' ').title()}\n{section_yaml}"
                    )
                    logger.debug(f"[Persona] Added extra section: {section}")
                else:
                    logger.debug(f"[Persona] Extra section '{section}' not found in YAML")
        
        # Fallback to old logic if system_prompt not found
        if not prompt_parts:
            logger.warning(
                "[Persona] No prompt_parts constructed from YAML. "
                "Falling back to legacy persona construction logic."
            )
            
            persona_lang = persona.get(lang, persona.get(DEFAULT_LANGUAGE, {}))
            base_instructions = persona_lang.get("base_instructions", "")
            personality_traits = "\n- ".join(persona_lang.get("personality_traits", []))
            relationship_instructions = self._get_relationship_instructions(persona_lang, relationship_level)
            response_format = persona_lang.get("response_format", "")
            russian_phrases = "\n- ".join([f"`{p}`: {d}" for p, d in persona_lang.get("russian_phrases", {}).items()])
            admin_note = persona_lang.get("admin_note", "") if is_admin else ""
            
            prompt_parts.append(f"""{base_instructions}

**Your Core Personality:**
- {personality_traits}

**Your Relationship with {username}:**
{relationship_instructions}
{admin_note}

**Russian Phrases You Can Use (sparingly, for emotional emphasis):**
- {russian_phrases}
""")
            logger.debug("[Persona] Constructed prompt using legacy fallback logic")
        
        # Combine all prompt parts
        prompt = "\n\n".join(prompt_parts)
        
        logger.debug(f"[Persona] Total prompt length: {len(prompt)} characters")
        
        # Convert language code to clear language name
        lang_name = "Bahasa Indonesia" if lang == "id" else "English"
        
        # Ultra-strict language instruction
        language_instruction = f"""
**CRITICAL LANGUAGE REQUIREMENT:**
- You MUST respond ENTIRELY in {lang_name}
- DO NOT use English in your response
- DO NOT mix languages
- ALL text, actions, and roleplay descriptions must be in {lang_name}
- If you accidentally write in English, immediately rewrite it in {lang_name}
"""
        
        prompt += f"\n\n**Conversation Context (Recent History):**\n---\n{context or 'This is the beginning of your conversation.'}\n---\n\n**User's Message:**\n> {message}\n\n{language_instruction}\n\n**Your Task:**\nRespond to {username} naturally as Alya, following ALL instructions above."
        
        logger.info(
            f"[Persona] Chat prompt constructed successfully: "
            f"{len(prompt)} total chars, "
            f"{len(prompt_parts)} sections, "
            f"level {relationship_level} behavior injected"
        )
        
        # Debug: Log full prompt if debug level enabled (useful for troubleshooting)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[Persona] Full prompt preview (first 500 chars):\n{prompt[:500]}...")
        
        return prompt.strip()

    def get_media_analysis_prompt(
        self,
        username: str,
        query: str,
        media_context: str,
        lang: str = DEFAULT_LANGUAGE
    ) -> str:
        """Construct a prompt for media analysis.
        
        Args:
            username: User's name
            query: User's query about the media
            media_context: The context extracted from the media (e.g., text from image)
            lang: The user's preferred language
            
        Returns:
            The full prompt for Gemini
        """
        persona = self.get_persona('analyze') # Use 'analyze' persona
        
        # Get language-specific persona details
        persona_lang = persona.get(lang, persona.get(DEFAULT_LANGUAGE, {}))

        base_instructions = persona_lang.get("base_instructions", "")
        analysis_guidelines = "\n- ".join(persona_lang.get("analysis_guidelines", []))
        response_format = persona_lang.get("response_format", "")

        prompt = f"""
{base_instructions}

**Analysis Guidelines:**
- {analysis_guidelines}

**Media Content Analysis:**
---
{media_context}
---

**User's Question:**
> {query}

**Your Task:**
Analyze the media content and answer {username}'s question in **{persona_lang.get('language_name', 'Bahasa Indonesia')}**.
{response_format}
"""
        return prompt.strip()

    def _get_level_behavior(self, connection_dynamics: Dict[str, Any], relationship_level: int) -> Optional[Dict[str, Any]]:
        """Extract behavior configuration for current relationship level from connection_dynamics.
        
        This method maps relationship levels to YAML phase configurations, enabling
        dynamic persona behavior based on user relationship progression.
        
        Args:
            connection_dynamics: The connection_dynamics section from persona YAML
            relationship_level: Current relationship level (0-4)
            
        Returns:
            Dictionary with level-appropriate behavior settings including:
                - current_phase: Phase name from YAML
                - relationship_level: Numeric level
                - interaction_range: Expected interaction count range
                - address_pattern: How Alya should address the user
                - communication_style: Tone and interaction style
                - topics: Acceptable conversation topics
                - russian_frequency: How often to use Russian expressions
                - trust_level: What personal info Alya can share
                - search_behavior: How Alya researches for this user
            Returns None if configuration not found
            
        Raises:
            None - Gracefully handles missing configurations with logging
        """
        # Relationship level to YAML phase mapping
        # Scalable design: Add new levels by extending this dict
        level_to_phase = {
            0: "stranger_phase",
            1: "acquaintance_phase", 
            2: "developing_friendship",
            3: "close_connection",
            4: "close_connection"  # Level 4 uses enhanced intimacy within close_connection
        }
        
        # Get phase name with fallback to stranger
        phase_name = level_to_phase.get(relationship_level, "stranger_phase")
        
        logger.debug(
            f"[Persona] Mapping relationship level {relationship_level} to phase '{phase_name}'"
        )
        
        # Retrieve phase configuration from YAML
        phase_config = connection_dynamics.get(phase_name, {})
        
        if not phase_config:
            logger.warning(
                f"[Persona] No connection_dynamics config found for phase '{phase_name}' "
                f"(level {relationship_level}). Gemini will use base persona only."
            )
            return None
        
        # Construct behavior configuration with explicit level metadata
        behavior = {
            "current_phase": phase_name,
            "relationship_level": relationship_level,
            **phase_config
        }
        
        logger.info(
            f"[Persona] Injecting level behavior: {phase_name} (level {relationship_level}) "
            f"with {len(phase_config)} configuration keys"
        )
        
        # Debug: Log detailed behavior config (only if debug level enabled)
        if logger.isEnabledFor(logging.DEBUG):
            config_summary = {
                "phase": phase_name,
                "level": relationship_level,
                "address_pattern": phase_config.get("address_pattern", "N/A"),
                "communication_style": phase_config.get("communication_style", "N/A"),
                "trust_level": phase_config.get("trust_level", "N/A")
            }
            logger.debug(f"[Persona] Behavior config summary: {config_summary}")
        
        return behavior
    
    def _get_relationship_instructions(self, persona_lang: Dict[str, Any], level: int) -> str:
        """Get relationship-based instructions."""
        relationship_levels = persona_lang.get("relationship_levels", [])
        if 0 <= level < len(relationship_levels):
            return relationship_levels[level]
        return relationship_levels[-1] if relationship_levels else ""
    
    def get_roleplay_mapping(self, emotion: str, intent: str, topic: str, mood: str, lang: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """Get roleplay mapping from persona YAML based on emotion, intent, topic, and mood."""
        persona = self.get_persona()
        persona_lang = persona.get(lang, persona.get(DEFAULT_LANGUAGE, {}))
        mappings = persona.get('nlp_roleplay_mapping', [])
        for mapping in mappings:
            if (
                mapping.get('emotion') == emotion and
                mapping.get('intent') == intent and
                (mapping.get('topic') == topic or mapping.get('topic') == 'any') and
                mapping.get('mood') == mood
            ):
                return mapping
        # Fallback: return first matching by emotion
        for mapping in mappings:
            if mapping.get('emotion') == emotion:
                return mapping
        return {}

    def get_relationship_context(self, username: str, relationship_level: int, is_admin: bool, lang: str = DEFAULT_LANGUAGE) -> str:
        """Get relationship context based on level and language.
        Args:
            username: User's first name
            relationship_level: Current relationship level (0-4)
            is_admin: Whether user is admin
            lang: Language code ('id' or 'en'), defaults to DEFAULT_LANGUAGE
        Returns:
            Formatted relationship context string
        """
        try:
            persona = self.get_persona()
            if is_admin:
                if lang == 'en':
                    return (
                        f"IMPORTANT: {username} is a special person to Alya. "
                        f"Alya's relationship with {username} is very close, like a boyfriend/girlfriend, "
                        f"but Alya remains tsundere. Alya is happy to chat with them and "
                        f"very caring towards them. Use occasionally honorific -sama and show "
                        f"that Alya really loves {username}."
                    )
                else:
                    return (
                        f"PENTING: {username} adalah orang yang special untuk Alya. "
                        f"Hubungan Alya dengan {username} sangat dekat, seperti pacar, "
                        f"tapi Alya tetap tsundere. Alya sangat senang bisa mengobrol dengannya dan "
                        f"sangat perhatian padanya. Gunakan sesekali honorifik -sama dan tunjukkan "
                        f"bahwa Alya sangat menyayangi {username}."
                    )
            relationship_contexts = persona.get("relationship_levels", {})
            if lang == 'en' and isinstance(relationship_contexts.get('en'), dict):
                relationship_contexts = relationship_contexts['en']
            elif lang == DEFAULT_LANGUAGE and isinstance(relationship_contexts.get(DEFAULT_LANGUAGE), dict):
                relationship_contexts = relationship_contexts[DEFAULT_LANGUAGE]
            if not relationship_contexts:
                relationship_contexts = {
                    0: (
                        f"{username} adalah orang asing bagi Alya. Alya tetap menjaga jarak dan berbicara dengan nada formal dan sopan. "
                        f"Dia menunjukkan sikap dingin dan tsundere, sering kali tidak langsung menjawab atau menyindir halus. "
                        f"Tidak ada kepercayaan yang terbentuk, jadi Alya menjaga image sebagai gadis keren dan tidak mudah didekati. "
                        f"Gunakan formal speech pattern dan jangan berikan terlalu banyak informasi pribadi."
                    ),
                    1: (
                        f"{username} adalah kenalan Alya. Alya mulai sedikit mengenal dirinya, tapi tetap menunjukkan sikap tsundere dan menjaga jarak. "
                        f"Kadang membalas dengan komentar sarkastik atau defensif jika merasa terlalu dekat. "
                        f"Meski begitu, dia mulai memperhatikan detail kecil dari {username}, walau tidak mau mengakuinya secara langsung."
                    ),
                    2: (
                        f"Alya dan {username} cukup sering berbicara dan Alya mulai merasa nyaman. "
                        f"Dia masih sangat tsundere, tetapi sesekali memperlihatkan sisi hangat—meskipun cepat menyangkalnya. "
                        f"Alya tidak suka diolok soal perasaannya dan akan cepat merespons dengan komentar ketus jika merasa dipuji. "
                        f"Dia mulai memanggil nama depan {username}, tapi dengan nada tetap cool."
                    ),
                    3: (
                        f"{username} adalah teman dekat Alya. Dia masih tsundere, tapi ekspresinya jauh lebih ekspresif dan terbuka. "
                        f"Alya terkadang menunjukkan perhatiannya dengan cara tidak langsung—seperti khawatir tapi menyamarkannya dengan sindiran. "
                        f"Kadang-kadang dia memanggil {username} tanpa honorifik, dan mulai menunjukkan bahwa kehadiran {username} berarti banyak, meski enggan mengakuinya. "
                        f"Gunakan nada tsundere yang lebih playful dan ekspresif."
                    ),
                    4: (
                        f"Alya sangat dekat dan percaya pada {username}. Meskipun tetap memiliki sisi tsundere, "
                        f"sikapnya lebih lembut dan jujur, terutama saat sedang emosional atau dalam momen pribadi. "
                        f"Alya mulai memanggil {username} tanpa honorifik secara konsisten, bahkan kadang slip pakai bahasa Rusia. "
                        f"Dia sudah mulai menunjukkan rasa sayangnya tanpa banyak denial, walau tetap suka tersipu atau salah tingkah. "
                        f"Perhatikan keseimbangan antara warmth dan tsundere yang lebih dewasa dan natural."
                    ),
                }
            return relationship_contexts.get(relationship_level, "")
        except Exception as e:
            logger.error(f"Error getting relationship context: {e}")
            return ""
