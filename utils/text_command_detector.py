"""
Text Command Detector for Alya Telegram Bot.

This module provides utilities for detecting and routing text-based commands
that use specialized prefixes like !trace, !sauce, etc.
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

class TextCommandDetector:
    """
    Detects and extracts command and arguments from text messages.
    """
    
    def __init__(self):
        """Initialize the command detector with predefined patterns."""
        # Command patterns for common prefixes
        self.command_patterns = [
            # Search commands
            (r"^!search\s+(.+)$", "search"),
            # Source finder
            (r"^!sauce\s*(.*)$", "sauce"),
            # Trace/analyze
            (r"^!trace\s*(.*)$", "trace"),
            (r"^!ocr\s*(.*)$", "ocr"),
            # Other common commands
            (r"^!ai\s+(.+)$", "ai"),
            (r"^!alya\s+(.+)$", "ai"),
            (r"^!roast\s+(.+)$", "roast"),
        ]
    
    def detect_command(self, text: str) -> Tuple[Optional[str], str]:
        """
        Detect if text contains a recognized command pattern.
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (command_type, arguments)
        """
        if not text:
            return None, ""
            
        # Check against patterns
        for pattern, command_type in self.command_patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                # Extract arguments
                arguments = match.group(1) if match.groups() else ""
                return command_type, arguments
                
        # No match found
        return None, ""
    
    def parse_arguments(self, args_text: str) -> List[str]:
        """
        Parse arguments string into list, respecting quoted arguments.
        
        Args:
            args_text: String containing arguments
            
        Returns:
            List of argument strings
        """
        # Quick exit for empty text
        if not args_text:
            return []
            
        # Regex pattern for matching arguments with quotes
        pattern = r'([^\s"]+)|"([^"]*)"'
        
        args = []
        matches = re.finditer(pattern, args_text)
        
        for match in matches:
            # If the first group matched, it's an unquoted arg
            # If the second group matched, it's a quoted arg
            arg = match.group(1) or match.group(2)
            args.append(arg)
            
        return args

# Create singleton instance
text_command_detector = TextCommandDetector()
