"""
Memory manager for handling conversation history and context management.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from config.settings import MEMORY_EXPIRY_DAYS, MAX_CONTEXT_MESSAGES, SUMMARY_INTERVAL
from core.gemini_client import GeminiClient
from database.models import Conversation, ConversationSummary, User
from database.session import db_session_context
import json

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages conversation memory and context for users."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """Initialize memory manager.
        
        Args:
            gemini_client: Optional Gemini client for summarization
        """
        self.gemini_client = gemini_client
    
    def save_user_message(self, user_id: int, message: str) -> None:
        """Store a user message in the conversation history."""
        self.store_message(user_id, message, is_user=True)
        
    def save_bot_response(self, user_id: int, message: str) -> None:
        """Store a bot response in the conversation history."""
        self.store_message(user_id, message, is_user=False)
    
    def store_message(self, user_id: int, message: str, is_user: bool = True, 
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a message in the conversation history with duplicate prevention.
        
        Args:
            user_id: Telegram user ID
            message: Message content
            is_user: Whether the message is from the user (True) or bot (False)
            metadata: Additional metadata like emotions, context, etc.
        """
        try:
            with db_session_context() as session:
                # Check for recent duplicate within 1 second window
                recent = session.query(Conversation)\
                    .filter(
                        Conversation.user_id == user_id,
                        Conversation.message == message,
                        Conversation.timestamp >= datetime.now() - timedelta(seconds=1)
                    ).first()
                
                if recent is None:
                    conversation = Conversation(
                        user_id=user_id,
                        message=message,
                        is_user=is_user,
                        message_metadata=json.dumps(metadata or {}),
                        timestamp=datetime.now()
                    )
                    session.add(conversation)
                    session.commit()
                    
                    # Only run these if we actually added a new message
                    self._check_and_summarize_history(user_id, session)
                    self._cleanup_expired_memories(user_id, session)
                else:
                    logger.debug(f"Prevented duplicate message for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store message: {str(e)}")
            # Continue execution even if storage fails
    
    def get_recent_context(self, user_id: int, limit: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
        """Get recent conversation context for a user.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries with sender and content
        """
        try:
            with db_session_context() as session:
                # Get recent direct messages
                recent_messages = session.query(Conversation)\
                    .filter(Conversation.user_id == user_id)\
                    .order_by(Conversation.timestamp.desc())\
                    .limit(limit)\
                    .all()
                
                # Convert to format suitable for context
                context = []
                for msg in reversed(recent_messages):  # Oldest first
                    role = "user" if msg.is_user else "assistant"
                    context.append({
                        "role": role,
                        "content": msg.message,
                        "timestamp": msg.timestamp,
                        "metadata": msg.metadata
                    })
                
                # Get latest summary if we have fewer than the limit
                if len(context) < limit:
                    summary = self._get_latest_summary(user_id, session)
                    if summary:
                        # Add summary at the beginning to provide background context
                        context.insert(0, {
                            "role": "system",
                            "content": f"Previous conversation summary: {summary.content}",
                            "timestamp": summary.created_at,
                            "metadata": {"type": "summary"}
                        })
                
                return context
                
        except Exception as e:
            logger.error(f"Failed to retrieve conversation context: {str(e)}")
            return []
    
    def recall_by_topic(self, user_id: int, topic: str) -> List[Dict[str, Any]]:
        """Recall conversations related to a specific topic.
        
        Args:
            user_id: Telegram user ID
            topic: Topic to search for
            
        Returns:
            List of relevant messages
        """
        try:
            with db_session_context() as session:
                # First check summaries for the topic
                summaries = session.query(ConversationSummary)\
                    .filter(ConversationSummary.user_id == user_id,
                            ConversationSummary.content.contains(topic))\
                    .order_by(ConversationSummary.created_at.desc())\
                    .limit(3)\
                    .all()
                
                relevant_context = []
                
                # Add summaries if found
                for summary in summaries:
                    relevant_context.append({
                        "role": "system",
                        "content": f"Remembered: {summary.content}",
                        "timestamp": summary.created_at,
                        "metadata": {"type": "memory", "confidence": 0.9}
                    })
                
                # Then check recent messages
                recent_messages = session.query(Conversation)\
                    .filter(Conversation.user_id == user_id,
                            Conversation.message.contains(topic))\
                    .order_by(Conversation.timestamp.desc())\
                    .limit(5)\
                    .all()
                
                # Add messages if found
                for msg in recent_messages:
                    role = "user" if msg.is_user else "assistant"
                    relevant_context.append({
                        "role": role,
                        "content": msg.message,
                        "timestamp": msg.timestamp,
                        "metadata": msg.metadata
                    })
                
                return relevant_context
                
        except Exception as e:
            logger.error(f"Failed to recall by topic: {str(e)}")
            return []
    
    def get_user_relationship(self, user_id: int) -> Dict[str, Any]:
        """Get user relationship data for contextual personalization.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with relationship metrics and preferences
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                
                if not user:
                    # Create default user entry if not exists
                    return {
                        "familiarity": 0.1,
                        "friendship_level": "stranger",
                        "interaction_count": 0,
                        "preferences": {},
                        "topics_discussed": []
                    }
                
                # Calculate relationship metrics
                message_count = session.query(Conversation)\
                    .filter(Conversation.user_id == user_id)\
                    .count()
                
                # Normalize familiarity between 0 and 1
                # This grows with interaction count but plateaus
                familiarity = min(0.9, message_count / 100) if message_count > 0 else 0.1
                
                # Map familiarity to friendship level
                friendship_level = "stranger"
                if familiarity > 0.7:
                    friendship_level = "close_friend"
                elif familiarity > 0.4:
                    friendship_level = "friend"
                elif familiarity > 0.2:
                    friendship_level = "acquaintance"
                
                return {
                    "familiarity": familiarity,
                    "friendship_level": friendship_level,
                    "interaction_count": message_count,
                    "preferences": user.preferences or {},
                    "topics_discussed": user.topics_discussed or []
                }
                
        except Exception as e:
            logger.error(f"Failed to get user relationship data: {str(e)}")
            return {
                "familiarity": 0.1,
                "friendship_level": "stranger",
                "interaction_count": 0,
                "preferences": {},
                "topics_discussed": []
            }
    
    def reset_conversation_context(self, user_id: int) -> bool:
        """Reset conversation context for a user while maintaining relationship data.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            with db_session_context() as session:
                # Delete all conversation messages for this user
                session.query(Conversation)\
                    .filter(Conversation.user_id == user_id)\
                    .delete(synchronize_session=False)
                
                # Delete conversation summaries
                session.query(ConversationSummary)\
                    .filter(ConversationSummary.user_id == user_id)\
                    .delete(synchronize_session=False)
                
                # Commit the changes
                session.commit()
                
                logger.info(f"Reset conversation context for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to reset conversation context: {str(e)}")
            return False
    
    def _check_and_summarize_history(self, user_id: int, session) -> None:
        """Check if we need to summarize conversation history and do so if necessary.
        
        Args:
            user_id: Telegram user ID
            session: Database session
        """
        # Check when the last summary was created
        last_summary = session.query(ConversationSummary)\
            .filter(ConversationSummary.user_id == user_id)\
            .order_by(ConversationSummary.created_at.desc())\
            .first()
            
        # If no summary exists, or last summary is older than SUMMARY_INTERVAL
        summary_needed = False
        if not last_summary:
            summary_needed = True
        else:
            days_since_summary = (datetime.now() - last_summary.created_at).days
            if days_since_summary >= SUMMARY_INTERVAL:
                summary_needed = True
        
        # If we need a summary, get messages to summarize
        if summary_needed and self.gemini_client:
            # Get messages since the last summary or up to SUMMARY_INTERVAL days back
            if last_summary:
                since_date = last_summary.created_at
            else:
                since_date = datetime.now() - timedelta(days=SUMMARY_INTERVAL)
                
            # Get messages to summarize
            messages_to_summarize = session.query(Conversation)\
                .filter(Conversation.user_id == user_id,
                        Conversation.timestamp > since_date,
                        Conversation.timestamp < datetime.now() - timedelta(days=1))\
                .order_by(Conversation.timestamp.asc())\
                .all()
                
            if len(messages_to_summarize) > 10:  # Only summarize if we have enough messages
                self._generate_conversation_summary(user_id, messages_to_summarize, session)
    
    def _generate_conversation_summary(self, user_id: int, messages: List[Conversation], session) -> None:
        """Generate a summary of conversation messages using Gemini.
        
        Args:
            user_id: Telegram user ID
            messages: List of messages to summarize
            session: Database session
        """
        try:
            # Format messages for the summarization prompt
            conversation_text = []
            for msg in messages:
                speaker = "User" if msg.is_user else "Alya"
                conversation_text.append(f"{speaker}: {msg.message}")
            
            if not conversation_text:
                return
                
            conversation_chunk = "\n".join(conversation_text)
            
            # Create the summarization prompt
            prompt = (
                "Please summarize the following conversation between a user and Alya (a waifu-like "
                "AI assistant with tsundere personality).\n\n"
                "Focus on:\n"
                "1. Key topics discussed\n"
                "2. Important information shared by the user\n"
                "3. Any preferences or interests revealed\n"
                "4. Emotional tone of the conversation\n"
                "5. Any promises or commitments made\n\n"
                "Keep the summary concise (2-3 sentences) while capturing the essence. "
                "Write in third person perspective.\n\n"
                f"Conversation to summarize:\n{conversation_chunk}"
            )
            
            # Generate summary using Gemini
            response = self.gemini_client.generate_content(prompt, max_tokens=150)
            
            if response and response.strip():
                # Store the summary
                summary = ConversationSummary(
                    user_id=user_id,
                    content=response.strip(),
                    message_count=len(messages),
                    created_at=datetime.now()
                )
                session.add(summary)
                session.commit()
                logger.info(f"Generated conversation summary for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to generate conversation summary: {str(e)}")
    
    def _get_latest_summary(self, user_id: int, session) -> Optional[ConversationSummary]:
        """Get the latest conversation summary for a user.
        
        Args:
            user_id: Telegram user ID
            session: Database session
            
        Returns:
            Latest summary object or None
        """
        return session.query(ConversationSummary)\
            .filter(ConversationSummary.user_id == user_id)\
            .order_by(ConversationSummary.created_at.desc())\
            .first()
    
    def _cleanup_expired_memories(self, user_id: int, session) -> None:
        """Clean up expired messages based on retention policy.
        
        Args:
            user_id: Telegram user ID
            session: Database session
        """
        if MEMORY_EXPIRY_DAYS <= 0:
            return  # No cleanup if expiry is disabled
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=MEMORY_EXPIRY_DAYS)
            
            # Delete messages older than cutoff date
            session.query(Conversation)\
                .filter(Conversation.user_id == user_id, 
                        Conversation.timestamp < cutoff_date)\
                .delete(synchronize_session=False)
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Failed to clean up expired messages: {str(e)}")
    
    def create_context_prompt(self, user_id: int, query: str) -> str:
        """Create a context-enriched prompt for AI processing.
        
        This adapter method gathers conversation context and formats it for prompt use.
        
        Args:
            user_id: Telegram user ID
            query: Current user query/message
            
        Returns:
            Context-enriched prompt string for AI processing
        """
        # Get recent conversation context
        context = self.get_conversation_context(user_id)
        if not context:
            # If no context available, just return the query
            return query
            
        # Format context into a coherent prompt
        prompt_parts = []
        
        # Include system context if available
        system_context = next((item for item in context if item.get('role') == 'system'), None)
        if system_context:
            prompt_parts.append(f"Previous context: {system_context.get('content', '')}")
            
        # Add recent conversation turns (last 3-5 messages)
        conversation_turns = [item for item in context if item.get('role') != 'system'][-5:]
        for turn in conversation_turns:
            role = "User" if turn.get('role') == 'user' else "Alya"
            prompt_parts.append(f"{role}: {turn.get('content', '')}")
            
        # Add current query
        prompt_parts.append(f"User: {query}")
        
        # Add system instruction to maintain continuity
        prompt_parts.append(
            "Based on the conversation history above, continue the conversation as Alya, "
            "responding to the last user message."
        )
        
        # Join all parts with line breaks
        return "\n\n".join(prompt_parts)
    
    def get_conversation_context(self, user_id: int, limit: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
        """Get conversation context for a user in format compatible with Gemini API.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries formatted for Gemini API
        """
        # Get the raw context first
        raw_context = self.get_recent_context(user_id, limit)
        
        # Transform to Gemini-compatible format
        gemini_format = []
        for item in raw_context:
            # Extract the role and content, ignoring timestamp and metadata
            role = item.get("role", "user")  # Default to user if missing
            content = item.get("content", "")
            
            # Format in Gemini-expected structure with 'parts' array
            gemini_format.append({
                "role": role,
                "parts": [{"text": content}]
            })
        
        return gemini_format
