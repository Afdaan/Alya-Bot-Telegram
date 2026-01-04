"""
Enterprise-grade MySQL database manager for Alya Bot.
Handles all database operations with proper connection pooling, error handling, and transaction management.
"""
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from database.session import db_session_context, execute_with_session, health_check
from database.models import User, Conversation, ConversationSummary, ApiUsage
from config.settings import (
    MEMORY_EXPIRY_DAYS,
    RELATIONSHIP_THRESHOLDS,
    RELATIONSHIP_LEVELS,
    AFFECTION_POINTS,
    RELATIONSHIP_ROLE_NAMES,
    ADMIN_IDS,
    DEFAULT_LANGUAGE
)

logger = logging.getLogger(__name__)


def get_role_by_relationship_level(relationship_level: int, is_admin: bool = False) -> str:
    """
    Get user role name based on relationship level.
    
    Args:
        relationship_level: Current relationship level (0-10)
        is_admin: Whether user is admin
        
    Returns:
        str: Role name for display purposes
    """
    if is_admin:
        return "Admin-sama"
    
    return RELATIONSHIP_ROLE_NAMES.get(relationship_level, "Stranger")


def get_user_lang(user_id: int) -> str:
    """
    Gets a user's preferred language directly from the database.

    Args:
        user_id: The ID of the user.

    Returns:
        The user's language code ('id' or 'en'), defaulting to DEFAULT_LANGUAGE.
    """
    try:
        with db_session_context() as session:
            user = session.query(User.language_code).filter(User.id == user_id).first()
            if user and user.language_code:
                return user.language_code
    except Exception as e:
        logger.error(f"Error getting user language for {user_id}: {e}", exc_info=True)
    return DEFAULT_LANGUAGE


