import re

# Simplified command patterns with keyword capture
GITHUB_ROAST_PATTERN = r'(?:!ai\s+)?roast\s+github\s+(\w+)(?:\s+(.+))?'  # Capture: username, keywords
PERSONAL_ROAST_PATTERN = r'(?:!ai\s+)?roast\s+(\w+)(?:\s+(.+))?'         # Capture: username, keywords

def is_roast_command(text: str) -> tuple:
    """Check if message is a roast command and get target.
    
    Returns:
        tuple: (is_roast, target, is_github, keywords)
    """
    text = text.lower().strip()
    
    # Check GitHub roast first
    github_match = re.search(GITHUB_ROAST_PATTERN, text)
    if github_match:
        return (True, github_match.group(1), True, github_match.group(2) or '')
    
    # Check personal roast
    personal_match = re.search(PERSONAL_ROAST_PATTERN, text)
    if personal_match:
        return (True, personal_match.group(1), False, personal_match.group(2) or '')
    
    return (False, None, False, '')
