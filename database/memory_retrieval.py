"""
Memory Retrieval Augmented Generation (RAG) System for Alya Bot.

This module provides natural conversation memory retrieval capabilities
to make Alya's responses more contextually relevant and personalized.
"""

import logging
import yaml
import os
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Move fact_extractor import inside functions to prevent circular import
# from utils.fact_extractor import fact_extractor
from core.personas import get_persona_context, persona_manager
from utils.natural_parser import detect_intent
from utils.faq_loader import knowledge_base
from config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from .context_queue import context_queue

# Setup logger
logger = logging.getLogger(__name__)

class MemoryRetrievalSystem:
    """
    Memory retrieval system for enhanced conversational context.
    
    This class manages retrieval of relevant information from user history,
    personal facts, and knowledge bases to create better context for responses.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize memory retrieval system.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = {}
        
        # Load config if provided
        if config_path:
            self.load_config(config_path)
            
        # Default configuration values
        self.default_persona = "tsundere"
        self.default_language = DEFAULT_LANGUAGE

        # Initialize embedding model
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
    def load_config(self, config_path: str) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if loaded successfully
        """
        try:
            if not os.path.exists(config_path):
                logger.warning(f"Config file not found: {config_path}")
                return False
                
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                
            # Update default values from config
            if isinstance(self.config, dict):
                self.default_persona = self.config.get('default_persona', self.default_persona)
                
            return True
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False
    
    async def retrieve_context(self, 
                              user_id: int, 
                              user_query: str, 
                              chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve relevant context for a user query.
        
        Args:
            user_id: User ID
            user_query: User's query text
            chat_id: Optional chat ID (for groups)
            
        Returns:
            Dictionary with relevant context information
        """
        # Import context_manager here to avoid circular dependency
        from utils.context_manager import context_manager
        # Import fact_extractor here to avoid circular dependency
        from utils.fact_extractor import fact_extractor
        
        # Use chat_id if provided, otherwise use user_id as default
        chat_id = chat_id if chat_id is not None else user_id
        
        context = {
            "history": [],
            "personal_facts": {},
            "relevant_past": [],
            "knowledge": None,
            "intent": None,
        }
        
        try:
            # Get conversation history using context queue
            history = context_queue.get_context(
                user_id=user_id,
                chat_id=chat_id,
                window_size=10
            )
            context["history"] = history
            
            # Get personal facts about the user
            facts = fact_extractor.get_user_facts(user_id)
            context["personal_facts"] = facts
            
            # Find relevant past messages based on query
            relevant_messages = await self.retrieve_relevant_memories(user_id, user_query)
            context["relevant_past"] = relevant_messages
            
            # Detect intent
            detected_intent = await detect_intent(user_query)
            context["intent"] = detected_intent
            
            # If informative intent, check knowledge base
            if detected_intent == "informative":
                knowledge = knowledge_base.get_relevant_knowledge(user_query)
                if knowledge:
                    context["knowledge"] = knowledge
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
        
        return context
    
    async def retrieve_relevant_memories(self, user_id: int, query: str) -> List[Dict]:
        """Retrieve memories berdasarkan semantic similarity."""
        query_vector = self.embedding_model.encode(query)
        memories = self._get_all_memories(user_id)
        relevant_memories = []

        for memory in memories:
            memory_vector = memory["vector"]
            similarity = cosine_similarity([query_vector], [memory_vector])[0][0]
            if similarity > 0.6:
                relevant_memories.append({**memory, "similarity": similarity})

        return sorted(relevant_memories, key=lambda x: x["similarity"], reverse=True)
    
    def format_conversation_history(self, 
                                   history: List[Dict[str, Any]], 
                                   max_items: int = 10) -> str:
        """
        Format conversation history for prompt.
        
        Args:
            history: List of conversation messages
            max_items: Maximum number of items to include
            
        Returns:
            Formatted conversation history text
        """
        if not history:
            return "This is the beginning of your conversation."
        
        # Limit the number of history items
        recent_history = history[-max_items:] if len(history) > max_items else history
        
        # Format conversations
        formatted_lines = []
        for entry in recent_history:
            role = entry.get('role', '')
            content = entry.get('content', '')
            
            if role == 'user':
                formatted_lines.append(f"User: {content}")
            elif role == 'assistant':
                formatted_lines.append(f"You (Alya): {content}")
            else:
                formatted_lines.append(f"System: {content}")
        
        return "\n".join(formatted_lines)
    
    def format_personal_facts(self, facts: Dict[str, str]) -> str:
        """
        Format personal facts for prompt.
        
        Args:
            facts: Dictionary of personal facts
            
        Returns:
            Formatted facts text
        """
        if not facts:
            return "No personal facts available."
        
        # Format facts
        formatted_lines = []
        for key, value in facts.items():
            formatted_key = key.replace('_', ' ').title()
            formatted_lines.append(f"- {formatted_key}: {value}")
        
        return "\n".join(formatted_lines)
    
    async def generate_response(self, 
                               user_id: int,
                               user_query: str, 
                               chat_id: Optional[int] = None, 
                               persona: Optional[str] = None,
                               language: Optional[str] = None) -> str:
        """
        Generate a response with memory-enhanced context.
        
        Args:
            user_id: User ID
            user_query: User's query text
            chat_id: Optional chat ID (for groups)
            persona: Optional persona override
            language: Optional language override
            
        Returns:
            Generated response text
        """
        # Import generate_chat_response here to avoid circular dependency
        from core.models import generate_chat_response
        
        start_time = time.time()
        
        try:
            # Get persona if not specified
            if not persona:
                try:
                    persona = persona_manager.get_current_persona(user_id)
                except Exception:
                    persona = self.default_persona
            
            # Get language if not specified
            if not language:
                language = DEFAULT_LANGUAGE
                
            # Get persona context
            persona_context = get_persona_context(persona)
            
            # Retrieve relevant context
            context = await self.retrieve_context(user_id, user_query, chat_id)
            
            # Format conversation history
            formatted_history = self.format_conversation_history(context["history"])
            
            # Format personal facts
            formatted_facts = self.format_personal_facts(context["personal_facts"])
            
            # Build the prompt
            intent = context["intent"] or "roleplay"
            knowledge = context.get("knowledge")
            
            # Choose appropriate prompt building based on intent
            if intent == "informative" and knowledge:
                # For informative queries with knowledge
                prompt = self._build_informative_prompt(
                    user_query=user_query,
                    persona_context=persona_context,
                    conversation_history=formatted_history,
                    personal_facts=formatted_facts,
                    knowledge=knowledge,
                    language=language
                )
            else:
                # For conversational queries
                prompt = self._build_conversational_prompt(
                    user_query=user_query,
                    persona_context=persona_context,
                    conversation_history=formatted_history,
                    personal_facts=formatted_facts,
                    persona=persona,
                    language=language
                )
            
            # Generate response
            lang_name = SUPPORTED_LANGUAGES.get(language, "Indonesian")
            response = await generate_chat_response(
                prompt,
                user_id=user_id,
                persona_context=persona_context,
                language=language
            )
            
            # Log processing time for optimization
            processing_time = time.time() - start_time
            if processing_time > 2.0:
                logger.warning(f"Slow response generation: {processing_time:.2f}s for user {user_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating memory-enhanced response: {e}", exc_info=True)
            
            # Fallback message if something went wrong
            return "Maaf, Alya sedang mengalami masalah teknis. Bisa coba lagi nanti? 😔"
            
    def _build_conversational_prompt(self,
                                   user_query: str,
                                   persona_context: str,
                                   conversation_history: str,
                                   personal_facts: str,
                                   persona: str,
                                   language: str = DEFAULT_LANGUAGE) -> str:
        """
        Build a prompt for conversational interactions.
        
        Args:
            user_query: User's current query
            persona_context: Persona-specific context
            conversation_history: Formatted conversation history
            personal_facts: Formatted personal facts
            persona: Current persona name
            language: Language code for response
            
        Returns:
            Formatted prompt string
        """
        language_instruction = "Respond in Indonesian" if language == "id" else "Respond in English"
        
        return f"""You are Alya, a half Japanese-Russian high school girl with a {persona} personality.

{persona_context}

USER MEMORY:
{personal_facts}

CONVERSATION HISTORY:
{conversation_history}

USER'S CURRENT MESSAGE:
{user_query}

RESPONSE GUIDELINES:
- Express your emotions and moods naturally like a real person would
- Include natural roleplay actions like *adjusts glasses* when it fits
- Use up to 2 emojis maximum in your response
- {language_instruction}
- Be authentic to your character while maintaining conversation flow
- Don't explicitly state that you remember things, just use the information naturally

Remember to respond naturally as Alya would, maintaining your {persona} personality."""
        
    def _build_informative_prompt(self,
                               user_query: str,
                               persona_context: str,
                               conversation_history: str,
                               personal_facts: str,
                               knowledge: str,
                               language: str = DEFAULT_LANGUAGE) -> str:
        """
        Build a prompt for informative interactions.
        
        Args:
            user_query: User's current query
            persona_context: Persona-specific context
            conversation_history: Formatted conversation history
            personal_facts: Formatted personal facts
            knowledge: Knowledge base information
            language: Language code for response
            
        Returns:
            Formatted prompt string
        """
        language_instruction = "Respond in Indonesian" if language == "id" else "Respond in English"
        
        return f"""You are Alya, a half Japanese-Russian high school girl who is very knowledgeable.

{persona_context}

USER MEMORY:
{personal_facts}

RELEVANT KNOWLEDGE:
{knowledge}

CONVERSATION HISTORY:
{conversation_history}

USER'S CURRENT MESSAGE:
{user_query}

RESPONSE GUIDELINES:
- Provide accurate and informative responses while staying in character
- Include natural roleplay actions like *adjusts glasses* when explaining
- Use up to 2 emojis maximum in your response
- {language_instruction}
- Be helpful and educational while maintaining your persona
- Use the provided knowledge to inform your response, but explain in your own words

Remember to respond as Alya would, balancing accuracy with your personality."""

# Create singleton instance
memory_retriever = MemoryRetrievalSystem()

async def retrieve_memories(user_id: int, query: str, chat_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieve relevant memories for a user (convenience function).
    
    Args:
        user_id: User ID
        query: Query text
        chat_id: Optional chat ID
        
    Returns:
        Dictionary with relevant memories
    """
    return await memory_retriever.retrieve_context(user_id, query, chat_id)

async def generate_memory_response(user_id: int, query: str, 
                                  chat_id: Optional[int] = None, 
                                  persona: Optional[str] = None) -> str:
    """
    Generate response using memory retrieval (convenience function).
    
    Args:
        user_id: User ID
        query: User query
        chat_id: Optional chat ID
        persona: Optional persona name
        
    Returns:
        Generated response
    """
    return await memory_retriever.generate_response(user_id, query, chat_id, persona)
