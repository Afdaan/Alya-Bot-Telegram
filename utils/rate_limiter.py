"""
Rate Limiting for Telegram Bot.

Module ini mengelola pembatasan penggunaan fitur untuk mencegah
spam dan flood control dari Telegram API.
"""

import time
import logging
from typing import Dict, Tuple
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for bot commands with per-user and global limits."""
    
    def __init__(self):
        # Command limits: {command: (max_calls, period_seconds)}
        self.command_limits = {
            "search": (2, 10),  # 2 calls per 10 seconds per user
            "image": (2, 10),   # 2 calls per 10 seconds per user
            "sauce": (2, 10),   # 2 calls per 10 seconds per user
            "trace": (2, 10),   # 2 calls per 10 seconds per user
            "roast": (3, 30),   # 3 calls per 30 seconds per user
            "default": (5, 10)  # 5 calls per 10 seconds for other commands
        }
        
        # Global rate limits
        self.global_limit = (20, 60)  # 20 calls per 60 seconds across all users
        
        # Track command usage: {command: {user_id: [(timestamp, count), ...]}}
        self.user_usage = defaultdict(lambda: defaultdict(list))
        
        # Track global usage: [(timestamp, count), ...]
        self.global_usage = []
    
    def _clean_old_records(self, records: list, period: int) -> list:
        """Remove records older than the specified period."""
        current_time = time.time()
        return [r for r in records if current_time - r[0] < period]
    
    def _is_user_rate_limited(self, command: str, user_id: int) -> Tuple[bool, int]:
        """Check if a user is rate limited for a command.
        
        Returns:
            Tuple of (is_limited, seconds_to_wait)
        """
        limit_data = self.command_limits.get(command, self.command_limits["default"])
        max_calls, period = limit_data
        
        # Clean old records
        self.user_usage[command][user_id] = self._clean_old_records(
            self.user_usage[command][user_id], period
        )
        
        # Count recent calls
        recent_calls = sum(record[1] for record in self.user_usage[command][user_id])
        
        if recent_calls >= max_calls:
            # Calculate wait time based on oldest record
            if self.user_usage[command][user_id]:
                oldest_timestamp = self.user_usage[command][user_id][0][0]
                wait_seconds = int(period - (time.time() - oldest_timestamp)) + 1
                return True, max(1, wait_seconds)
            
        return False, 0
    
    def _is_globally_rate_limited(self) -> Tuple[bool, int]:
        """Check if there's a global rate limit in effect.
        
        Returns:
            Tuple of (is_limited, seconds_to_wait)
        """
        max_calls, period = self.global_limit
        
        # Clean old records
        self.global_usage = self._clean_old_records(self.global_usage, period)
        
        # Count recent global calls
        recent_calls = sum(record[1] for record in self.global_usage)
        
        if recent_calls >= max_calls:
            # Calculate wait time based on oldest record
            if self.global_usage:
                oldest_timestamp = self.global_usage[0][0]
                wait_seconds = int(period - (time.time() - oldest_timestamp)) + 1
                return True, max(1, wait_seconds)
            
        return False, 0
    
    async def check_rate_limit(self, command: str, user_id: int) -> Tuple[bool, int, str]:
        """Check if a command should be rate limited.
        
        Args:
            command: The command being executed
            user_id: User ID executing the command
            
        Returns:
            Tuple of (allowed, wait_time, reason)
                allowed: True if command is allowed, False if rate limited
                wait_time: Seconds to wait if rate limited
                reason: Reason for rate limiting if applicable
        """
        # Check user-specific limit
        user_limited, user_wait = self._is_user_rate_limited(command, user_id)
        if user_limited:
            return False, user_wait, "personal"
            
        # Check global limit
        global_limited, global_wait = self._is_globally_rate_limited()
        if global_limited:
            return False, global_wait, "global"
            
        # Record this usage
        current_time = time.time()
        self.user_usage[command][user_id].append((current_time, 1))
        self.global_usage.append((current_time, 1))
        
        return True, 0, ""
        
    async def acquire_with_feedback(self, update, context, command: str) -> bool:
        """Try to acquire rate limit permission and provide feedback to user if limited.
        
        Args:
            update: Telegram update object
            context: CallbackContext
            command: Command being executed
            
        Returns:
            True if allowed to proceed, False if rate limited
        """
        user_id = update.effective_user.id
        
        allowed, wait_time, reason = await self.check_rate_limit(command, user_id)
        
        if not allowed:
            # Determine the appropriate message based on the reason
            if reason == "personal":
                message = f"⏳ Please wait {wait_time} seconds before using this command again."
            else:
                message = f"⏳ Bot is experiencing high traffic. Please try again in {wait_time} seconds."
                
            # Send feedback to the user
            try:
                await update.message.reply_text(message)
            except Exception as e:
                logger.warning(f"Failed to send rate limit message: {e}")
                
            return False
            
        return True


# Global instance
limiter = RateLimiter()
