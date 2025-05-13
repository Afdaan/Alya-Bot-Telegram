"""
Command Parsing Utilities for Alya Telegram Bot.

This module provides pattern matching and parsing for special commands,
particularly focused on roast commands and @mentions.
"""

import re
from typing import Dict, Optional, Tuple, Any

# =========================
# Command Patterns
# =========================

# Main roast command patterns with username/mention support
GITHUB_ROAST_PATTERN = r'(?:!ai\s+)?roast\s+github\s+(?:@)?(\w+)(?:\s+(.+))?'  # Support @username
PERSONAL_ROAST_PATTERN = r'(?:!ai\s+)?roast\s+(?:@)?(\w+)(?:\s+(.+))?'         # Support @username

# Natural language variations of roast commands
NATURAL_ROAST_PATTERNS = [
    r'(?:!ai\s+)?roasting\s+si\s+@?(\w+)(?:\s+(.+))?',      # roasting si username [keywords]
    r'(?:!ai\s+)?roasting\s+@?(\w+)(?:\s+(.+))?',           # roasting username [keywords]
    r'(?:!ai\s+)?roast\s+@?(\w+)(?:\s+(.+))?',              # roast username [keywords]
    r'(?:!ai\s+)?roast(?:ing)?\s+@?(\w+)(?:\s+(.+))?',      # roasting username [keywords]
    r'(?:!ai\s+)?roast(?:ing)?\s+si\s+@?(\w+)(?:\s+(.+))?', # roasting si username [keywords]
    r'(?:!ai\s+)?roast(?:ing)?\s+(.+)',                     # roast/roasting <free text>
    r'(?:!ai\s+)?roast(?:ing)?\b',                          # roast/roasting (catch-all)
]

# =========================
# Mention Detection
# =========================

def get_user_info_from_mention(message, username: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from message mentions.
    
    Args:
        message: Telegram message object
        username: Username to look for in mentions
        
    Returns:
        Dictionary with user info or None if not found
    """
    # No entities to check
    if not message.entities:
        return None
        
    # Look for mention entities
    for entity in message.entities:
        if entity.type == 'mention':  # @username mention
            mention_text = message.text[entity.offset:entity.offset + entity.length]
            
            # Check if the mention matches the target username
            if mention_text.lower() == f"@{username.lower()}":
                return {
                    'username': username,
                    'mention': mention_text,
                    'is_mention': True
                }
                
    # No matching mention found
    return None

# =========================
# Command Detection
# =========================

def is_roast_command(message) -> Tuple[bool, Optional[str], bool, str, Optional[Dict]]:
    """
    Enhanced roast command detection with mention & natural language support.
    
    Args:
        message: Telegram message object
        
    Returns:
        Tuple containing:
        - is_roast: Whether this is a roast command
        - target: Username of roast target
        - is_github: Whether this is a GitHub roast
        - keywords: Additional roast keywords
        - user_info: Dictionary with user information if available
    """
    text = message.text.lower().strip()
    
    # First check for GitHub roast (highest specificity)
    github_match = re.search(GITHUB_ROAST_PATTERN, text)
    if github_match:
        username = github_match.group(1)
        keywords = github_match.group(2) or ''
        user_info = get_user_info_from_mention(message, username)
        return (True, username, True, keywords, user_info)
    
    # Then check for personal roast (explicit format)
    personal_match = re.search(PERSONAL_ROAST_PATTERN, text)
    if personal_match:
        username = personal_match.group(1)
        keywords = personal_match.group(2) or ''
        user_info = get_user_info_from_mention(message, username)
        return (True, username, False, keywords, user_info)
    
    # Finally check for natural language roast patterns
    for pattern in NATURAL_ROAST_PATTERNS:
        match = re.search(pattern, text)
        if match:
            # Extract username if available
            username = match.group(1) if match.lastindex and match.lastindex >= 1 else None
            # Extract keywords if available
            keywords = match.group(2) if match.lastindex and match.lastindex >= 2 else ''
            # Get user info if username is found
            user_info = get_user_info_from_mention(message, username) if username else None
            return (True, username or '', False, keywords, user_info)
    
    # Not a roast command
    return (False, None, False, '', None)
