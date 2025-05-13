import re

# Update patterns to handle @ mentions and natural roast prompts
GITHUB_ROAST_PATTERN = r'(?:!ai\s+)?roast\s+github\s+(?:@)?(\w+)(?:\s+(.+))?'  # Support @username
PERSONAL_ROAST_PATTERN = r'(?:!ai\s+)?roast\s+(?:@)?(\w+)(?:\s+(.+))?'         # Support @username

# New: Natural roast prompt patterns
NATURAL_ROAST_PATTERNS = [
    r'(?:!ai\s+)?roasting\s+si\s+@?(\w+)(?:\s+(.+))?',      # roasting si username [keywords]
    r'(?:!ai\s+)?roasting\s+@?(\w+)(?:\s+(.+))?',           # roasting username [keywords]
    r'(?:!ai\s+)?roast\s+@?(\w+)(?:\s+(.+))?',              # roast username [keywords]
    r'(?:!ai\s+)?roast(?:ing)?\s+@?(\w+)(?:\s+(.+))?',      # roasting username [keywords]
    r'(?:!ai\s+)?roast(?:ing)?\s+si\s+@?(\w+)(?:\s+(.+))?', # roasting si username [keywords]
    r'(?:!ai\s+)?roast(?:ing)?\s+(.+)',                     # roast/roasting <free text>
    r'(?:!ai\s+)?roast(?:ing)?\b',                          # roast/roasting (catch-all)
]

def get_user_info_from_mention(message, username: str) -> dict:
    """Get user information from message mention."""
    if not message.entities:
        return None
        
    for entity in message.entities:
        if entity.type == 'mention':  # @username mention
            # Get actual user info from mention
            mention_text = message.text[entity.offset:entity.offset + entity.length]
            if mention_text.lower() == f"@{username.lower()}":
                # Try to get full user info
                return {
                    'username': username,
                    'mention': mention_text,
                    'is_mention': True
                }
    return None

def is_roast_command(message) -> tuple:
    """Enhanced roast command checker with mention & natural prompt support.
    
    Returns:
        tuple: (is_roast, target, is_github, keywords, user_info)
    """
    text = message.text.lower().strip()
    
    # Check GitHub roast first
    github_match = re.search(GITHUB_ROAST_PATTERN, text)
    if github_match:
        username = github_match.group(1)
        keywords = github_match.group(2) or ''
        user_info = get_user_info_from_mention(message, username)
        return (True, username, True, keywords, user_info)
    
    # Check personal roast (explicit)
    personal_match = re.search(PERSONAL_ROAST_PATTERN, text)
    if personal_match:
        username = personal_match.group(1)
        keywords = personal_match.group(2) or ''
        user_info = get_user_info_from_mention(message, username)
        return (True, username, False, keywords, user_info)
    
    # Check natural roast patterns
    for pattern in NATURAL_ROAST_PATTERNS:
        match = re.search(pattern, text)
        if match:
            username = match.group(1) if match.lastindex and match.lastindex >= 1 else None
            keywords = match.group(2) if match.lastindex and match.lastindex >= 2 else ''
            user_info = get_user_info_from_mention(message, username) if username else None
            # If username is not found, treat as generic roast
            return (True, username or '', False, keywords, user_info)
    
    return (False, None, False, '', None)
