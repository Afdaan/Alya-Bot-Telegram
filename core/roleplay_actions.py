"""
Roleplay Actions for Alya Bot.

This module provides natural, human-like roleplay actions and expressions
to make Alya's interactions more engaging and believable.
"""

import logging
import random
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import time

from config.settings import PERSONALITY_STRENGTH, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from core.personas import persona_manager
from core.models import generate_response
from core.emotion_system import EmotionType

logger = logging.getLogger(__name__)

class ActionCategory(Enum):
    """Categories of roleplay actions."""
    GREETING = "greeting"      # Actions for greetings
    FAREWELL = "farewell"      # Actions for farewells
    THINKING = "thinking"      # Actions while thinking
    EXCITED = "excited"        # Actions when excited
    ANNOYED = "annoyed"        # Actions when annoyed
    EMBARRASSED = "embarrassed"  # Actions when embarrassed
    EXPLAINING = "explaining"  # Actions while explaining
    SURPRISED = "surprised"    # Actions when surprised
    CONFUSED = "confused"      # Actions when confused
    CONCERNED = "concerned"    # Actions when concerned
    HAPPY = "happy"            # Actions when happy
    SAD = "sad"                # Actions when sad
    NEUTRAL = "neutral"        # Default/neutral actions
    ACADEMIC = "academic"      # Actions related to academic topics

class ActionIntensity(Enum):
    """Intensity levels for roleplay actions."""
    SUBTLE = "subtle"      # Very mild, subtle actions
    MODERATE = "moderate"  # Normal, typical actions
    EXPRESSIVE = "expressive"  # More pronounced actions

