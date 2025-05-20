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
        
    def is_roast_command(self, message: str) -> bool:
        """
        Check if the message is a roast command.
        
        Args:
            message: Message text
            
        Returns:
            True if it's a roast command
        """
        if not message:
            return False
            
        # First check if it has a chat prefix with "roast"
        message_lower = message.lower().strip()
        
        if message_lower.startswith(f"{CHAT_PREFIX} roast ") or message_lower.startswith("!alya roast "):
            return True
            
        # Then check for direct roast prefix
        if message_lower.startswith(f"{ROAST_PREFIX} ") or message_lower == ROAST_PREFIX:
            return True
            
        return False

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

def get_random_roast(target: str, is_github: bool = False) -> str:
    """
    Generate a random roast for the target.
    
    Args:
        target: Person to roast
        is_github: Whether to use GitHub roasts
        
    Returns:
        Roast message with target name
    """
    # Sanitize target name
    if not target or len(target) > 50:
        target = "user"
        
    # Collection of roasts
    github_roasts = [
        "*melihat repository {target}* ANJING CODE APA INI? Mending lu hapus GitHub account sebelum bikin malu komunitas programmer!",
        "PR dari {target}? *tertawa sinis* Merge conflict parah banget, SAMA KAYAK OTAK LO YANG KONFLIK SAMA LOGIKA! 💩",
        "Eh {target}, errornya BUKAN di code, tapi di PROGRAMMER-nya! Mending uninstall VSCode lu dah!",
        "BAJINGAN! {target} masih push ke master branch?! Fix lu amateur yang gak pernah baca Git workflow! 🤬",
        "Variable naming convention lu KACAU {target}! Sama kacaunya kayak hidup lu yang gak ada struktur! 😤",
        "Pull request dari {target} auto-reject! Gak hanya karena code-nya sampah, tapi karena otak lu juga sampah! 🚮"
    ]
    
    regular_roasts = [
        "*menatap {target} dengan jijik* Najis! {target} kok bisa hidup tapi selalu salah langkah gini sih? Gak ada yang bener dari lu!",
        "ANJIR {target} lagi? Kalo otak lu dijual mungkin harganya murah banget, SOALNYA GAK PERNAH DIPAKE! 🤢",
        "HAH? {target}? *tertawa histeris* Muka kayak gitu kok berani nongol di public ya! Bikin mata sakit aja! 😤",
        "Eh {target}, tolong dong berhenti jadi beban tim. Skillnya nol, otak kosong, nyusahin semua orang! 💩",
        "Goblok lu {target}! Error lu tuh gak bisa di-debug soalnya sumbernya dari existensi lu!",
        "ANJIRRR MINIMAL useless, MAKSIMAL jadi beban seperti biasa kan {target}? 🙄",
        "NAJIS BGT SIH {target}! Kalo ada kontes bikin masalah, lu pasti juara beruntun 10 tahun!",
        "Ya ampun {target}... *memutar mata* Code lu kacau, hidup lu kacau, semua tentang lu bikin muak! 🤮"
    ]
    
    # Select appropriate roast collection
    roast_collection = github_roasts if is_github else regular_roasts
    
    # Select random roast and format
    roast_template = random.choice(roast_collection)
    return roast_template.format(target=target)

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

def extract_roast_target(message: str) -> Optional[str]:
    """
    Extract target username from roast command.
    
    Args:
        message: Message text
        
    Returns:
        Target username or None
    """
    if not message:
        return None
        
    # Check if it's a roast command
    message_lower = message.lower().strip()
    
    for prefix in [f"{ROAST_PREFIX} ", "!ai roast ", "!alya roast "]:
        if message_lower.startswith(prefix):
            args = message_lower[len(prefix):].strip().split()
            if args:
                target = args[0]
                # Remove @ if present
                if target.startswith("@"):
                    target = target[1:]
                return target
    
    return None
