"""
Cache Management Utilities for Alya Bot.

This module provides caching functionality for API responses and other
expensive operations to improve performance and reduce external API calls.
"""

import logging
import time
from typing import Dict, Any, Optional, TypeVar, Generic, Callable, Tuple
import functools

logger = logging.getLogger(__name__)

# Type variable for generic caching
T = TypeVar('T')

class ResponseCache(Generic[T]):
    """
    In-memory response cache with TTL and size limits.
    
    This class provides a thread-safe cache for storing and retrieving
    responses with automatic expiration and size limiting.
    """
    
    def __init__(self, 
                max_size: int = 1000, 
                default_ttl: int = 3600,
                max_key_length: int = 128):
        """
        Initialize response cache.
        
        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds
            max_key_length: Maximum key length for cache keys
        """
        self._cache: Dict[str, Tuple[T, float]] = {}  # value, expiry
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._max_key_length = max_key_length
        logger.debug(f"Initialized cache with max_size={max_size}, default_ttl={default_ttl}s")
    
    def get(self, key: str) -> Optional[T]:
        """
        Get item from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if not key or len(key) > self._max_key_length:
            return None
            
        # Find in cache
        cached = self._cache.get(key)
        if not cached:
            return None
            
        # Check if expired
        value, expiry = cached
        if time.time() > expiry:
            # Expired, remove from cache
            del self._cache[key]
            return None
            
        return value
    
    def set(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """
        Set item in cache with optional custom TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
            
        Returns:
            True if successful, False otherwise
        """
        # Validate key
        if not key or len(key) > self._max_key_length:
            return False
            
        # Manage cache size
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._evict()
            
        # Calculate expiry
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        
        # Store in cache
        self._cache[key] = (value, expiry)
        return True
    
    def _evict(self) -> None:
        """Evict items from cache using LRU policy."""
        # First try to remove expired items
        now = time.time()
        expired_keys = [
            k for k, (_, exp) in self._cache.items() 
            if exp < now
        ]
        
        for key in expired_keys:
            del self._cache[key]
            
        # If still over size, remove oldest items
        if len(self._cache) >= self._max_size:
            # Sort by expiry (oldest first)
            sorted_items = sorted(
                self._cache.items(), 
                key=lambda item: item[1][1]
            )
            
            # Remove 10% of oldest items
            items_to_remove = max(1, len(sorted_items) // 10)
            for i in range(items_to_remove):
                if i < len(sorted_items):
                    del self._cache[sorted_items[i][0]]
    
    def clear(self, prefix: Optional[str] = None) -> int:
        """
        Clear items from cache, optionally by prefix.
        
        Args:
            prefix: Optional prefix to selectively clear
            
        Returns:
            Number of items removed from cache
        """
        if not prefix:
            count = len(self._cache)
            self._cache = {}
            return count
            
        # Clear by prefix
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
            
        return len(keys_to_remove)
    
    def clear_all(self) -> int:
        """
        Clear all items from cache.
        
        Returns:
            Number of items removed
        """
        count = len(self._cache)
        self._cache.clear()
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        now = time.time()
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'usage_percent': int((len(self._cache) / self._max_size) * 100) if self._max_size > 0 else 0,
            'expired_count': sum(1 for _, exp in self._cache.values() if exp < now),
            'avg_ttl': sum(exp - now for _, exp in self._cache.values()) / len(self._cache) if self._cache else 0
        }

# Create singleton instance
response_cache = ResponseCache()

# Cache decorator
def cached(ttl: Optional[int] = None, prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Optional time-to-live in seconds
        prefix: Optional cache key prefix
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [prefix or func.__name__]
            
            # Add positional args to key
            for arg in args:
                # Skip self/cls for methods
                if not isinstance(arg, type) and not hasattr(arg, '__dict__'):
                    key_parts.append(str(arg))
            
            # Add keyword args to key (sorted for consistent keys)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
                
            cache_key = ":".join(key_parts)
            
            # Check cache
            cached_result = response_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
                
            # Call function
            result = func(*args, **kwargs)
            
            # Cache result
            response_cache.set(cache_key, result, ttl)
            
            return result
            
        return wrapper
    
    return decorator

# Async cache decorator
def async_cached(ttl: Optional[int] = None, prefix: str = ""):
    """
    Decorator to cache async function results.
    
    Args:
        ttl: Optional time-to-live in seconds
        prefix: Optional cache key prefix
        
    Returns:
        Decorated async function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [prefix or func.__name__]
            
            # Add positional args to key
            for arg in args:
                # Skip self/cls for methods
                if not isinstance(arg, type) and not hasattr(arg, '__dict__'):
                    key_parts.append(str(arg))
            
            # Add keyword args to key (sorted for consistent keys)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
                
            cache_key = ":".join(key_parts)
            
            # Check cache
            cached_result = response_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
                
            # Call async function
            result = await func(*args, **kwargs)
            
            # Cache result
            response_cache.set(cache_key, result, ttl)
            
            return result
            
        return wrapper
    
    return decorator
