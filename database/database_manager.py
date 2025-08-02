"""
Enterprise-grade MySQL database manager for Alya Bot.
Handles all database operations with proper connection pooling, error handling, and transaction management.
"""
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.orm import Session

from database.session import db_session_context, execute_with_session, health_check
from database.models import User, Conversation, ConversationSummary, ApiUsage, UserSettings
from config.settings import (
    MEMORY_EXPIRY_DAYS,
    RELATIONSHIP_THRESHOLDS,
    RELATIONSHIP_LEVELS,
    AFFECTION_POINTS,
    RELATIONSHIP_ROLE_NAMES,
    ADMIN_IDS
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


def get_user_lang(user_id: int, db_manager: Any) -> str:
    """
    Gets a user's preferred language from the database.

    Args:
        user_id: The ID of the user.
        db_manager: The instance of the database manager.

    Returns:
        The user's language code ('id' or 'en'), defaulting to 'id'.
    """
    if db_manager:
        user_settings = db_manager.get_user_settings(user_id)
        # The settings are now in a flat dictionary, not nested
        if user_settings and user_settings.get('language'):
            return user_settings['language']
    return 'id'


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
        Update user settings in the database.
        This method fetches existing settings, merges them with new ones,
        and saves the result.

        Args:
            user_id: The user's ID.
            new_settings: A dictionary with the settings to update.
        """
        session = self.Session()
        try:
            user_settings = session.query(UserSettings).filter_by(user_id=user_id).first()
            if user_settings:
                # Correctly merge JSON data
                current_preferences = user_settings.preferences or {}
                current_preferences.update(new_settings)
                user_settings.preferences = current_preferences
            else:
                # If no settings exist, create a new record
                user_settings = UserSettings(user_id=user_id, preferences=new_settings)
                session.add(user_settings)
            
            session.commit()
            logger.info(f"Successfully updated settings for user {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update user settings for {user_id}: {e}", exc_info=True)
        finally:
            session.close()

    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves user-specific settings, such as language preference.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A dictionary with user settings or an empty dict if not found.
        """
        try:
            with db_session_context() as session:
                settings = session.query(UserSettings).filter(UserSettings.user_id == user_id).first()
                if settings and settings.preferences:
                    # Return the preferences dictionary directly
                    return settings.preferences
                return {}
        except Exception as e:
            logger.error(f"Error getting user settings for {user_id}: {e}")
            return {}

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
                
                # Optionally, reset interaction count and topics in User table
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.interaction_count = 0
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
                        language_code="id",
                        created_at=datetime.now(),
                        last_interaction=datetime.now(),
                        is_active=True,
                        relationship_level=0,
                        affection_points=0,
                        interaction_count=0,
                        preferences={
                            "notification_enabled": True,
                            "preferred_language": "id",
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
                        language_code="id",
                        created_at=datetime.now(),
                        last_interaction=datetime.now(),
                        is_active=True,
                        relationship_level=0,
                        affection_points=0,
                        interaction_count=0,
                        preferences={
                            "notification_enabled": True,
                            "preferred_language": "id",
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
    
    def update_affection(self, user_id: int, points: int) -> bool:
        """
        Update user's affection points and relationship level.
        
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
                    logger.warning(f"User {user_id} not found for affection update")
                    return False
                
                # Ensure we have integer types for calculations
                current_affection = int(user.affection_points) if user.affection_points is not None else 0
                current_interactions = int(user.interaction_count) if user.interaction_count is not None else 0
                old_level = int(user.relationship_level) if user.relationship_level is not None else 0
                
                # Update affection points (don't go below 0)
                new_affection = max(0, current_affection + int(points))
                user.affection_points = new_affection
                
                # Calculate new relationship level
                new_level = self._calculate_relationship_level(new_affection, current_interactions)
                
                if new_level != old_level:
                    user.relationship_level = new_level
                    logger.info(f"User {user_id} relationship level: {old_level} -> {new_level}")
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating affection for user {user_id}: {e}")
            return False
    
    def get_user_relationship_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's relationship information and statistics formatted for /stats command.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict containing relationship info in expected format
        """
        try:
            with db_session_context() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.debug(f"User {user_id} not found in database")
                    return {}
                
                logger.debug(f"Found user {user_id}: level={user.relationship_level}, affection={user.affection_points}, interactions={user.interaction_count}")
                
                # Calculate relationship progress
                level = user.relationship_level
                current_interactions = user.interaction_count
                current_affection = user.affection_points
                
                # Use settings from config
                level_names = list(RELATIONSHIP_LEVELS.values())
                interaction_thresholds = RELATIONSHIP_THRESHOLDS["interaction_count"]
                affection_thresholds = RELATIONSHIP_THRESHOLDS["affection_points"]
                
                # Ensure level is within bounds
                level = min(level, len(level_names) - 1)
                
                # Calculate progress to next level
                if level < len(level_names) - 1:
                    next_level = level + 1
                    interaction_needed = interaction_thresholds.get(next_level, float('inf'))
                    affection_needed = affection_thresholds.get(next_level, float('inf'))
                    
                    # Calculate progress based on both interaction and affection requirements
                    interaction_progress = min(100.0, (current_interactions / interaction_needed) * 100) if interaction_needed != float('inf') else 100.0
                    affection_progress = min(100.0, (current_affection / affection_needed) * 100) if affection_needed != float('inf') else 100.0
                    
                    # Overall progress is the minimum of both (both requirements must be met)
                    progress_percent = min(interaction_progress, affection_progress)
                    next_level_at_interaction = interaction_needed
                    next_level_at_affection = affection_needed
                else:
                    # Max level reached
                    progress_percent = 100.0
                    next_level_at_interaction = current_interactions
                    next_level_at_affection = current_affection
                
                # Calculate affection progress for display (based on max achievable points)
                max_affection_for_display = 500  # Reasonable max for progress bar
                affection_display_percent = min(100.0, max(0.0, (current_affection / max_affection_for_display) * 100))
                
                # Get user role
                role = get_role_by_relationship_level(level, user_id in ADMIN_IDS)
                
                return {
                    "name": user.username or user.first_name or f"User{user_id}",
                    "relationship": {
                        "level": level,
                        "name": level_names[level],
                        "interactions": current_interactions,
                        "next_level_at_interaction": next_level_at_interaction,
                        "next_level_at_affection": next_level_at_affection,
                        "progress_percent": progress_percent
                    },
                    "affection": {
                        "points": current_affection,
                        "progress_percent": affection_display_percent
                    },
                    "stats": {
                        "total_messages": current_interactions,
                        "positive_interactions": max(0, current_affection),  # Positive affection
                        "negative_interactions": max(0, -current_affection),  # Negative affection
                        "role": role,
                        "topics_discussed": len(user.topics_discussed or []),
                        "last_interaction": user.last_interaction.isoformat() if user.last_interaction else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting relationship info for user {user_id}: {e}")
            return {}
    
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
    
    def _calculate_relationship_level(self, affection_points: int, interaction_count: int) -> int:
        """
        Calculate relationship level based on affection points and interactions.
        
        Args:
            affection_points: Current affection points
            interaction_count: Total interactions
            
        Returns:
            int: Relationship level (0-10)
        """
        # Convert values to int to avoid comparison errors
        affection_points = int(affection_points) if affection_points is not None else 0
        interaction_count = int(interaction_count) if interaction_count is not None else 0
        
        # Get affection thresholds from nested config
        affection_thresholds = RELATIONSHIP_THRESHOLDS.get("affection_points", {})
        interaction_thresholds = RELATIONSHIP_THRESHOLDS.get("interaction_count", {})
        
        # Calculate level based on affection points
        affection_level = 0
        for level, threshold in affection_thresholds.items():
            if affection_points >= int(threshold):
                affection_level = int(level)
        
        # Calculate level based on interaction count
        interaction_level = 0
        for level, threshold in interaction_thresholds.items():
            if interaction_count >= int(threshold):
                interaction_level = int(level)
        
        # Take the higher of both levels
        final_level = max(affection_level, interaction_level)
        
        # Cap at maximum level
        max_level = max(RELATIONSHIP_LEVELS) if RELATIONSHIP_LEVELS else 10
        return min(final_level, max_level)
    
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
                        language_code="id",
                        created_at=datetime.now(),
                        last_interaction=datetime.now(),
                        is_active=True,
                        relationship_level=0,
                        affection_points=0,
                        interaction_count=0,
                        preferences={
                            "notification_enabled": True,
                            "preferred_language": "id",
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

db_manager = DatabaseManager()