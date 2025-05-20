"""
Rate Limiting Utilities for Alya Bot.

This module provides utilities for limiting the rate of various operations
to ensure responsible use of external APIs and prevent abuse.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable, Tuple, Union
import functools

logger = logging.getLogger(__name__)

# Type variables for generics
T = TypeVar('T')

class RateLimiter:
    """
    Rate limiter implementation to prevent abuse.
    """
    def __init__(self, 
                 rate: int = 3, 
                 per: int = 60, 
                 operations_per_minute: Optional[int] = None,
                 operations_per_user_minute: Optional[int] = None,
                 cooldown_period: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed (deprecated, use operations_per_minute)
            per: Time period in seconds (deprecated)
            operations_per_minute: Number of operations allowed per minute
            operations_per_user_minute: Number of operations allowed per user per minute
            cooldown_period: Additional cooldown period in seconds
        """
        # Handle both old and new parameter styles
        if operations_per_minute is not None:
            self.rate = operations_per_minute
            self.per = 60  # Always per minute
        else:
            self.rate = rate
            self.per = per
            
        self.user_rate = operations_per_user_minute if operations_per_user_minute is not None else self.rate
        self.cooldown = cooldown_period if cooldown_period is not None else 0
        
        self.allowance = {}  # Global allowance
        self.user_allowance = {}  # Per-user allowance
        self.last_check = {}
        self.user_last_check = {}

    # Deprecated - use acquire_with_feedback instead
    async def acquire(self, user_id: Optional[int] = None) -> bool:
        """
        Attempt to acquire a token for the user.
        
        Args:
            user_id: Telegram user ID (optional)
            
        Returns:
            True if allowed, False if rate limited
        """
        allowed, _ = await self._check_rate_limits(user_id)
        return allowed

    async def acquire_with_feedback(self, 
                                   update_or_user_id: Any = None, 
                                   context_or_type: Any = None,
                                   *args, **kwargs) -> Tuple[bool, Optional[float]]:
        """
        Acquire with feedback on wait time. Handles both legacy and new parameter formats.
        
        Args:
            update_or_user_id: Either Update object, user_id, or None
            context_or_type: Either context object, operation type, or None
            *args: Additional args (ignored)
            **kwargs: Additional kwargs (ignored)
            
        Returns:
            Tuple of (allowed: bool, wait_time: Optional[float]) indicating if request is allowed and wait time
        """
        # Extract user_id from different parameter types
        user_id = self._extract_user_id(update_or_user_id)
        
        # Check actual rate limiting
        allowed, wait_time = await self._check_rate_limits(user_id)
        
        # If not allowed and we have an update object, provide feedback
        if not allowed and wait_time and wait_time > 0 and hasattr(update_or_user_id, 'message'):
            await self._send_rate_limit_feedback(update_or_user_id, context_or_type, wait_time)
                    
        return allowed, wait_time  # Return tuple of (bool, float) instead of just bool
    
    def _extract_user_id(self, update_or_user_id: Any) -> Optional[int]:
        """Extract user ID from various input types."""
        if update_or_user_id is None:
            return None
            
        # Handle Update object
        if hasattr(update_or_user_id, 'effective_user') and update_or_user_id.effective_user:
            return update_or_user_id.effective_user.id
            
        # Handle direct user_id (int)
        if isinstance(update_or_user_id, int):
            return update_or_user_id
            
        return None
    
    async def _send_rate_limit_feedback(self, update: Any, context_or_type: Any, wait_time: float) -> None:
        """Send rate limit feedback message to user."""
        try:
            operation = "chat" if isinstance(context_or_type, str) else "operation"
            wait_seconds = int(wait_time) + 1
            await update.message.reply_text(
                f"Mohon tunggu {wait_seconds} detik sebelum mengirimkan {operation} lain."
            )
        except Exception as e:
            logger.error(f"Error sending rate limit message: {e}")
        
    async def _check_rate_limits(self, user_id: Optional[int] = None) -> Tuple[bool, Optional[float]]:
        """
        Internal method to check rate limits and calculate wait time.
        
        Args:
            user_id: Optional user ID to check
            
        Returns:
            Tuple of (allowed, wait_time)
        """
        current = time.time()
        global_key = 'global'
        
        # Check global rate limit first
        global_allowed, global_wait = self._check_single_limit(
            global_key, self.allowance, self.last_check, 
            self.rate, self.per, current
        )
        
        # If no user_id, just return global result
        if user_id is None:
            return global_allowed, global_wait
            
        # Check user-specific rate limit
        user_allowed, user_wait = self._check_single_limit(
            user_id, self.user_allowance, self.user_last_check,
            self.user_rate, self.per, current
        )
        
        # If both allowed, consume tokens and return success
        if global_allowed and user_allowed:
            self.allowance[global_key] -= 1.0
            self.user_allowance[user_id] -= 1.0
            return True, None
            
        # Return the longer wait time
        wait_time = max(global_wait or 0.0, user_wait or 0.0)
        return False, wait_time
    
    def _check_single_limit(
        self, key: Union[str, int], 
        allowance_dict: Dict, last_check_dict: Dict,
        rate: float, per: float, current: float
    ) -> Tuple[bool, Optional[float]]:
        """Check a single rate limit (global or per-user)."""
        # Initialize if not present
        if key not in allowance_dict:
            allowance_dict[key] = rate
            last_check_dict[key] = current
            return True, None
            
        # Calculate time passed and add tokens
        time_passed = current - last_check_dict[key]
        last_check_dict[key] = current
        
        allowance_dict[key] += time_passed * (rate / per)
        
        # Cap at max rate
        if allowance_dict[key] > rate:
            allowance_dict[key] = rate
            
        # Check if we have enough tokens
        if allowance_dict[key] < 1.0:
            # Calculate wait time needed
            wait_time = (1.0 - allowance_dict[key]) * per / rate
            return False, wait_time
        
        return True, None

    def get_wait_time(self, user_id: Optional[int] = None) -> float:
        """
        Get wait time for user to have another token available.
        
        Args:
            user_id: Telegram user ID (optional)
            
        Returns:
            Wait time in seconds
        """
        global_key = 'global'
        global_wait = 0.0
        
        if global_key in self.allowance and self.allowance[global_key] < 1.0:
            global_wait = (1.0 - self.allowance[global_key]) * self.per / self.rate
            
        # If no user_id provided, just return global wait time
        if user_id is None:
            return global_wait
            
        # Check user wait time
        user_wait = 0.0
        if user_id in self.user_allowance and self.user_allowance[user_id] < 1.0:
            user_wait = (1.0 - self.user_allowance[user_id]) * self.per / self.user_rate
            
        # Return the longer wait time
        return max(global_wait, user_wait)

    async def wait_if_needed(self, user_id: Optional[int] = None) -> None:
        """
        Wait if rate limited, then acquire token.
        
        Args:
            user_id: Telegram user ID (optional)
        """
        allowed, wait_time = await self._check_rate_limits(user_id)
        if not allowed and wait_time is not None:
            logger.debug(f"Rate limited, waiting for {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            # Recurse - should succeed after waiting
            await self.wait_if_needed(user_id)

# Create standard limiters for various operations
limiter = RateLimiter(operations_per_minute=30, operations_per_user_minute=10)
heavy_limiter = RateLimiter(operations_per_minute=15, operations_per_user_minute=5, cooldown_period=2)
gemini_limiter = RateLimiter(operations_per_minute=60, operations_per_user_minute=15)

class APIKeyManager:
    """
    Manages rotation of API keys for external services.
    
    This class provides functionality to rotate through multiple API keys
    when rate limits are reached, ensuring continuous operation.
    """
    
    def __init__(self, primary_key: str, backup_keys: Optional[list[str]] = None):
        """
        Initialize API key manager.
        
        Args:
            primary_key: Primary API key
            backup_keys: List of backup API keys
        """
        self.primary_key = primary_key
        self.backup_keys = backup_keys or []
        self.all_keys = [primary_key] + self.backup_keys
        self.current_key_index = 0
        self.key_usage_count = {key: 0 for key in self.all_keys}
        self.key_last_used = {key: 0 for key in self.all_keys}
        
        # Skip empty backup keys
        self.all_keys = [k for k in self.all_keys if k.strip()]
        logger.debug(f"APIKeyManager initialized with {len(self.all_keys)} keys")

    def get_current_key(self) -> str:
        """
        Get the current API key.
        
        Returns:
            Current API key
        """
        if not self.all_keys:
            return ""
        
        current_key = self.all_keys[self.current_key_index]
        self.key_usage_count[current_key] += 1
        self.key_last_used[current_key] = time.time()
        return current_key

    def rotate_key(self, force: bool = False) -> str:
        """
        Rotate to the next API key.
        
        Args:
            force: Force rotation even if not needed
            
        Returns:
            New API key
        """
        if not self.all_keys:
            return ""
        
        if not force and (time.time() - self.key_last_used[self.all_keys[self.current_key_index]]) < 60:
            return self.get_current_key()
        
        self.current_key_index = (self.current_key_index + 1) % len(self.all_keys)
        logger.info(f"Rotated to API key #{self.current_key_index+1}")
        return self.get_current_key()

    def get_least_used_key(self) -> str:
        """
        Get the least used API key.
        
        Returns:
            Least used API key
        """
        if not self.all_keys:
            return ""
        
        least_used = min(self.all_keys, key=lambda k: self.key_usage_count[k])
        return least_used

    def get_key_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for all keys.
        
        Returns:
            Dictionary mapping masked API keys to usage count
        """
        stats = {}
        for key in self.all_keys:
            masked_key = key[:4] + "..." + key[-4:]
            stats[masked_key] = self.key_usage_count[key]
        return stats

# Initialize API Key Manager - fixed to avoid circular import
def init_api_key_manager():
    """Initialize API Key Manager from settings."""
    from config.settings import GEMINI_API_KEY, GEMINI_BACKUP_API_KEYS
    return APIKeyManager(GEMINI_API_KEY, GEMINI_BACKUP_API_KEYS)

# Create singleton instance
api_key_manager = init_api_key_manager()

# Function to get API key manager (NOT a property)
def get_api_key_manager():
    """Get API Key Manager singleton instance."""
    global api_key_manager
    return api_key_manager

# Decorator for rate-limited functions
def rate_limited(rate_limiter: RateLimiter):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        rate_limiter: RateLimiter instance to use
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            user_id = None
            if args and hasattr(args[0], 'effective_user') and args[0].effective_user:
                user_id = args[0].effective_user.id
            
            await rate_limiter.wait_if_needed(user_id)
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

# Make sure these are directly exported
__all__ = [
    'RateLimiter',
    'limiter',
    'heavy_limiter',
    'gemini_limiter',
    'api_key_manager',
    'get_api_key_manager',
    'rate_limited',
    'APIKeyManager'
]