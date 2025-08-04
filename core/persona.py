"""
Persona manager for Alya Bot to handle persona loading and response formatting.
"""
import os
import logging
import random
from typing import Dict, List, Any, Optional
import yaml
import datetime

from config.settings import PERSONA_DIR, DEFAULT_PERSONA

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
        
    def get_error_message(self, persona_name: Optional[str] = None, username: str = "user", lang: str = 'id') -> str:
        """Get a generic error message for the given persona.
        
        Args:
            persona_name: Name of the persona to use, or None for default
            username: Username to insert in the error template
            lang: Language for the error message
            
        Returns:
            Formatted error message
        """
        persona = self.get_persona(persona_name)
        errors = persona.get("errors", {})
        
        # Get language-specific errors, fallback to default language or a generic message
        lang_errors = errors.get(lang, errors.get('id', {}))
        error_template = lang_errors.get("generic", "Sorry, something went wrong, {username}.")
        
        return error_template.format(username=username)
        
    def get_help_message(self, username: str, prefix: str, lang: str = 'id') -> str:
        """Get help message in specified language.
        
        Args:
            username: User's name
            prefix: Command prefix
            lang: Language code ('id' or 'en')
            
        Returns:
            Help message string
        """
        if lang == 'en':
            return f"""<b>Hi {username}-kun!</b> ✨

Alya is here to chat and help with various tasks!

<b>🎓 How to Use:</b>
• Just chat naturally with Alya
• In groups: use `{prefix}` before your message
• Ask about images, get help with studies, or just talk!

<b>📚 Commands:</b>
• `/help` - Show this message
• `/stats` - Your stats with Alya
• `/lang` - Change language
• `/reset` - Reset conversation

<i>Don't be shy... Alya will remember our conversations! 😤</i>"""
        else:
            return f"""<b>Hai {username}-kun!</b> ✨

Alya di sini siap nemenin ngobrol dan bantuin berbagai keperluan!

<b>🎓 Cara Pakai:</b>
• Langsung ngobrol natural sama Alya
• Di grup: pakai `{prefix}` sebelum pesan
• Tanya tentang gambar, minta bantuan belajar, atau sekadar curhat!

<b>📚 Perintah:</b>
• `/help` - Tampilkan pesan ini
• `/stats` - Statistik kamu dengan Alya
• `/lang` - Ganti bahasa
• `/reset` - Reset percakapan

<i>Jangan malu-malu... Alya akan ingat percakapan kita! 😤</i>"""

    def get_chat_prompt(
        self,
        username: str,
        message: str,
        context: str,
        relationship_level: int,
        is_admin: bool,
        lang: str = 'id'
    ) -> str:
        """Construct a detailed chat prompt for Gemini.
        
        Args:
            username: User's name
            message: User's message
            context: Conversation context
            relationship_level: User's relationship level with Alya
            is_admin: Whether the user is an admin
            lang: The user's preferred language
            
        Returns:
            The full prompt for Gemini
        """
        persona = self.get_persona() # Use default persona for chat
        
        # Get language-specific persona details
        persona_lang = persona.get(lang, persona.get('id', {}))

        base_instructions = persona_lang.get("base_instructions", "")
        personality_traits = "\n- ".join(persona_lang.get("personality_traits", []))
        relationship_instructions = self._get_relationship_instructions(persona_lang, relationship_level)
        response_format = persona_lang.get("response_format", "")
        russian_phrases = "\n- ".join([f"`{p}`: {d}" for p, d in persona_lang.get("russian_phrases", {}).items()])
        
        admin_note = ""
        if is_admin:
            admin_note = persona_lang.get("admin_note", "")

        prompt = f"""
{base_instructions}

**Your Core Personality:**
- {personality_traits}

**Your Relationship with {username}:**
{relationship_instructions}
{admin_note}

**Conversation Context (Recent History):**
---
{context or "This is the beginning of your conversation."}
---

**User's Message:**
> {message}

**Your Task:**
Respond to {username} in **{persona_lang.get('language_name', 'Bahasa Indonesia')}**.
{response_format}

**Russian Phrases You Can Use (sparingly, for emotional emphasis):**
- {russian_phrases}
"""
        return prompt.strip()

    def get_media_analysis_prompt(
        self,
        username: str,
        query: str,
        media_context: str,
        lang: str = 'id'
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
        persona_lang = persona.get(lang, persona.get('id', {}))

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

    def _get_relationship_instructions(self, persona_lang: Dict[str, Any], level: int) -> str:
        """Get relationship-based instructions."""
        relationship_levels = persona_lang.get("relationship_levels", [])
        if 0 <= level < len(relationship_levels):
            return relationship_levels[level]
        return relationship_levels[-1] if relationship_levels else ""
    
    def get_roleplay_mapping(self, emotion: str, intent: str, topic: str, mood: str, lang: str = 'id') -> Dict[str, Any]:
        """Get roleplay mapping from persona YAML based on emotion, intent, topic, and mood."""
        persona = self.get_persona()
        persona_lang = persona.get(lang, persona.get('id', {}))
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

    def get_relationship_context(self, username: str, relationship_level: int, is_admin: bool, lang: str = 'id') -> str:
        """Get relationship context based on level and language.
        Args:
            username: User's first name
            relationship_level: Current relationship level (0-4)
            is_admin: Whether user is admin
            lang: Language code ('id' or 'en')
        Returns:
            Formatted relationship context string
        """
        try:
            persona = self.get_persona()
            # Handle admin special case
            if is_admin:
                if lang == 'en':
                    return (
                        f"IMPORTANT: {username} is a bot admin and very special person to Alya. "
                        f"Alya's relationship with {username} is very close, like a boyfriend/girlfriend, "
                        f"but Alya remains tsundere. Alya is very happy to chat with them and "
                        f"very caring towards them. Use occasionally honorific -sama and show "
                        f"that Alya really loves {username}."
                    )
                else:
                    return (
                        f"PENTING: {username} adalah admin bot dan orang yang sangat special untuk Alya. "
                        f"Hubungan Alya dengan {username} sangat dekat, seperti pacar, "
                        f"tapi Alya tetap tsundere. Alya sangat senang bisa mengobrol dengannya dan "
                        f"sangat perhatian padanya. Gunakan sesekali honorifik -sama dan tunjukkan "
                        f"bahwa Alya sangat menyayangi {username}."
                    )
            # Get relationship contexts from YAML if available
            relationship_contexts = persona.get("relationship_levels", {})
            if lang == 'en' and isinstance(relationship_contexts.get("en"), dict):
                relationship_contexts = relationship_contexts["en"]
            elif lang == 'id' and isinstance(relationship_contexts.get("id"), dict):
                relationship_contexts = relationship_contexts["id"]
            # Fallback to hardcoded if YAML not available
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