# --- Utility: Centralized user creation (DRY) ---
def create_default_user(session: Session, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> 'User':
    """Create a new user with default values and commit to session."""
    from config.settings import DEFAULT_LANGUAGE
    user = User(
        id=user_id,
        username=username or None,
        first_name=first_name or f"User{user_id}",
        last_name=last_name or None,
        language_code=DEFAULT_LANGUAGE,
        created_at=datetime.now(),
        last_interaction=datetime.now(),
        is_active=True,
        relationship_level=0,
        affection_points=0,
        interaction_count=0,
        preferences={
            "notification_enabled": True,
            "preferred_language": DEFAULT_LANGUAGE,
            "persona": "waifu",
            "timezone": "Asia/Jakarta"
        },
        topics_discussed=[]
    )
    session.add(user)
    session.flush()
    return user


class DatabaseManager:
    """
    Enterprise-grade MySQL database manager using SQLAlchemy.
    
    Handles all database operations for Alya Bot including:
    - User management and relationship tracking
    - Conversation history with RAG support
    - Memory management and summarization
    - API usage tracking
    - Performance optimization with caching
    """
    
    def __init__(self) -> None:
        """Initialize the database manager with caching and health monitoring."""
        self.recent_message_hashes = {}  # Cache for recent message hashes
        self._last_health_check = datetime.now()
        self._health_check_interval = timedelta(minutes=5)
        
        # Perform initial health check
        if health_check():
            logger.info("Database manager initialized successfully")
        else:
            logger.error("Database connection failed during initialization")
            raise ConnectionError("Unable to connect to MySQL database")
    
    def update_user_settings(self, user_id: int, new_settings: Dict[str, Any]) -> None:
        """
        Update user settings in the database, specifically for language.
        This now updates the `language_code` in the `users` table.

        Args:
            user_id: The user's ID.
            new_settings: A dictionary containing the 'language' to set.
        """
        if 'language' not in new_settings:
            logger.warning(f"Attempted to update settings for user {user_id} without 'language' key.")
            return

        try:
            with db_session_context() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    user.language_code = new_settings['language']
                    session.commit()
                    logger.info(f"Successfully updated language to '{new_settings['language']}' for user {user_id}")
                else:
                    logger.warning(f"User {user_id} not found when trying to update language.")
        except Exception as e:
            logger.error(f"Failed to update user settings for {user_id}: {e}", exc_info=True)

    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves user-specific settings, primarily language preference from `users.language_code`.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A dictionary with the user's language, defaulting to 'id'.
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user and user.language_code:
                    return {'language': user.language_code}
                return {'language': DEFAULT_LANGUAGE}
        except Exception as e:
            logger.error(f"Error getting user settings for {user_id}: {e}", exc_info=True)
            return {'language': DEFAULT_LANGUAGE}

    def reset_user_conversation(self, user_id: int) -> bool:
        """
        Deletes all conversation history for a specific user.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with db_session_context() as session:
                # Delete from Conversation table
                session.query(Conversation).filter(Conversation.user_id == user_id).delete(synchronize_session=False)
                
                # Delete from ConversationSummary table
                session.query(ConversationSummary).filter(ConversationSummary.user_id == user_id).delete(synchronize_session=False)
                
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.topics_discussed = []
                    user.last_interaction = datetime.now()

                session.commit()
                logger.info(f"Successfully reset conversation history for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error resetting conversation history for user {user_id}: {e}")
            return False

    def _check_health_periodically(self) -> None:
        """Perform periodic health checks to ensure database connectivity."""
        now = datetime.now()
        if now - self._last_health_check > self._health_check_interval:
            if not health_check():
                logger.warning("Database health check failed - connection may be unstable")
            self._last_health_check = now
    
    def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "", 
                           last_name: str = "", is_admin: bool = False) -> Dict[str, Any]:
        """
        Get or create a user in the database with proper error handling.
        
        Args:
            user_id: Telegram user ID
            username: Username (without @)
            first_name: User's first name
            last_name: User's last name
            is_admin: Whether user has admin privileges
            
        Returns:
            Dict containing user data, empty dict on error
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                
                if not user:
                    # Create new user with default values
                    user = User(
                        id=user_id,
                        username=username or None,
                        first_name=first_name or None,
                        last_name=last_name or None,
                        language_code=DEFAULT_LANGUAGE,
                        created_at=datetime.now(),
                        last_interaction=datetime.now(),
                        is_active=True,
                        relationship_level=0,
                        affection_points=0,
                        interaction_count=0,
                        preferences={
                            "notification_enabled": True,
                            "preferred_language": DEFAULT_LANGUAGE,
                            "persona": "waifu",
                            "timezone": "Asia/Jakarta"
                        },
                        topics_discussed=[]
                    )
                    session.add(user)
                    session.commit()
                    logger.info(f"Created new user: {user_id} ({first_name or username})")
                    
                else:
                    # Update existing user data if provided
                    updated = False
                    if username and user.username != username:
                        user.username = username
                        updated = True
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name
                        updated = True
                    if last_name and user.last_name != last_name:
                        user.last_name = last_name
                        updated = True
                    
                    if updated:
                        user.last_interaction = datetime.now()
                        session.commit()
                        logger.debug(f"Updated user data for {user_id}")
                
                # Return user data as dictionary
                return {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "language_code": user.language_code,
                    "relationship_level": user.relationship_level,
                    "affection_points": user.affection_points,
                    "interaction_count": user.interaction_count,
                    "preferences": user.preferences or {},
                    "topics_discussed": user.topics_discussed or [],
                    "created_at": user.created_at,
                    "last_interaction": user.last_interaction,
                    "is_admin": is_admin or user_id in ADMIN_IDS,
                    "role_name": get_role_by_relationship_level(
                        user.relationship_level, 
                        user_id in ADMIN_IDS
                    )
                }
                
        except Exception as e:
            logger.error(f"Error getting/creating user {user_id}: {e}")
            return {}
    
    def save_message(self, user_id: int, role: str, content: str, 
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a message to conversation history with deduplication.
        
        Args:
            user_id: Telegram user ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata for the message
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Create message hash for deduplication
            message_hash = hashlib.md5(f"{user_id}:{content}:{role}".encode()).hexdigest()
            
            with db_session_context() as session:
                # CRITICAL: Ensure user exists before saving conversation
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    # Auto-create user if not exists to prevent foreign key constraint errors
                    logger.warning(f"User {user_id} not found, creating automatically")
                    user = User(
                        id=user_id,
                        username=None,
                        first_name=f"User{user_id}",
                        last_name=None,
                        language_code=DEFAULT_LANGUAGE,
                        created_at=datetime.now(),
                        last_interaction=datetime.now(),
                        is_active=True,
                        relationship_level=0,
                        affection_points=0,
                        interaction_count=0,
                        preferences={
                            "notification_enabled": True,
                            "preferred_language": DEFAULT_LANGUAGE,
                            "persona": "waifu",
                            "timezone": "Asia/Jakarta"
                        },
                        topics_discussed=[]
                    )
                    session.add(user)
                    session.flush()  # Ensure user is created before conversation
                
                # Check for recent duplicate (last 5 minutes)
                recent_cutoff = datetime.now() - timedelta(minutes=5)
                duplicate = session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    Conversation.message_hash == message_hash,
                    Conversation.created_at > recent_cutoff
                ).first()
                
                if duplicate:
                    logger.debug(f"Skipping duplicate message for user {user_id}")
                    return True
                
                # Create conversation entry
                conversation = Conversation(
                    user_id=user_id,
                    content=content,
                    role=role,
                    is_user=(role == "user"),
                    message_hash=message_hash,
                    message_metadata=metadata or {},
                    created_at=datetime.now()
                )
                session.add(conversation)
                
                # Update user interaction count and last interaction
                user.interaction_count += 1
                user.last_interaction = datetime.now()
                
                session.commit()
                
                # Cache the message hash
                self.recent_message_hashes[user_id] = message_hash
                
                logger.debug(f"Saved {role} message for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving message for user {user_id}: {e}")
            return False
    
    def get_conversation_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user with proper ordering.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages in chronological order
        """
        try:
            with db_session_context() as session:
                conversations = (
                    session.query(Conversation)
                    .filter(Conversation.user_id == user_id)
                    .order_by(Conversation.created_at.desc())
                    .limit(limit)
                    .all()
                )
                
                # Reverse to get chronological order (oldest first)
                history = []
                for conv in reversed(conversations):
                    history.append({
                        "id": conv.id,
                        "role": conv.role,
                        "content": conv.content,
                        "created_at": conv.created_at,
                        "metadata": conv.message_metadata or {},
                        "sentiment_score": conv.sentiment_score,
                        "emotion_category": conv.emotion_category
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting conversation history for user {user_id}: {e}")
            return []
    
    def get_conversation_summaries(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve conversation summaries for a user, ordered by most recent.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of summaries to return
        Returns:
            List of summary dicts (most recent first)
        """
        try:
            with db_session_context() as session:
                summaries = (
                    session.query(ConversationSummary)
                    .filter(ConversationSummary.user_id == user_id)
                    .order_by(ConversationSummary.created_at.desc())
                    .limit(limit)
                    .all()
                )
                result = []
                for summary in summaries:
                    result.append({
                        "id": summary.id,
                        "content": summary.content,
                        "summary_type": summary.summary_type,
                        "message_count": summary.message_count,
                        "date_range_start": summary.date_range_start,
                        "date_range_end": summary.date_range_end,
                        "model_used": summary.model_used,
                        "summary_metadata": summary.get_summary_metadata(),
                        "created_at": summary.created_at
                    })
                return result
        except Exception as e:
            logger.error(f"Error getting conversation summaries for user {user_id}: {e}", exc_info=True)
            return []

    def update_affection(self, user_id: int, points: int) -> bool:
        """
        Update user's affection points and relationship level.
        
        IMPORTANT: Level is determined by BOTH affection AND interaction thresholds.
        User gets whichever level is higher (max of both metrics).
        
        Args:
            user_id: Telegram user ID
            points: Points to add (can be negative)
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    user = create_default_user(session, user_id)
                
                current_affection = int(user.affection_points) if user.affection_points is not None else 0
                old_level = int(user.relationship_level) if user.relationship_level is not None else 0
                
                # Update affection points
                new_affection = max(0, current_affection + int(points))
                user.affection_points = new_affection
                
                # Calculate level based on BOTH metrics (same logic as increment_interaction_count)
                affection_level = self._calculate_relationship_level(
                    new_affection, 
                    mode="affection_points"
                )
                interaction_level = self._calculate_relationship_level(
                    user.interaction_count or 0, 
                    mode="interaction_count"
                )
                
                # User gets the benefit of whichever threshold they've reached
                new_level = max(affection_level, interaction_level)
                
                if new_level != old_level:
                    user.relationship_level = new_level
                    logger.warning(
                        f"[DB] LEVEL UPDATE via affection! User {user_id}: "
                        f"level {old_level} → {new_level} "
                        f"(affection: {new_affection}, affection_level: {affection_level}, "
                        f"interaction_level: {interaction_level})"
                    )
                
                session.commit()
                
                logger.info(
                    f"Updated affection for user {user_id}: "
                    f"{current_affection} -> {new_affection}, level {old_level} -> {new_level}"
                )
                return True
        except Exception as e:
            logger.error(f"Error updating affection for user {user_id}: {e}", exc_info=True)
            return False

    def increment_interaction_count(self, user_id: int) -> bool:
        """Increment user's interaction count and recalculate relationship level.
        
        This should be called for each meaningful conversation turn to track
        relationship progression based on interaction frequency.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    user = create_default_user(session, user_id)
                
                old_count = int(user.interaction_count) if user.interaction_count else 0
                old_level = int(user.relationship_level) if user.relationship_level else 0
                
                # Increment interaction count
                new_count = old_count + 1
                user.interaction_count = new_count
                
                # Recalculate level based on BOTH interaction_count AND affection_points
                # Take the HIGHER of the two to determine actual level
                affection_level = self._calculate_relationship_level(
                    user.affection_points or 0, 
                    mode="affection_points"
                )
                interaction_level = self._calculate_relationship_level(
                    new_count, 
                    mode="interaction_count"
                )
                
                # User gets the benefit of whichever threshold they've reached
                new_level = max(affection_level, interaction_level)
                
                if new_level != old_level:
                    user.relationship_level = new_level
                    logger.warning(
                        f"[DB] LEVEL UP via interaction! User {user_id}: "
                        f"level {old_level} → {new_level} "
                        f"(interactions: {new_count}, affection_level: {affection_level}, "
                        f"interaction_level: {interaction_level})"
                    )
                
                session.commit()
                
                logger.debug(
                    f"[DB] Incremented interaction count for user {user_id}: "
                    f"{old_count} → {new_count}, level: {old_level} → {new_level}"
                )
                
                return True
        except Exception as e:
            logger.error(f"Error incrementing interaction count for user {user_id}: {e}", exc_info=True)
            return False
    
    def _calculate_relationship_level(self, value: int, mode: str = "affection_points") -> int:
        """Calculate relationship level based on affection points or interaction count.
        
        This method determines the user's relationship level by comparing their
        progress against configured thresholds. The level represents how close
        the user is to Alya, affecting her behavior and response tone.
        
        Args:
            value: The value to compare (affection points or interaction count)
            mode: Which threshold to use ('affection_points' or 'interaction_count')
            
        Returns:
            int: Relationship level (0-4)
                0 = Stranger
                1 = Acquaintance  
                2 = Friend
                3 = Close Friend
                4 = Soulmate
                
        Example:
            >>> _calculate_relationship_level(150, mode="affection_points")
            2  # Friend level (threshold: 80-150)
        """
        try:
            # Get thresholds from config
            thresholds = RELATIONSHIP_THRESHOLDS.get(mode)
            
            if not thresholds or not isinstance(thresholds, dict):
                logger.error(f"[DB] Invalid relationship threshold mode: {mode}")
                return 0
            
            # Check thresholds in descending order to find highest level reached
            # Example: {1: 30, 2: 80, 3: 150, 4: 300}
            for level in sorted(thresholds.keys(), reverse=True):
                threshold = thresholds[level]
                if value >= threshold:
                    logger.debug(
                        f"[DB] Level calculation: value={value}, mode={mode}, "
                        f"threshold={threshold}, result_level={level}"
                    )
                    return int(level)
            
            # If no threshold reached, user is still at level 0
            return 0
            
        except Exception as e:
            logger.error(f"[DB] Error calculating relationship level: {e}", exc_info=True)
            return 0
    
    def get_user_relationship_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's relationship information and statistics formatted for /stat command.
        Returns only minimal, always-populated fields.
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return {
                        "relationship_level": 0,
                        "affection_points": 0,
                        "interaction_count": 0,
                        "role_name": get_role_by_relationship_level(0),
                        "topics_discussed": [],
                        "persona": "waifu"
                    }
                return {
                    "relationship_level": user.relationship_level,
                    "affection_points": user.affection_points,
                    "interaction_count": user.interaction_count,
                    "role_name": get_role_by_relationship_level(user.relationship_level, user_id in ADMIN_IDS),
                    "topics_discussed": user.topics_discussed or [],
                    "persona": user.preferences.get("persona", "waifu") if user.preferences else "waifu"
                }
        except Exception as e:
            logger.error(f"Error getting user relationship info for {user_id}: {e}", exc_info=True)
            return {
                "relationship_level": 0,
                "affection_points": 0,
                "interaction_count": 0,
                "role_name": get_role_by_relationship_level(0),
                "topics_discussed": [],
                "persona": "waifu"
            }
    
    def reset_conversation(self, user_id: int) -> bool:
        """
        Reset conversation history for a user while preserving user data.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if reset successfully, False otherwise
        """
        try:
            with db_session_context() as session:
                # Delete conversations
                deleted_convs = session.query(Conversation).filter(
                    Conversation.user_id == user_id
                ).delete()
                
                # Delete summaries
                deleted_summaries = session.query(ConversationSummary).filter(
                    ConversationSummary.user_id == user_id
                ).delete()
                
                session.commit()
                
                # Clear cache
                if user_id in self.recent_message_hashes:
                    del self.recent_message_hashes[user_id]
                
                logger.info(f"Reset conversation for user {user_id}: {deleted_convs} messages, {deleted_summaries} summaries")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting conversation for user {user_id}: {e}")
            return False
    
    def cleanup_old_data(self) -> None:
        """Clean up old conversation data based on expiry settings."""
        try:
            cutoff_date = datetime.now() - timedelta(days=MEMORY_EXPIRY_DAYS)
            
            with db_session_context() as session:
                # Delete old conversations
                old_conversations = session.query(Conversation).filter(
                    Conversation.created_at < cutoff_date
                ).delete()
                
                # Delete old summaries
                old_summaries = session.query(ConversationSummary).filter(
                    ConversationSummary.created_at < cutoff_date
                ).delete()
                
                session.commit()
                
                logger.info(f"Cleaned up {old_conversations} old conversations and {old_summaries} summaries")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def apply_sliding_window(self, user_id: int, keep_recent: int) -> bool:
        """
        Apply sliding window to conversation history.
        
        Args:
            user_id: Telegram user ID
            keep_recent: Number of recent messages to keep
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with db_session_context() as session:
                # Get total conversation count
                total_count = session.query(Conversation).filter(
                    Conversation.user_id == user_id
                ).count()
                
                if total_count <= keep_recent:
                    return True  # No need to apply sliding window
                
                # Get IDs of messages to keep (most recent)
                recent_messages = (
                    session.query(Conversation.id)
                    .filter(Conversation.user_id == user_id)
                    .order_by(Conversation.created_at.desc())
                    .limit(keep_recent)
                    .subquery()
                )
                
                # Delete older messages
                deleted_count = session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    ~Conversation.id.in_(recent_messages)
                ).delete(synchronize_session=False)
                
                session.commit()
                
                logger.info(f"Applied sliding window for user {user_id}: deleted {deleted_count} old messages")
                return True
                
        except Exception as e:
            logger.error(f"Error applying sliding window for user {user_id}: {e}")
            return False
    
    def search_conversations(self, user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search user's conversation history for relevant messages.
        
        Args:
            user_id: Telegram user ID
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching conversations
        """
        try:
            with db_session_context() as session:
                conversations = (
                    session.query(Conversation)
                    .filter(
                        Conversation.user_id == user_id,
                        Conversation.content.ilike(f"%{query}%")
                    )
                    .order_by(Conversation.created_at.desc())
                    .limit(limit)
                    .all()
                )
                
                results = []
                for conv in conversations:
                    results.append({
                        "id": conv.id,
                        "content": conv.content,
                        "role": conv.role,
                        "created_at": conv.created_at,
                        "metadata": conv.message_metadata or {}
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching conversations for user {user_id}: {e}")
            return []
    
    def track_api_usage(self, user_id: Optional[int], provider: str, method: str, 
                       input_tokens: int = 0, output_tokens: int = 0, 
                       cost_cents: int = 0, success: bool = True, 
                       error_message: str = None) -> bool:
        """
        Track API usage for monitoring and cost analysis.
        
        Args:
            user_id: User ID (None for system usage)
            provider: API provider (gemini, openai, etc.)
            method: API method called
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            cost_cents: Estimated cost in cents
            success: Whether the API call succeeded
            error_message: Error message if failed
            
        Returns:
            bool: True if tracked successfully
        """
        try:
            with db_session_context() as session:
                usage = ApiUsage(
                    user_id=user_id,
                    api_provider=provider,
                    api_method=method,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    estimated_cost_cents=cost_cents,
                    success=success,
                    error_message=error_message,
                    created_at=datetime.now()
                )
                session.add(usage)
                session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Error tracking API usage: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics for monitoring.
        
        Returns:
            Dict containing database statistics
        """
        try:
            with db_session_context() as session:
                user_count = session.query(User).count()
                active_users = session.query(User).filter(User.is_active == True).count()
                conversation_count = session.query(Conversation).count()
                summary_count = session.query(ConversationSummary).count()
                
                # Get recent activity (last 24 hours)
                recent_cutoff = datetime.now() - timedelta(hours=24)
                recent_messages = session.query(Conversation).filter(
                    Conversation.created_at > recent_cutoff
                ).count()
                
                return {
                    "total_users": user_count,
                    "active_users": active_users,
                    "total_conversations": conversation_count,
                    "total_summaries": summary_count,
                    "recent_messages_24h": recent_messages,
                    "health_status": "healthy" if health_check() else "unhealthy"
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """
        Alias for get_database_stats() to maintain compatibility.
        
        Returns:
            Dict containing database statistics
        """
        return self.get_database_stats()
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if a user is an admin.
        
        Args:
            user_id: Telegram user ID to check
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        try:
            # First check against ADMIN_IDS from config (faster)
            if user_id in ADMIN_IDS:
                return True
                
            # Then check database is_admin flag if user exists
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    # Check if user has is_admin attribute and it's True
                    return getattr(user, 'is_admin', False)
                return False
                
        except Exception as e:
            logger.error(f"Error checking admin status for user {user_id}: {e}")
            # Fallback to config check only
            return user_id in ADMIN_IDS

    def test_connection(self) -> bool:
        """
        Test the database connection with a simple query.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            with db_session_context() as session:
                # Perform a lightweight query to check connection
                result = session.execute("SELECT 1")
                return result.scalar() == 1
                
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def ensure_user_exists(self, user_id: int, username: str = "", first_name: str = "", 
                          last_name: str = "") -> bool:
        """
        Ensure a user exists in the database, create if not exists.
        This prevents foreign key constraint errors when saving conversations.
        
        Args:
            user_id: Telegram user ID
            username: Username (optional)
            first_name: First name (optional)
            last_name: Last name (optional)
            
        Returns:
            bool: True if user exists or was created successfully
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    # Create new user with minimal data
                    user = User(
                        id=user_id,
                        username=username or None,
                        first_name=first_name or f"User{user_id}",
                        last_name=last_name or None,
                        language_code=DEFAULT_LANGUAGE,
                        created_at=datetime.now(),
                        last_interaction=datetime.now(),
                        is_active=True,
                        relationship_level=0,
                        affection_points=0,
                        interaction_count=0,
                        preferences={
                            "notification_enabled": True,
                            "preferred_language": DEFAULT_LANGUAGE,
                            "persona": "waifu",
                            "timezone": "Asia/Jakarta"
                        },
                        topics_discussed=[]
                    )
                    session.add(user)
                    session.commit()
                    logger.info(f"Auto-created user {user_id} to prevent foreign key errors")
                
                return True
                
        except Exception as e:
            logger.error(f"Error ensuring user {user_id} exists: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves user information from the database.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A dictionary with user information or None if not found.
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    return {
                        'id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'language_code': user.language_code,
                        'is_admin': user_id in ADMIN_IDS,
                        'relationship_level': user.relationship_level,
                        'interaction_count': user.interaction_count,
                        'affection_points': user.affection_points,
                        'last_interaction': user.last_interaction,
                        'created_at': user.created_at
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
            return None

    def save_conversation_summary(self, user_id: int, summary: Dict[str, Any]) -> bool:
        """
        Save a conversation summary for a user.
        Args:
            user_id: Telegram user ID
            summary: Dict with keys: content, message_count, date_range_start, date_range_end, etc.
        Returns:
            bool: True if saved successfully
        """
        try:
            with db_session_context() as session:
                new_summary = ConversationSummary(
                    user_id=user_id,
                    content=summary.get("content", ""),
                    summary_type=summary.get("summary_type", "auto"),
                    message_count=summary.get("message_count", 0),
                    date_range_start=summary.get("date_range_start"),
                    date_range_end=summary.get("date_range_end"),
                    model_used=summary.get("model_used"),
                    summary_metadata=summary.get("summary_metadata", {})
                )
                session.add(new_summary)
                session.commit()
                logger.info(f"Saved conversation summary for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error saving conversation summary for user {user_id}: {e}", exc_info=True)
            return False

    def delete_conversation_messages(self, user_id: int, before: Any) -> int:
        """
        Delete conversation messages for a user before a certain timestamp.
        Args:
            user_id: Telegram user ID
            before: Timestamp (datetime) to delete messages before
        Returns:
            int: Number of messages deleted
        """
        try:
            with db_session_context() as session:
                deleted = session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    Conversation.created_at < before
                ).delete(synchronize_session=False)
                session.commit()
                logger.info(f"Deleted {deleted} old conversation messages for user {user_id}")
                return deleted
        except Exception as e:
            logger.error(f"Error deleting conversation messages for user {user_id}: {e}", exc_info=True)
            return 0

    def get_rag_texts(self, user_id: int, limit: int = 10) -> list:
        """
        Retrieve relevant conversation texts for RAG (Retrieval-Augmented Generation).
        Args:
            user_id: Telegram user ID
            limit: Number of texts to retrieve
        Returns:
            List of dicts: [{"text": str}]
        """
        try:
            with db_session_context() as session:
                conversations = (
                    session.query(Conversation.content)
                    .filter(Conversation.user_id == user_id)
                    .order_by(Conversation.created_at.desc())
                    .limit(limit)
                    .all()
                )
                return [{"text": conv.content} for conv in conversations]
        except Exception as e:
            logger.error(f"Error in get_rag_texts for user {user_id}: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # MOOD SYSTEM METHODS
    # ========================================================================
    
    def update_user_mood(
        self, 
        user_id: int, 
        mood: str, 
        intensity: int,
        mood_history: List[Dict[str, Any]] = None
    ) -> bool:
        """
        Update user's current mood state.
        
        Args:
            user_id: Telegram user ID
            mood: New mood state (happy, tsundere, affectionate, neutral, annoyed, sad)
            intensity: Mood intensity (0-100)
            mood_history: Optional updated mood history
            
        Returns:
            bool: True if updated successfully
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.warning(f"Cannot update mood for non-existent user {user_id}")
                    return False
                
                old_mood = user.current_mood
                user.current_mood = mood
                user.mood_intensity = intensity
                user.last_mood_change = datetime.now()
                
                if mood_history is not None:
                    user.mood_history = mood_history
                
                session.commit()
                
                logger.info(
                    f"Updated mood for user {user_id}: {old_mood} → {mood} "
                    f"(intensity: {intensity})"
                )
                return True
                
        except Exception as e:
            logger.error(f"Error updating mood for user {user_id}: {e}", exc_info=True)
            return False
    
    def get_user_mood(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's current mood state.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict with mood, intensity, last_change, and history
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return {
                        "mood": "neutral",
                        "intensity": 50,
                        "last_change": datetime.now(),
                        "history": []
                    }
                
                return {
                    "mood": user.current_mood or "neutral",
                    "intensity": user.mood_intensity or 50,
                    "last_change": user.last_mood_change or datetime.now(),
                    "history": user.mood_history or []
                }
                
        except Exception as e:
            logger.error(f"Error getting mood for user {user_id}: {e}", exc_info=True)
            return {
                "mood": "neutral",
                "intensity": 50,
                "last_change": datetime.now(),
                "history": []
            }

db_manager = DatabaseManager()