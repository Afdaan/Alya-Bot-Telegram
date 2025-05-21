"""
Command Understanding for Alya Telegram Bot.

This module provides simplified prefix detection and command parsing
utilities focused on reliability rather than complex NLU.
"""

import logging
import random
import re
from typing import Dict, Optional, Tuple, Any, List, Set

from config.settings import (
    CHAT_PREFIX, 
    ADDITIONAL_PREFIXES, 
    GROUP_CHAT_REQUIRES_PREFIX,
    ANALYZE_PREFIX,
    SAUCE_PREFIX,
    ROAST_PREFIX
)

logger = logging.getLogger(__name__)

class CommandDetector:
    """Simplified command detector focusing on prefix detection."""
    
    def __init__(self):
        """Initialize command detector."""
        # All command prefixes from settings
        self.all_prefixes = [
            CHAT_PREFIX, ANALYZE_PREFIX, SAUCE_PREFIX, ROAST_PREFIX
        ] + ADDITIONAL_PREFIXES
        
        # Recognized prefixes without duplicates
        self.recognized_prefixes = list(set(self.all_prefixes))
        
        # Lowercase all prefixes for case-insensitive matching
        self.recognized_prefixes = [prefix.lower() for prefix in self.recognized_prefixes]
    
    def detect_prefix(self, message: str) -> Optional[str]:
        """
        Detect if the message starts with a recognized prefix.
        
        Args:
            message: User message to analyze
            
        Returns:
            The detected prefix or None if no prefix found
        """
        if not message:
            return None
            
        clean_message = message.lower().strip()
        
        # Skip empty messages
        if not clean_message:
            return None
        
        # Check for exact prefix matches
        for prefix in self.recognized_prefixes:
            if clean_message.startswith(f"{prefix} ") or clean_message == prefix:
                return prefix
                
        return None
    
    def extract_message_after_prefix(self, message: str, prefix: str) -> str:
        """
        Extract the actual message content after removing the prefix.
        
        Args:
            message: Original message text
            prefix: Detected prefix
            
        Returns:
            Message without prefix
        """
        if not message or not prefix:
            return ""
            
        clean_message = message.strip()
        
        # Remove prefix if present (case-insensitive)
        if clean_message.lower().startswith(f"{prefix.lower()} "):
            return clean_message[len(prefix)+1:].strip()
            
        if clean_message.lower() == prefix.lower():
            return ""
                
        return clean_message
    
    def should_respond_in_group(self, message: str) -> bool:
        """
        Determine if the bot should respond in a group chat.
        
        Args:
            message: Message text
            
        Returns:
            True if the bot should respond
        """
        if not GROUP_CHAT_REQUIRES_PREFIX:
            return True
            
        if not message:
            return False
            
        # Check if message starts with any recognized prefix
        return self.detect_prefix(message) is not None

# Create singleton instance
command_detector = CommandDetector()

def parse_command_args(text: str) -> Tuple[str, List[str]]:
    """
    Parse command and arguments from a text message.
    
    Args:
        text: Message text
        
    Returns:
        Tuple of (command, args)
    """
    if not text or not text.startswith('/'):
        return ('', [])
    
    parts = text.split()
    command = parts[0].lower().lstrip('/')
    args = parts[1:]
    
    return (command, args)

def is_media_command(message: str) -> bool:
    """
    Check if message is a media command.
    
    Args:
        message: Message text
        
    Returns:
        True if it's a media command
    """
    if not message:
        return False
        
    message_lower = message.lower().strip()
    
    return (message_lower.startswith(f"{ANALYZE_PREFIX} ") or 
            message_lower == ANALYZE_PREFIX or
            message_lower.startswith(f"{SAUCE_PREFIX} ") or
            message_lower == SAUCE_PREFIX)