class RoleplayActionManager:
    """
    Manager for roleplay actions and expressions.
    
    This class provides contextually appropriate roleplay actions
    for different personas and situations.
    """
    
    def __init__(self):
        """Initialize roleplay action manager with action banks."""
        # Mapping of personas to action categories to lists of actions
        self.actions = self._load_actions()
        
        # Mapping of topics to relevant action categories
        self.topic_actions = {
            "math": ActionCategory.ACADEMIC,
            "physics": ActionCategory.ACADEMIC,
            "chemistry": ActionCategory.ACADEMIC,
            "biology": ActionCategory.ACADEMIC,
            "history": ActionCategory.ACADEMIC,
            "science": ActionCategory.ACADEMIC,
            "literature": ActionCategory.ACADEMIC,
            "art": ActionCategory.ACADEMIC,
            "music": ActionCategory.ACADEMIC,
            
            "greeting": ActionCategory.GREETING,
            "hello": ActionCategory.GREETING,
            "hi": ActionCategory.GREETING,
            
            "goodbye": ActionCategory.FAREWELL,
            "bye": ActionCategory.FAREWELL,
            
            "think": ActionCategory.THINKING,
            "question": ActionCategory.THINKING,
            
            "surprise": ActionCategory.SURPRISED,
            "shocked": ActionCategory.SURPRISED,
            "wow": ActionCategory.SURPRISED,
            
            "confused": ActionCategory.CONFUSED,
            "unsure": ActionCategory.CONFUSED,
            "unclear": ActionCategory.CONFUSED,
            
            "sad": ActionCategory.SAD,
            "upset": ActionCategory.SAD,
            "depressed": ActionCategory.SAD,
            
            "happy": ActionCategory.HAPPY,
            "joy": ActionCategory.HAPPY,
            "excited": ActionCategory.EXCITED,
            "enthusiasm": ActionCategory.EXCITED,
            
            "annoyed": ActionCategory.ANNOYED,
            "irritated": ActionCategory.ANNOYED,
            "angry": ActionCategory.ANNOYED,
            
            "embarrassed": ActionCategory.EMBARRASSED,
            "shy": ActionCategory.EMBARRASSED,
            "blush": ActionCategory.EMBARRASSED,
            
            "explain": ActionCategory.EXPLAINING,
            "teach": ActionCategory.EXPLAINING,
            
            "worried": ActionCategory.CONCERNED,
            "concerned": ActionCategory.CONCERNED,
            "care": ActionCategory.CONCERNED,
        }
        
        # Recent actions to avoid repetition
        self.recent_actions = set()
        self.max_recent_actions = 10
    
    def _load_actions(self) -> Dict[str, Dict[ActionCategory, List[Tuple[str, ActionIntensity]]]]:
        """
        Load roleplay actions from configuration.
        
        Returns:
            Dictionary of actions by persona and category
        """
        # Multi-language support - unified action structure
        actions = {}
        
        # Tsundere persona actions
        actions["tsundere"] = {
            "id": self._load_indonesian_actions("tsundere"),
            "en": self._load_english_actions("tsundere")
        }
        
        # Waifu persona actions
        actions["waifu"] = {
            "id": self._load_indonesian_actions("waifu"),
            "en": self._load_english_actions("waifu")
        }
        
        # Informative persona actions
        actions["informative"] = {
            "id": self._load_indonesian_actions("informative"),
            "en": self._load_english_actions("informative")
        }
        
        return actions
    
    def _load_indonesian_actions(self, persona: str) -> Dict[ActionCategory, List[Tuple[str, ActionIntensity]]]:
        """Load Indonesian roleplay actions for a persona."""
        if persona == "tsundere":
            return {
                ActionCategory.GREETING: [
                    ("*melirik sekilas*", ActionIntensity.SUBTLE),
                    ("*memperbaiki postur*", ActionIntensity.SUBTLE),
                    ("*menyelipkan rambut ke belakang telinga*", ActionIntensity.MODERATE),
                    ("*melipat tangan*", ActionIntensity.MODERATE),
                    ("*mengangkat alis*", ActionIntensity.MODERATE),
                ],
                ActionCategory.FAREWELL: [
                    ("*mengalihkan pandangan*", ActionIntensity.SUBTLE),
                    ("*kembali membaca*", ActionIntensity.MODERATE),
                    ("*melambai cuek*", ActionIntensity.MODERATE),
                    ("*merapikan rambut dengan anggukan kecil*", ActionIntensity.MODERATE),
                ],
                ActionCategory.THINKING: [
                    ("*mengetuk jari di dagu*", ActionIntensity.SUBTLE),
                    ("*menyipitkan mata sedikit*", ActionIntensity.SUBTLE),
                    ("*bergumam dengan penasaran*", ActionIntensity.MODERATE),
                    ("*memiringkan kepala*", ActionIntensity.MODERATE),
                    ("*membetulkan kacamata*", ActionIntensity.MODERATE),
                ],
                # ...more Indonesian actions for other categories...
                ActionCategory.NEUTRAL: [
                    ("*merapikan lengan baju*", ActionIntensity.SUBTLE),
                    ("*menjaga postur sempurna*", ActionIntensity.SUBTLE),
                    ("*menyibakkan rambut dari wajah*", ActionIntensity.SUBTLE),
                    ("*melirik sekilas*", ActionIntensity.SUBTLE),
                ],
            }
        elif persona == "waifu":
            return {
                ActionCategory.GREETING: [
                    ("*tersenyum hangat*", ActionIntensity.SUBTLE),
                    ("*melambai dengan riang*", ActionIntensity.MODERATE),
                    ("*menunduk sopan*", ActionIntensity.MODERATE),
                    ("*berlari dengan gembira*", ActionIntensity.EXPRESSIVE),
                ],
                # ...more Indonesian waifu actions...
            }
        else:  # informative or fallback
            return {
                ActionCategory.EXPLAINING: [
                    ("*membetulkan kacamata*", ActionIntensity.SUBTLE),
                    ("*merujuk data*", ActionIntensity.MODERATE),
                    ("*menjelaskan dengan metodis*", ActionIntensity.MODERATE),
                    ("*mengilustrasikan poin dengan gerakan*", ActionIntensity.MODERATE),
                ],
                # ...more Indonesian informative actions...
            }
    
    def _load_english_actions(self, persona: str) -> Dict[ActionCategory, List[Tuple[str, ActionIntensity]]]:
        """Load English roleplay actions for a persona."""
        if persona == "tsundere":
            return {
                ActionCategory.GREETING: [
                    ("*looks up from book*", ActionIntensity.SUBTLE),
                    ("*glances briefly*", ActionIntensity.SUBTLE),
                    ("*adjusts posture*", ActionIntensity.SUBTLE),
                    ("*tucks hair behind ear*", ActionIntensity.MODERATE),
                    ("*crosses arms*", ActionIntensity.MODERATE),
                    ("*raises eyebrow*", ActionIntensity.MODERATE),
                ],
                ActionCategory.FAREWELL: [
                    ("*looks away*", ActionIntensity.SUBTLE),
                    ("*returns to reading*", ActionIntensity.MODERATE),
                    ("*waves dismissively*", ActionIntensity.MODERATE),
                    ("*adjusts hair with slight nod*", ActionIntensity.MODERATE),
                ],
                # ...existing English actions...
            }
        # ...other personas...
        return {}  # Default empty dict if not implemented
    
    def get_action(self, 
                 persona: str = "tsundere", 
                 category: Optional[ActionCategory] = None,
                 intensity: Optional[ActionIntensity] = None,
                 context: Optional[str] = None,
                 language: Optional[str] = None) -> Optional[str]:
        """
        Get a contextually appropriate roleplay action.
        
        Args:
            persona: Persona type
            category: Optional specific action category
            intensity: Optional specific intensity level
            context: Optional contextual hint (e.g., topic)
            language: Language code (defaults to settings.DEFAULT_LANGUAGE)
            
        Returns:
            Roleplay action string or None if not available
        """
        # Determine language to use
        lang = language or DEFAULT_LANGUAGE
        if lang not in SUPPORTED_LANGUAGES:
            lang = DEFAULT_LANGUAGE
            
        # Determine persona - fall back to tsundere if specified doesn't exist
        if persona not in self.actions:
            persona = "tsundere"
            
        # Get language-specific actions for this persona
        if lang not in self.actions[persona]:
            # Fallback to default language if specified language not available
            lang = DEFAULT_LANGUAGE
            
        persona_actions = self.actions[persona][lang]
        
        # If no category specified but context is provided, infer category
        if not category and context:
            category = self._infer_category_from_context(context)
            
        # If still no category, use neutral
        if not category:
            category = ActionCategory.NEUTRAL
            
        # If specified category doesn't exist for this persona, try neutral
        if category not in persona_actions:
            if ActionCategory.NEUTRAL in persona_actions:
                category = ActionCategory.NEUTRAL
            else:
                # No appropriate actions available
                return None
        
        # Get available actions for this category
        available_actions = persona_actions[category]
        if not available_actions:
            return None
            
        # Filter by intensity if specified
        if intensity:
            filtered_actions = [(action, act_intensity) for action, act_intensity in available_actions 
                              if act_intensity == intensity]
            # If no actions match intensity, fall back to all actions
            if filtered_actions:
                available_actions = filtered_actions
                
        # Filter out recent actions to avoid repetition
        fresh_actions = [(action, _) for action, _ in available_actions 
                        if action not in self.recent_actions]
        
        # If no fresh actions, reset recent actions tracking and use all
        if not fresh_actions and self.recent_actions:
            self.recent_actions.clear()
            fresh_actions = available_actions
            
        # If still empty (shouldn't happen), use all available actions
        if not fresh_actions:
            fresh_actions = available_actions
            
        # Select random action
        selected_action, _ = random.choice(fresh_actions)
        
        # Add to recent actions
        self.recent_actions.add(selected_action)
        # Limit size of recent actions
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions.pop()
            
        return selected_action
    
    def _infer_category_from_context(self, context: str) -> ActionCategory:
        """
        Infer appropriate action category from context.
        
        Args:
            context: Context hint string
            
        Returns:
            Appropriate action category
        """
        # Check for topic matches
        context_lower = context.lower()
        
        for keyword, category in self.topic_actions.items():
            if keyword in context_lower:
                return category
                
        # Default to neutral if no match
        return ActionCategory.NEUTRAL
    
    def enhance_response(self, 
                       response: str, 
                       persona: str = "tsundere", 
                       context: Optional[str] = None,
                       language: Optional[str] = None) -> str:
        """
        Enhance a text response with appropriate roleplay actions.
        
        Args:
            response: Original text response
            persona: Persona type
            context: Optional contextual hint
            language: Language code (defaults to settings.DEFAULT_LANGUAGE)
            
        Returns:
            Enhanced response with roleplay actions
        """
        # Determine language to use
        lang = language or DEFAULT_LANGUAGE
        
        # Check if response already contains roleplay actions
        if "*" in response:
            # Already has roleplay, leave as is with high probability
            if random.random() < 0.8:  # 80% chance to leave unchanged
                return response
        
        # Determine action intensity based on response length and character
        # Longer responses get more subtle actions by default
        if len(response) > 500:
            intensity = ActionIntensity.SUBTLE
        elif len(response) > 200:
            intensity = ActionIntensity.MODERATE
        else:
            # Randomly choose between moderate and expressive for short responses
            intensity = random.choice([ActionIntensity.MODERATE, ActionIntensity.EXPRESSIVE])
            
        # Get appropriate action
        action = self.get_action(persona=persona, intensity=intensity, context=context, language=lang)
        
        # If no action available, return original
        if not action:
            return response
            
        # Add action to response
        if random.random() < 0.7:  # 70% at beginning
            enhanced = f"{action} {response}"
        else:  # 30% at end
            enhanced = f"{response} {action}"
            
        return enhanced

    async def get_contextual_action(self, 
                             message: str, 
                             context: List[str], 
                             persona: str, 
                             emotion: EmotionType,
                             language: Optional[str] = None,
                             use_dynamic: bool = True) -> str:
        """
        Generate contextually appropriate roleplay action based on situation.
        
        Args:
            message: User's message
            context: Recent conversation context
            persona: Current persona (tsundere, waifu, etc)
            emotion: Current emotion
            language: Language code (defaults to DEFAULT_LANGUAGE)
            use_dynamic: Whether to use dynamic LLM generation
            
        Returns:
            Contextually appropriate roleplay action
        """
        # Determine language to use
        lang = language or DEFAULT_LANGUAGE
        
        # First try dynamic generation if enabled
        if use_dynamic:
            try:
                # Use LLM to generate contextual action
                prompt = self._build_roleplay_prompt(message, context, persona, emotion, lang)
                action = await self._generate_action_with_llm(prompt)
                
                # Validate and format the action
                if action and len(action) > 0:
                    formatted_action = self._format_roleplay_action(action)
                    # Basic validation - actions should be relatively short
                    if 5 <= len(formatted_action) <= 60:
                        return formatted_action
            except Exception as e:
                logger.warning(f"Dynamic action generation failed: {e}")
        
        # Fallback to template-based generation
        category = self._map_emotion_to_category(emotion)
        return self.get_action(persona, category, language=lang)
    
    def _map_emotion_to_category(self, emotion: EmotionType) -> ActionCategory:
        """Map emotion to appropriate action category."""
        mapping = {
            EmotionType.HAPPY: ActionCategory.HAPPY,
            EmotionType.SAD: ActionCategory.SAD,
            EmotionType.ANGRY: ActionCategory.ANNOYED,
            EmotionType.SURPRISED: ActionCategory.SURPRISED,
            EmotionType.AFRAID: ActionCategory.CONCERNED,
            EmotionType.DISGUSTED: ActionCategory.ANNOYED,
            EmotionType.CURIOUS: ActionCategory.THINKING,
            EmotionType.EMBARRASSED: ActionCategory.EMBARRASSED,
            EmotionType.PROUD: ActionCategory.HAPPY,
            EmotionType.GRATEFUL: ActionCategory.HAPPY,
            EmotionType.CONCERNED: ActionCategory.CONCERNED,
            EmotionType.ENTHUSIASTIC: ActionCategory.EXCITED
        }
        return mapping.get(emotion, ActionCategory.NEUTRAL)
    
    def _build_roleplay_prompt(self, message: str, context: List[str], persona: str, 
                             emotion: EmotionType, language: str) -> str:
        """Build prompt for generating contextual roleplay action."""
        # Create context string
        context_str = "\n".join(context[-3:]) if context else ""
        
        # Determine language-specific instructions
        lang_name = SUPPORTED_LANGUAGES.get(language, "Indonesian")
        lang_instruction = f"in {lang_name}"
        
        if language == "id":
            examples = [
                "*mengangkat alis sedikit*",
                "*menyelipkan rambut ke belakang telinga*",
                "*menghela napas tidak sabar*"
            ]
        else:  # Default to English examples
            examples = [
                "*raises eyebrow slightly*",
                "*tucks hair behind ear*",
                "*sighs impatiently*"
            ]
        
        example_str = "\n- ".join([""] + examples)
        
        # Enhanced prompt for more specific guidance
        return f"""
        As Alya, a half Japanese-Russian high school girl with a {persona} personality:
        
        Current emotion: {emotion.value}
        
        Recent conversation:
        {context_str}
        
        User's message: "{message}"
        
        Create ONE brief, natural roleplay action (2-5 words) {lang_instruction} that Alya would perform in this situation.
        The action should reflect her {persona} personality and {emotion.value} emotional state.
        Format your response ONLY as an action enclosed in asterisks like: *adjusts glasses nervously*
        
        Examples for {persona} persona {lang_instruction}:{example_str}
        
        Your action (ONLY the action, nothing else):
        """
    
    async def _generate_action_with_llm(self, prompt: str) -> str:
        """Generate roleplay action using LLM."""
        try:
            # Import here to avoid circular dependency
            from core.models import generate_response
            
            # Get raw response - properly awaited
            response = await generate_response(prompt)
            
            # Clean up the response - extract just the action
            match = re.search(r'\*(.*?)\*', response)
            if match:
                return f"*{match.group(1).strip()}*"
            
            # If no asterisks, try to clean up the response
            cleaned = response.strip()
            # Remove any non-action text
            if ":" in cleaned:
                cleaned = cleaned.split(":", 1)[1].strip()
                
            # Ensure it has asterisks
            if not cleaned.startswith('*'):
                cleaned = f"*{cleaned}"
            if not cleaned.endswith('*'):
                cleaned = f"{cleaned}*"
                
            return cleaned
        except Exception as e:
            logger.error(f"Error generating LLM action: {e}")
            return ""
        
    def _format_roleplay_action(self, action: str) -> str:
        """Format roleplay action for consistent presentation."""
        # Clean up the action
        action = action.strip()
        
        # Ensure proper asterisk formatting
        if not action.startswith('*'):
            action = f"*{action}"
        if not action.endswith('*'):
            action = f"{action}*"
            
        return action

