"""
Command Parsing Utilities for Alya Telegram Bot.

This module provides pattern matching and parsing for special commands,
particularly focused on roast commands and @mentions.
"""

import re
import random
import os
import yaml
from typing import Dict, Optional, Tuple, Any, List
from pathlib import Path

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

# Prefix words that indicate this is a roasting command
ROAST_PREFIXES = ["roast", "roasting", "flame", "burn", "hina", "destroy"]

# =========================
# Roast Response Loading
# =========================

def load_roast_responses() -> Dict[str, List[str]]:
    """
    Load roast responses from YAML file.
    
    Returns:
        Dictionary containing roast responses by category
    """
    try:
        # Load from unified structure
        base_dir = Path(__file__).parent.parent
        roasts_path = base_dir / "config" / "roasts.yaml"
        
        # If file exists, use it
        if roasts_path.exists():
            with open(roasts_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Extract appropriate sections
            if data and isinstance(data, dict):
                # Process data in format
                result = {
                    "roast_intros": data.get("intros", []),
                    "general_criteria": data.get("criteria", {}).get("general", []),
                    "github_criteria": data.get("criteria", {}).get("github", []),
                    "roast_outros": data.get("outros", []),
                    "general_roasts": data.get("pre_made", {}).get("general", []),
                    "github_roasts": data.get("pre_made", {}).get("github", [])
                }
                return result
        
        # Emergency fallback if file not found
        logger.error(f"Roasts file not found at {roasts_path}")
        return {
            "roast_intros": ["*menatap*"],
            "general_criteria": ["ketidakmampuan"],
            "general_roasts": ["Hmm, {target}..."],
            "github_criteria": ["coding style"],
            "github_roasts": ["Repository {target}..."],
            "roast_outros": ["..."]
        }
            
    except Exception as e:
        logger.error(f"Error loading roast responses: {e}")
        # Return minimal fallback data
        return {
            "roast_intros": ["*menatap*"],
            "general_criteria": ["ketidakmampuan"],
            "general_roasts": ["Hmm, {target}..."],
            "github_criteria": ["coding style"],
            "github_roasts": ["Repository {target}..."],
            "roast_outros": ["..."]
        }

# Cache for roast responses
_ROAST_RESPONSES = None

def get_roast_responses() -> Dict[str, List[str]]:
    """
    Get roast responses with caching.
    
    Returns:
        Dictionary containing roast responses by category
    """
    global _ROAST_RESPONSES
    if (_ROAST_RESPONSES is None):
        _ROAST_RESPONSES = load_roast_responses()
    return _ROAST_RESPONSES

def get_random_brutal_roast(target: str, is_github: bool = False) -> str:
    """
    Generate super brutal Indonesian roast with vulgar language.
    
    Args:
        target: Name of the roast target
        is_github: Whether to use GitHub specific roasting criteria
        
    Returns:
        Brutal roast text in Indonesian with profanity
    """
    responses = get_roast_responses()
    
    # Get basic components
    intros = responses.get("roast_intros") or ["*menatap jijik*", "ANJIRR!", "NAJIS BANGET!"]
    outros = responses.get("roast_outros") or ["DASAR SAMPAH!", "FIX MENTAL ISSUE!"]
    
    # Get appropriate criteria based on type
    criteria_key = "github_criteria" if is_github else "general_criteria"
    criteria = responses.get(criteria_key) or ["kebodohan", "muka ancur", "bau badan"]
    
    # Get kata kasar (profanity)
    kata_kasar_mild = responses.get("kata_kasar", {}).get("mild") or ["tolol", "goblok", "bego"]
    kata_kasar_medium = responses.get("kata_kasar", {}).get("medium") or ["bangsat", "brengsek", "kampret"]
    kata_kasar_harsh = responses.get("kata_kasar", {}).get("harsh") or ["anjing", "kontol", "memek"]
    
    # Get templates and descriptors
    brutal_templates = responses.get("brutal_templates") or ["{target} {kata_kasar1}! MUKA LO {descriptor}!"]
    descriptors = responses.get("descriptors") or ["GORONG-GORONG BOCOR", "KAIN LAP BEKAS"]
    consequences = responses.get("consequences") or ["BAU NYA NYENGET KEMANA-MANA", "BIKIN ORANG MUNTAH"]
    penghubung = responses.get("penghubung_roast") or ["DASAR", "EMANG DASAR", "KAYAK"]
    
    # Build super brutal roast
    # Start with all caps intro
    intro = random.choice(intros).replace("{target}", target).upper()
    
    # Add multiple paragraphs of brutality (3-5 paragraphs)
    paragraphs = [intro]
    
    # How brutal should it be (1-10 scale)?
    brutality = random.randint(7, 10)
    
    # Number of paragraphs based on brutality
    num_paragraphs = min(5, max(3, brutality - 5))
    
    # Choose criteria based on type
    selected_criteria = random.sample(criteria, min(num_paragraphs, len(criteria)))
    
    # Generate brutal paragraphs
    for i in range(num_paragraphs):
        # For max brutality, include harsh language
        if brutality >= 8:
            kata_kasar1 = random.choice(kata_kasar_harsh if random.random() < 0.7 else kata_kasar_medium)
            kata_kasar2 = random.choice(kata_kasar_harsh if random.random() < 0.5 else kata_kasar_medium)
        else:
            kata_kasar1 = random.choice(kata_kasar_medium if random.random() < 0.7 else kata_kasar_mild)
            kata_kasar2 = random.choice(kata_kasar_medium if random.random() < 0.5 else kata_kasar_mild)
        
        # Create a harsh template
        template = random.choice(brutal_templates)
        descriptor = random.choice(descriptors)
        consequence = random.choice(consequences)
        penghubung_text = random.choice(penghubung)
        
        # Format the template with all the brutal pieces
        brutal_paragraph = template.format(
            target=target,
            kata_kasar1=kata_kasar1.upper(),
            kata_kasar2=kata_kasar2.upper(),
            descriptor=descriptor,
            consequence=consequence,
            penghubung=penghubung_text
        )
        
        # Add random emoji for effect
        emoji = random.choice(["🤮", "💀", "🤡", "💅", "🖕", "😤", "💩", "🔪"]) * random.randint(2, 3)
        
        # Format paragraph and add to list
        paragraphs.append(f"{brutal_paragraph} {emoji}")
    
    # Add brutal outro
    outro = random.choice(outros).upper()
    outro_emoji = random.choice(["🤮", "💀", "🤡", "💅", "🖕", "😤", "💩", "🔪"]) * 2
    paragraphs.append(f"{outro} {outro_emoji}")
    
    # Combine all parts into one mega-brutal roast
    full_roast = "\n\n".join(paragraphs)
    
    return full_roast

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
    if not message or not message.text:
        return (False, None, False, '', None)
        
    text = message.text.lower().strip()
    words = text.split()
    
    # Input validation - check for minimum content
    if not words:
        return (False, None, False, '', None)
    
    # STRICT PREFIX CHECK: Word must be at beginning of sentence
    if words[0] not in ROAST_PREFIXES:
        # Allow for 'roast github' special case
        if len(words) > 1 and words[0] == "roast" and words[1] == "github":
            pass  # Continue checking
        else:
            return (False, None, False, '', None)
    
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
    
    # Handle case with just prefix (self-roast)
    if words and words[0] in ROAST_PREFIXES:
        target = words[1] if len(words) > 1 else ""
        is_github = words[0] == "gitroast" or (len(words) > 2 and words[1] == "github")
        return (True, target, is_github, "", None)
    
    # Not a roast command
    return (False, None, False, '', None)
