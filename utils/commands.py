"""
Command Understanding for Alya Telegram Bot.

This module uses natural language understanding to identify command intents
without relying on rigid regex patterns.
"""

import logging
import random
import re
from typing import Dict, Optional, Tuple, Any, List, Set

logger = logging.getLogger(__name__)

class CommandDetector:
    """Natural command detection without regex patterns."""
    
    def __init__(self):
        """Initialize command detector."""
        self.command_indicators = {
            'roast': [
                'roast', 'hina', 'toxic', 'bully', 'buli', 'flame', 'ejek',
                '/roast', '/hina', '/bully', '/buli', '/flame', '/toxic'
            ],
            'search': [
                'search', 'cari', 'find', 'lookup', '/search', '/cari', 
                'tolong cari', 'please search', 'find me'
            ],
            'mode': [
                'mode', 'persona', 'character', 'personality', 'switch',
                '/mode', '/persona', 'ganti mode', 'change mode'
            ],
            'help': [
                'help', 'bantuan', 'tolong', 'commands', '/help', '/bantuan',
                '/commands', 'cara pakai', 'how to use'
            ]
        }
    
    def detect_command_type(self, message: str) -> Optional[str]:
        """
        Detect command type using natural language understanding.
        
        Args:
            message: User message to analyze
            
        Returns:
            Command type or None if not a command
        """
        # Clean and normalize message
        if not message:
            return None
            
        clean_message = message.lower().strip()
        
        # Skip empty messages
        if not clean_message:
            return None
            
        # First check for explicit AI command prefix
        if clean_message.startswith("!ai "):
            clean_message = clean_message[4:].strip()
            
        # Get first word for simple command detection
        words = clean_message.split()
        if not words:
            return None
            
        first_word = words[0]
        
        # Check all command types
        for cmd_type, indicators in self.command_indicators.items():
            # Check for direct match with first word
            if first_word in indicators:
                return cmd_type
                
            # Check for phrase match
            if len(words) >= 3:
                three_word_phrase = " ".join(words[:3])
                for indicator in indicators:
                    if " " in indicator and indicator in three_word_phrase:
                        return cmd_type
        
        return None
    
    def extract_command_args(self, message: str, command_type: str) -> List[str]:
        """
        Extract command arguments based on detected command type.
        
        Args:
            message: Original message text
            command_type: Detected command type
            
        Returns:
            List of command arguments
        """
        if not message or not command_type:
            return []
            
        clean_message = message.lower().strip()
        
        # Skip AI prefix if present
        if clean_message.startswith("!ai "):
            clean_message = clean_message[4:].strip()
            
        # Find command word
        for indicator in self.command_indicators.get(command_type, []):
            if " " in indicator:
                # Multi-word command
                if clean_message.startswith(indicator):
                    return clean_message[len(indicator):].strip().split()
            else:
                # Single word command
                words = clean_message.split()
                if words and words[0] == indicator:
                    return words[1:] if len(words) > 1 else []
        
        return []
    
    def extract_roast_target(self, message: str) -> Optional[str]:
        """
        Extract roast target through natural language understanding.
        
        Args:
            message: Message text
            
        Returns:
            Target username or None
        """
        args = self.extract_command_args(message, "roast")
        if not args:
            return None
            
        # First argument is the target
        target = args[0]
        
        # Remove @ prefix if present
        if target.startswith("@"):
            target = target[1:]
            
        # Remove "si" prefix if present
        if target == "si" and len(args) > 1:
            target = args[1]
            
        # Basic validation
        if len(target) >= 2 and target.isalnum():
            return target
            
        return None
    
    def extract_search_query(self, message: str) -> Optional[str]:
        """
        Extract search query from message.
        
        Args:
            message: Message text
            
        Returns:
            Search query or None
        """
        args = self.extract_command_args(message, "search")
        if not args:
            return None
            
        # Join all args for the search query
        return " ".join(args)
    
    def extract_mode_name(self, message: str) -> Optional[str]:
        """
        Extract mode name from mode switch command.
        
        Args:
            message: Message text
            
        Returns:
            Mode name or None
        """
        args = self.extract_command_args(message, "mode")
        if not args:
            return None
            
        # First arg is the mode name
        mode_name = args[0].lower()
        
        # Validate mode
        valid_modes = {"waifu", "tsundere", "smart", "toxic", "professional"}
        if mode_name in valid_modes:
            return mode_name
            
        return None

# Create a singleton instance for global use
command_detector = CommandDetector()

def parse_command_args(text: str) -> Tuple[str, List[str]]:
    """
    Parse command and arguments from a text message.
    
    Args:
        text: The message text
        
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
    Generate a random roast message for the target.
    
    Args:
        target: Person to roast
        is_github: Whether to use GitHub-specific roasts
        
    Returns:
        Roast message with target name inserted
    """
    # Sanitize target name
    if not target or len(target) > 50:
        target = "user"
        
    # Collection of brutal roasts
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
    
    # Choose appropriate roast collection
    roast_collection = github_roasts if is_github else regular_roasts
    
    # Select random roast and format with target name
    roast_template = random.choice(roast_collection)
    return roast_template.format(target=target)