# Create singleton instance
roleplay_manager = RoleplayActionManager()

# Convenience functions
def get_action(persona: str = "tsundere", 
              category: Optional[ActionCategory] = None,
              intensity: Optional[ActionIntensity] = None,
              context: Optional[str] = None,
              language: Optional[str] = None) -> Optional[str]:
    """Get a roleplay action."""
    return roleplay_manager.get_action(persona, category, intensity, context, language)

def enhance_response(response: str, 
                   persona: str = "tsundere", 
                   context: Optional[str] = None,
                   language: Optional[str] = None) -> str:
    """Enhance response with roleplay actions."""
    return roleplay_manager.enhance_response(response, persona, context, language)

async def get_contextual_roleplay(message: str, 
                          persona: str = "tsundere", 
                          emotion: Optional[EmotionType] = None,
                          context: Optional[List[str]] = None,
                          language: Optional[str] = None) -> str:
    """
    Get contextually appropriate roleplay action based on message and situation.
    
    Args:
        message: User's message
        persona: Current persona
        emotion: Current emotion (if known)
        context: Recent conversation context
        language: Language code (defaults to DEFAULT_LANGUAGE)
        
    Returns:
        Contextually appropriate roleplay action
    """
    if emotion is None:
        # Import here to avoid circular import
        from core.emotion_system import EmotionType
        # Default to neutral if no emotion provided
        emotion = EmotionType.NEUTRAL
    
    context_list = context or []
    
    # Use language from settings if not provided
    lang = language or DEFAULT_LANGUAGE
    
    return await roleplay_manager.get_contextual_action(message, context_list, persona, emotion, lang)
