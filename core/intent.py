"""
Intent Detection Module for Alya Bot.

This module provides natural intent detection capabilities using context-aware
analysis rather than relying on hardcoded patterns or keywords.
"""

import logging
import asyncio
import re
from typing import Dict, Any, List, Tuple, Literal, Optional, Set
from dataclasses import dataclass

from core.models import generate_response
from transformers import pipeline

logger = logging.getLogger(__name__)

# Type definitions for intent detection
IntentType = Literal["conversation", "information", "assistance", "unknown"]

@dataclass
class IntentResult:
    """Result of intent detection."""
    primary: IntentType  # Primary intent
    confidence: float  # Confidence score (0.0-1.0)
    secondary: Optional[IntentType] = None  # Optional secondary intent
    attributes: Dict[str, Any] = None  # Additional attributes

    def __post_init__(self):
        """Initialize attributes dictionary if not provided."""
        if self.attributes is None:
            self.attributes = {}

class IntentDetector:
    """Natural intent detection without relying on regex patterns."""
    
    def __init__(self):
        """Initialize intent detector dengan zero-shot classification."""
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        self.labels = ["conversation", "information", "assistance", "unknown"]
        
        # Cache for recent intent detections to reduce LLM calls
        self._cache: Dict[str, IntentResult] = {}
        self._cache_size = 100
        
        # Track conversation context
        self.conversation_context: Dict[int, List[str]] = {}
        
    def add_to_context(self, user_id: int, message: str) -> None:
        """
        Add message to conversation context.
        
        Args:
            user_id: User ID
            message: Message text
        """
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = []
            
        context = self.conversation_context[user_id]
        context.append(message)
        
        # Keep context manageable
        if len(context) > 10:
            self.conversation_context[user_id] = context[-10:]
    
    def get_context(self, user_id: int, max_messages: int = 5) -> List[str]:
        """
        Get recent conversation context for a user.
        
        Args:
            user_id: User ID
            max_messages: Maximum number of messages to retrieve
            
        Returns:
            List of recent messages
        """
        if user_id not in self.conversation_context:
            return []
            
        context = self.conversation_context[user_id]
        return context[-max_messages:]
        
    def detect_intent_simple(self, message: str, context: Optional[List[str]] = None) -> IntentType:
        """
        Context-aware intent detection without hardcoded patterns.
        
        Uses universal message characteristics and context analysis.
        Works for any language (English, Indonesian, etc).
        
        Args:
            message: User message to analyze
            context: Optional conversation context
            
        Returns:
            Detected intent type
        """
        # Basic validation
        if not message or message.isspace():
            return "unknown"
            
        # Too short messages are likely conversation starters
        if len(message) < 8:
            return "conversation"
        
        message_lower = message.lower().strip()
        
        # Universal structural analysis (language-independent)
        # Questions often end with ? in many languages
        ends_with_question = message_lower.endswith('?')
        
        # Check for command-like formats without using regex
        starts_with_special = message_lower.startswith(('!', '/', '.'))
        
        # Command-like messages are likely assistance requests
        if starts_with_special and len(message_lower) > 2:
            return "assistance"
        
        # Context-aware analysis
        if context and len(context) >= 2:
            # Analyze conversation momentum
            information_momentum = 0
            conversation_momentum = 0
            
            # Last 3 messages set the momentum
            for msg in context[-3:]:
                # Longer messages with question marks tend to be information-seeking
                if len(msg) > 30 and '?' in msg:
                    information_momentum += 1
                # Very short responses tend to be conversational
                elif len(msg) < 15 and '?' not in msg:
                    conversation_momentum += 1
            
            # Strong momentum in either direction
            if information_momentum > conversation_momentum + 1:
                return "information"
            if conversation_momentum > information_momentum + 1:
                return "conversation"
        
        # Length-based heuristic (works across languages)
        # Longer questions tend to be information-seeking
        if ends_with_question:
            if len(message) > 25:  # Longer questions are likely seeking information
                return "information"
        
        # Detect if message contains multiple sentences (likely more information-seeking)
        sentence_breaks = sum(1 for char in message if char in '.!?')
        if sentence_breaks >= 2:
            return "information"
        
        # Message complexity heuristic
        # More complex messages (word count + length) tend to be information-seeking
        words = message_lower.split()
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        
        # Complex messages with longer words are often information-seeking
        if len(words) > 8 and avg_word_length > 4.5:
            return "information"
            
        # Default to conversation for other messages
        return "conversation"
    
    def extract_entities(self, message: str) -> Dict[str, Any]:
        """
        Extract basic entities from message without using complex regex.
        
        Args:
            message: User message
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Extract numeric values (dates, counts, etc.)
        numbers = []
        for word in message.split():
            # Try to parse as number
            try:
                number = float(word.replace(',', '.'))
                numbers.append(number)
            except ValueError:
                pass
        
        if numbers:
            entities["numbers"] = numbers
            
        return entities

    async def detect_intent(self, 
                          user_id: int, 
                          message: str, 
                          use_llm: bool = False) -> IntentResult:
        """
        Detect user intent with context awareness.
        
        Uses LLM for natural understanding when requested.
        
        Args:
            user_id: User ID for context tracking
            message: User message to analyze
            use_llm: Whether to use LLM for detection
            
        Returns:
            IntentResult with detected intent and attributes
        """
        # Get context
        context = self.get_context(user_id)
        
        # Add current message to context
        self.add_to_context(user_id, message)
        
        # Check if we need LLM detection
        if not use_llm:
            intent = self.detect_intent_simple(message, context)
            return IntentResult(
                primary=intent,
                confidence=0.7,  # Simple detection has moderate confidence
                attributes={"method": "heuristic"}
            )
            
        try:
            # Use LLM for more natural detection
            return await self._detect_intent_with_llm(message, context)
        except Exception as e:
            logger.error(f"Error in LLM intent detection: {e}")
            # Fall back to simple detection
            intent = self.detect_intent_simple(message, context)
            return IntentResult(
                primary=intent,
                confidence=0.6,  # Lower confidence due to fallback
                attributes={"method": "heuristic_fallback", "error": str(e)}
            )
    
    async def _detect_intent_with_llm(self, message: str, context: List[str]) -> IntentResult:
        """
        Use LLM to detect intent in a more natural way.
        
        Args:
            message: User message
            context: Conversation context
            
        Returns:
            IntentResult with LLM-detected intent
        """
        # Check cache for recent identical queries
        cache_key = message.lower()[:50]  # Use first 50 chars as key
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Prepare context string
        context_str = "\n".join([f"- {msg}" for msg in context[-3:]]) if context else "No context available"
        
        # Create a prompt focused on conversation flow not keywords
        prompt = (
            "As a natural language expert, analyze this message and determine the primary intent. "
            "Consider the conversation context and message structure, not just keywords.\n\n"
            f"Recent conversation:\n{context_str}\n\n"
            f"Current message: \"{message}\"\n\n"
            "Classify the primary intent as ONE of these: 'conversation' (casual chat), "
            "'information' (seeking facts/explanations), 'assistance' (requesting help with a task), "
            "or 'unknown'. Respond with ONLY the intent label."
        )
        
        # Get intent from LLM
        response = await generate_response(prompt)
        intent_text = response.strip().lower()
        
        # Determine confidence and map to valid intent
        if "conversation" in intent_text:
            intent = "conversation"
            confidence = 0.85
        elif "information" in intent_text:
            intent = "information"
            confidence = 0.85
        elif "assistance" in intent_text:
            intent = "assistance"
            confidence = 0.85
        else:
            intent = "unknown"
            confidence = 0.6
        
        # Create result
        result = IntentResult(
            primary=intent,
            confidence=confidence,
            attributes={"method": "llm", "raw_response": intent_text}
        )
        
        # Cache the result
        self._cache[cache_key] = result
        
        # Trim cache if too large
        if len(self._cache) > self._cache_size:
            # Remove random item (simple approach)
            self._cache.pop(next(iter(self._cache)))
        
        return result

# Create a singleton instance
intent_detector = IntentDetector()

# Convenience function for simple use
async def detect_message_intent(user_id: int, message: str, use_llm: bool = False) -> IntentType:
    """
    Convenience function to detect message intent.
    
    Args:
        user_id: User ID
        message: Message to analyze
        use_llm: Whether to use LLM for analysis
        
    Returns:
        Detected intent type
    """
    result = await intent_detector.detect_intent(user_id, message, use_llm)
    return result.primary
