"""
Memory manager for handling conversation history and context management.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from config.settings import MEMORY_EXPIRY_DAYS, MAX_CONTEXT_MESSAGES, SLIDING_WINDOW_SIZE
from core.gemini_client import GeminiClient
from database.models import Conversation, ConversationSummary, User
from database.session import db_session_context

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages conversation memory and context for users with sliding window and summary."""
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client

    def save_user_message(self, user_id: int, message: str) -> None:
        """Store a user message in the conversation history."""
        self.store_message(user_id, message, is_user=True)

    def save_bot_response(self, user_id: int, message: str) -> None:
        """Store a bot response in the conversation history."""
        self.store_message(user_id, message, is_user=False)

    def store_message(self, user_id: int, message: str, is_user: bool = True, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a message in the conversation history with duplicate prevention."""
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    from database.database_manager import create_default_user
                    user = create_default_user(session, user_id)
                # Prevent duplicate within 1 second
                recent = session.query(Conversation)\
                    .filter(
                        Conversation.user_id == user_id,
                        Conversation.content == message,
                        Conversation.created_at >= datetime.now() - timedelta(seconds=1)
                    ).first()
                if recent is None:
                    conversation = Conversation(
                        user_id=user_id,
                        content=message,
                        role="user" if is_user else "assistant",
                        is_user=is_user,
                        message_metadata=metadata or {},
                        created_at=datetime.now()
                    )
                    session.add(conversation)
                    session.commit()
                    self.apply_sliding_window(user_id, session)
                else:
                    logger.debug(f"Prevented duplicate message for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to store message: {str(e)}", exc_info=True)

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
                recent_messages = session.query(Conversation)\
                    .filter(Conversation.user_id == user_id)\
                    .order_by(Conversation.created_at.desc())\
                    .limit(limit)\
                    .all()
                context = []
                for msg in reversed(recent_messages):
                    role = "user" if msg.is_user else "assistant"
                    context.append({
                        "role": role,
                        "content": msg.content,
                        "timestamp": msg.created_at,
                        "metadata": msg.message_metadata or {}
                    })
                if len(context) < limit:
                    summary = self._get_latest_summary(user_id, session)
                    if summary:
                        context.insert(0, {
                            "role": "summary",
                            "content": summary.content,
                            "timestamp": summary.created_at,
                            "metadata": {}
                        })
                return context
        except Exception as e:
            logger.error(f"Failed to retrieve conversation context: {str(e)}")
            return []

    def apply_sliding_window(self, user_id: int, session) -> None:
        """Apply sliding window to conversation history, summarizing and deleting old messages as needed.
        
        Args:
            user_id: Telegram user ID
            session: Database session
        """
        messages = session.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .order_by(Conversation.created_at.asc())\
            .all()
        if len(messages) > SLIDING_WINDOW_SIZE:
            # Summarize old messages
            old_messages = messages[:len(messages) - SLIDING_WINDOW_SIZE]
            summary_text = self._summarize_messages([m.content for m in old_messages])
            summary = ConversationSummary(
                user_id=user_id,
                content=summary_text,
                summary_type='auto',
                message_count=len(old_messages),
                date_range_start=old_messages[0].created_at,
                date_range_end=old_messages[-1].created_at,
                model_used="Gemini" if self.gemini_client else "simple-join"
            )
            session.add(summary)
            # Delete old messages
            for m in old_messages:
                session.delete(m)
            session.commit()
            logger.info(f"Sliding window applied for user {user_id}, summarized {len(old_messages)} messages.")

    def _summarize_messages(self, messages: List[str]) -> str:
        """Summarize a list of messages using Gemini or fallback method.
        
        Args:
            messages: List of message strings to summarize
            
        Returns:
            Summary string
        """
        if self.gemini_client and messages:
            try:
                # Use Gemini to summarize if available
                prompt = "Ringkas percakapan berikut secara singkat dan natural (Bahasa Indonesia):\n" + "\n".join(messages)
                # GeminiClient.generate_response is async, so we use a sync fallback here
                # In production, consider running this in an async context
                import asyncio
                loop = asyncio.get_event_loop()
                summary = loop.run_until_complete(
                    self.gemini_client.generate_response(
                        user_id=0,
                        username="system",
                        message=prompt,
                        context="",
                        relationship_level=0,
                        is_admin=True,
                        lang='id',
                        retry_count=2
                    )
                )
                return summary
            except Exception as e:
                logger.error(f"Failed to summarize with Gemini: {e}")
        # Fallback: simple join
        return "\n".join(messages)

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
                summaries = session.query(ConversationSummary)\
                    .filter(ConversationSummary.user_id == user_id,
                            ConversationSummary.content.contains(topic))\
                    .order_by(ConversationSummary.created_at.desc())\
                    .limit(3)\
                    .all()
                relevant_context = []
                for summary in summaries:
                    relevant_context.append({
                        "role": "summary",
                        "content": summary.content,
                        "timestamp": summary.created_at,
                        "metadata": {}
                    })
                return relevant_context
        except Exception as e:
            logger.error(f"Failed to recall by topic: {e}")
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
                if user:
                    return {
                        "relationship_level": user.relationship_level,
                        "affection_points": user.affection_points,
                        "interaction_count": user.interaction_count
                    }
        except Exception as e:
            logger.error(f"Failed to get user relationship: {e}")
        return {"relationship_level": 0, "affection_points": 0, "interaction_count": 0}
