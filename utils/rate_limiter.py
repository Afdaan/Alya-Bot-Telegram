"""
Rate limiting utilities for API calls and request management.

This module provides rate limiting decorators and an API key rotation manager
to ensure API quota compliance and graceful fallbacks.
"""
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable, Optional, Union, TypeVar, Awaitable, Tuple
from functools import wraps

# Setup logger
logger = logging.getLogger(__name__)

# Type variables for generic function annotations
T = TypeVar('T')
FuncT = TypeVar('FuncT', bound=Callable[..., Any])
AsyncFuncT = TypeVar('AsyncFuncT', bound=Callable[..., Awaitable[Any]])

class ApiKeyRateLimiter:
    """Rate limiter for API requests with configurable limits."""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_timestamps: List[float] = []
        self._lock = asyncio.Lock()
        self._user_rate_limits: Dict[int, float] = {}
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make a request.
        
        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            current_time = time.time()
            # Remove timestamps outside the window
            self.request_timestamps = [t for t in self.request_timestamps 
                                      if current_time - t < self.time_window]
            
            # Check if we're under the limit
            if len(self.request_timestamps) < self.max_requests:
                self.request_timestamps.append(current_time)
                return True
            
            return False
    
    async def wait_for_capacity(self) -> None:
        """Wait until request capacity is available."""
        while True:
            if await self.acquire():
                return
            
            # Calculate wait time based on oldest request
            current_time = time.time()
            if self.request_timestamps:
                oldest = min(self.request_timestamps)
                wait_time = self.time_window - (current_time - oldest)
                wait_time = max(0.1, wait_time)
            else:
                wait_time = 0.5
            
            logger.debug(f"Rate limit reached. Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    @property
    def rate(self) -> int:
        """Get current rate limit."""
        return self.max_requests

    def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if the user is rate limited (per-user simple limiter).

        Args:
            user_id: User ID

        Returns:
            True if user can proceed, False if rate limited
        """
        if not hasattr(self, "_user_rate_limits"):
            self._user_rate_limits = {}
            
        now = time.time()
        last_time = self._user_rate_limits.get(user_id, 0)
        # 1 second cooldown per user (can be adjusted)
        if now - last_time < 1:
            return False
            
        self._user_rate_limits[user_id] = now
        return True

    async def acquire_with_feedback(self, user_id: Optional[int] = None) -> Tuple[bool, float]:
        """
        Try to acquire permission to make a request, returning if allowed and wait time if not.

        Args:
            user_id: Optional user ID for per-user rate limiting (not used in global limiter)

        Returns:
            Tuple (allowed: bool, wait_time: float)
        """
        async with self._lock:
            current_time = time.time()
            self.request_timestamps = [t for t in self.request_timestamps
                                      if current_time - t < self.time_window]
            if len(self.request_timestamps) < self.max_requests:
                self.request_timestamps.append(current_time)
                return True, 0.0
            # Calculate wait time until next slot is available
            oldest = min(self.request_timestamps) if self.request_timestamps else current_time
            wait_time = self.time_window - (current_time - oldest)
            wait_time = max(0.1, wait_time)
            return False, wait_time

# Default limiter for Gemini API with free tier limits
gemini_limiter = ApiKeyRateLimiter(max_requests=60, time_window=60)

# Alias for backward compatibility (for legacy imports)
limiter = gemini_limiter

def rate_limited(limiter: ApiKeyRateLimiter):
    """
    Decorator for rate limiting async functions.
    
    Args:
        limiter: The rate limiter to use
        
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: AsyncFuncT) -> AsyncFuncT:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.wait_for_capacity()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class ApiKeyManager:
    """
    Manager for API key rotation to handle rate limits and quotas.
    """
    
    def __init__(self, 
                 primary_key: str, 
                 backup_keys: Optional[List[str]] = None, 
                 cooldown_period: int = 60):
        """
        Initialize API key manager.
        
        Args:
            primary_key: Primary API key
            backup_keys: List of backup API keys
            cooldown_period: Cooldown period in seconds for failed keys
        """
        self.primary_key = primary_key.strip() if primary_key else ""
        self.backup_keys = [k.strip() for k in (backup_keys or []) if k and k.strip()]
        self.all_keys = [self.primary_key] + self.backup_keys if self.primary_key else self.backup_keys
        self.cooldown_period = cooldown_period
        self.current_key_index = 0
        self.key_last_failed: Dict[str, datetime] = {}
        
        # Filter out empty keys
        self.all_keys = [k for k in self.all_keys if k]
        
        if not self.all_keys:
            logger.warning("No API keys provided. Functionality will be limited.")
        else:
            logger.info(f"API Key Manager initialized with {len(self.all_keys)} keys")
    
    def get_current_key(self) -> str:
        """
        Get current API key.
        
        Returns:
            Current API key
        """
        if not self.all_keys:
            raise ValueError("No API keys available")
        
        current_key = self.all_keys[self.current_key_index]
        
        # Check if key is in cooldown
        if current_key in self.key_last_failed:
            cooldown_end = self.key_last_failed[current_key] + timedelta(seconds=self.cooldown_period)
            if datetime.now() < cooldown_end:
                # Current key is in cooldown, try to rotate
                return self.rotate_key()
        
        return current_key
    
    def rotate_key(self, force: bool = False) -> str:
        """
        Rotate to next available API key.
        
        Args:
            force: Force rotation even if current key is valid
            
        Returns:
            New API key
        """
        if not self.all_keys:
            raise ValueError("No API keys available")
        
        if len(self.all_keys) == 1:
            return self.all_keys[0]  # Only one key, nothing to rotate
        
        # Mark the current key as failed if forced
        if force:
            current_key = self.all_keys[self.current_key_index]
            self.key_last_failed[current_key] = datetime.now()
        
        # Find next available key not in cooldown
        initial_index = self.current_key_index
        while True:
            # Move to next key
            self.current_key_index = (self.current_key_index + 1) % len(self.all_keys)
            
            # Get the new key
            next_key = self.all_keys[self.current_key_index]
            
            # Check if this key is usable (not in cooldown)
            if next_key in self.key_last_failed:
                cooldown_end = self.key_last_failed[next_key] + timedelta(seconds=self.cooldown_period)
                if datetime.now() >= cooldown_end:
                    # Cooldown has ended
                    return next_key
            else:
                # Key has never failed
                return next_key
                
            # If we've tried all keys and come back to the initial one, just use it
            if self.current_key_index == initial_index:
                return self.all_keys[self.current_key_index]
    
    def mark_key_failed(self, key: str) -> None:
        """
        Mark an API key as failed.
        
        Args:
            key: The API key that failed
        """
        self.key_last_failed[key] = datetime.now()
        
        # If it's the current key, rotate
        if self.all_keys[self.current_key_index] == key:
            self.rotate_key()

    def get_key_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics about API keys.
        
        Returns:
            List of dictionaries with key statistics
        """
        stats = []
        for i, key in enumerate(self.all_keys):
            # Get first 5 chars of key for display
            key_prefix = key[:5] + "..." if key else "None"
            is_current = (i == self.current_key_index)
            
            # Check if key is in cooldown
            in_cooldown = False
            cooldown_ends = None
            
            if key in self.key_last_failed:
                cooldown_end = self.key_last_failed[key] + timedelta(seconds=self.cooldown_period)
                in_cooldown = datetime.now() < cooldown_end
                if in_cooldown:
                    cooldown_ends = cooldown_end.strftime("%H:%M:%S")
            
            stats.append({
                "key_prefix": key_prefix,
                "is_current": is_current,
                "in_cooldown": in_cooldown,
                "cooldown_ends": cooldown_ends,
                "index": i
            })
        
        return stats

# Import settings
from config.settings import GEMINI_API_KEY, GEMINI_BACKUP_API_KEYS

# Create global API key manager instance
api_key_manager = ApiKeyManager(
    primary_key=GEMINI_API_KEY,
    backup_keys=GEMINI_BACKUP_API_KEYS,
    cooldown_period=300  # 5 minutes cooldown for failed keys
)

def get_api_key_manager() -> ApiKeyManager:
    """
    Get the global API key manager instance.
    
    Returns:
        ApiKeyManager instance
    """
    return api_key_manager