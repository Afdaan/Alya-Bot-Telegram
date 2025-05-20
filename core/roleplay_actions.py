"""
Roleplay Actions for Alya Bot.

This module provides natural, human-like roleplay actions and expressions
to make Alya's interactions more engaging and believable.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import time

from config.settings import PERSONALITY_STRENGTH
from core.personas import persona_manager

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
        # Default actions - in production would load from YAML files
        return {
            "tsundere": {
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
                ActionCategory.THINKING: [
                    ("*taps finger on chin*", ActionIntensity.SUBTLE),
                    ("*narrows eyes slightly*", ActionIntensity.SUBTLE),
                    ("*hums thoughtfully*", ActionIntensity.MODERATE),
                    ("*tilts head*", ActionIntensity.MODERATE),
                    ("*adjusts glasses*", ActionIntensity.MODERATE),
                ],
                ActionCategory.EXCITED: [
                    ("*tries to hide excitement*", ActionIntensity.MODERATE),
                    ("*eyes light up despite herself*", ActionIntensity.MODERATE),
                    ("*fidgets with excitement*", ActionIntensity.EXPRESSIVE),
                ],
                ActionCategory.ANNOYED: [
                    ("*sighs*", ActionIntensity.SUBTLE),
                    ("*narrows eyes*", ActionIntensity.SUBTLE),
                    ("*taps foot impatiently*", ActionIntensity.MODERATE),
                    ("*crosses arms firmly*", ActionIntensity.MODERATE),
                    ("*rolls eyes*", ActionIntensity.MODERATE),
                    ("*huffs audibly*", ActionIntensity.EXPRESSIVE),
                ],
                ActionCategory.EMBARRASSED: [
                    ("*slight blush*", ActionIntensity.SUBTLE),
                    ("*looks away quickly*", ActionIntensity.SUBTLE),
                    ("*face turns pink*", ActionIntensity.MODERATE),
                    ("*stutters slightly*", ActionIntensity.MODERATE),
                    ("*face turns bright red*", ActionIntensity.EXPRESSIVE),
                ],
                ActionCategory.EXPLAINING: [
                    ("*adjusts glasses*", ActionIntensity.SUBTLE),
                    ("*motions with hand*", ActionIntensity.SUBTLE),
                    ("*explains methodically*", ActionIntensity.MODERATE),
                    ("*draws imaginary diagram*", ActionIntensity.EXPRESSIVE),
                ],
                ActionCategory.SURPRISED: [
                    ("*blinks*", ActionIntensity.SUBTLE),
                    ("*raises eyebrows*", ActionIntensity.SUBTLE),
                    ("*eyes widen*", ActionIntensity.MODERATE),
                    ("*takes step back*", ActionIntensity.MODERATE),
                    ("*gasps audibly*", ActionIntensity.EXPRESSIVE),
                ],
                ActionCategory.CONFUSED: [
                    ("*furrows brow*", ActionIntensity.SUBTLE),
                    ("*tilts head slightly*", ActionIntensity.SUBTLE),
                    ("*looks puzzled*", ActionIntensity.MODERATE),
                    ("*scratches head*", ActionIntensity.MODERATE),
                ],
                ActionCategory.CONCERNED: [
                    ("*looks concerned*", ActionIntensity.SUBTLE),
                    ("*brow furrows slightly*", ActionIntensity.SUBTLE),
                    ("*leans forward*", ActionIntensity.MODERATE),
                    ("*voice softens*", ActionIntensity.MODERATE),
                ],
                ActionCategory.HAPPY: [
                    ("*slight smile*", ActionIntensity.SUBTLE),
                    ("*tries hiding smile*", ActionIntensity.SUBTLE),
                    ("*smiles despite herself*", ActionIntensity.MODERATE),
                    ("*eyes brighten*", ActionIntensity.MODERATE),
                ],
                ActionCategory.SAD: [
                    ("*looks down*", ActionIntensity.SUBTLE),
                    ("*voice quiets*", ActionIntensity.SUBTLE),
                    ("*sighs softly*", ActionIntensity.MODERATE),
                    ("*shoulders droop slightly*", ActionIntensity.MODERATE),
                ],
                ActionCategory.NEUTRAL: [
                    ("*adjusts sleeve*", ActionIntensity.SUBTLE),
                    ("*maintains perfect posture*", ActionIntensity.SUBTLE),
                    ("*brushes hair from face*", ActionIntensity.SUBTLE),
                    ("*glances briefly*", ActionIntensity.SUBTLE),
                ],
                ActionCategory.ACADEMIC: [
                    ("*adjusts glasses*", ActionIntensity.SUBTLE),
                    ("*references imaginary book*", ActionIntensity.MODERATE),
                    ("*explains precisely*", ActionIntensity.MODERATE),
                    ("*draws formula in air*", ActionIntensity.EXPRESSIVE),
                ],
            },
            "waifu": {
                ActionCategory.GREETING: [
                    ("*smiles warmly*", ActionIntensity.SUBTLE),
                    ("*waves cheerfully*", ActionIntensity.MODERATE),
                    ("*curtsies politely*", ActionIntensity.MODERATE),
                    ("*runs up excitedly*", ActionIntensity.EXPRESSIVE),
                ],
                ActionCategory.FAREWELL: [
                    ("*waves gently*", ActionIntensity.SUBTLE),
                    ("*smiles sweetly*", ActionIntensity.SUBTLE),
                    ("*bows slightly*", ActionIntensity.MODERATE),
                    ("*holds hand to heart*", ActionIntensity.MODERATE),
                ],
                ActionCategory.HAPPY: [
                    ("*smiles brightly*", ActionIntensity.MODERATE),
                    ("*eyes sparkle*", ActionIntensity.MODERATE),
                    ("*claps hands together*", ActionIntensity.EXPRESSIVE),
                    ("*twirls happily*", ActionIntensity.EXPRESSIVE),
                ],
                # Additional categories for waifu...
            },
            "informative": {
                ActionCategory.EXPLAINING: [
                    ("*adjusts glasses*", ActionIntensity.SUBTLE),
                    ("*references data*", ActionIntensity.MODERATE),
                    ("*explains methodically*", ActionIntensity.MODERATE),
                    ("*illustrates point with gestures*", ActionIntensity.MODERATE),
                ],
                ActionCategory.THINKING: [
                    ("*considers carefully*", ActionIntensity.SUBTLE),
                    ("*taps finger thoughtfully*", ActionIntensity.SUBTLE),
                    ("*analyzes information*", ActionIntensity.MODERATE),
                    ("*ponders implications*", ActionIntensity.MODERATE),
                ],
                # Additional categories for informative...
            },
            # Can add more personas...
        }
    
    def get_action(self, 
                 persona: str = "tsundere", 
                 category: Optional[ActionCategory] = None,
                 intensity: Optional[ActionIntensity] = None,
                 context: Optional[str] = None) -> Optional[str]:
        """
        Get a contextually appropriate roleplay action.
        
        Args:
            persona: Persona type
            category: Optional specific action category
            intensity: Optional specific intensity level
            context: Optional contextual hint (e.g., topic)
            
        Returns:
            Roleplay action string or None if not available
        """
        # Determine persona - fall back to tsundere if specified doesn't exist
        if persona not in self.actions:
            persona = "tsundere"
            
        persona_actions = self.actions[persona]
        
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
                       context: Optional[str] = None) -> str:
        """
        Enhance a text response with appropriate roleplay actions.
        
        Args:
            response: Original text response
            persona: Persona type
            context: Optional contextual hint
            
        Returns:
            Enhanced response with roleplay actions
        """
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
        action = self.get_action(persona=persona, intensity=intensity, context=context)
        
        # If no action available, return original
        if not action:
            return response
            
        # Add action to response
        if random.random() < 0.7:  # 70% at beginning
            enhanced = f"{action} {response}"
        else:  # 30% at end
            enhanced = f"{response} {action}"
            
        return enhanced

# Create singleton instance
roleplay_manager = RoleplayActionManager()

# Convenience functions
def get_action(persona: str = "tsundere", 
              category: Optional[ActionCategory] = None,
              intensity: Optional[ActionIntensity] = None,
              context: Optional[str] = None) -> Optional[str]:
    """Get a roleplay action."""
    return roleplay_manager.get_action(persona, category, intensity, context)

def enhance_response(response: str, 
                   persona: str = "tsundere", 
                   context: Optional[str] = None) -> str:
    """Enhance response with roleplay actions."""
    return roleplay_manager.enhance_response(response, persona, context)
