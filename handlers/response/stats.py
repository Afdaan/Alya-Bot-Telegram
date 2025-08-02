import random
from typing import Dict
from core.language_manager import language_manager

def stats_response(
    name: str,
    relationship: dict,
    affection: dict,
    stats: dict,
    language: str = None
) -> str:
    """Generate a formatted stats response for the user.

    Args:
        name: User's display name
        relationship: Relationship info dict
        affection: Affection info dict
        stats: Stats info dict
        language: User's preferred language

    Returns:
        HTML-formatted stats string
    """
    def progress_bar(percent: float, length: int = 15, filled_char: str = "█", empty_char: str = "░") -> str:
        """Create a visual progress bar."""
        blocks = int(percent * length / 100)
        return f"[{filled_char * blocks}{empty_char * (length - blocks)}]"
    
    def get_level_emoji(level: int) -> str:
        """Get emoji for relationship level."""
        emojis = {
            0: "👋",  # Stranger
            1: "😊",  # Acquaintance  
            2: "🤝",  # Friend
            3: "💫",  # Close Friend
            4: "💖"   # Soulmate
        }
        return emojis.get(level, "❓")

    # Extract relationship data
    level = relationship.get('level', 0)
    current_interactions = relationship.get('interactions', 0)
    next_interaction_req = relationship.get('next_level_at_interaction', 100)
    next_affection_req = relationship.get('next_level_at_affection', 200)
    progress_percent = relationship.get('progress_percent', 0.0)
    
    # Extract affection data
    affection_points = affection.get('points', 0)
    affection_percent = affection.get('progress_percent', 0.0)
    
    # Extract stats
    total_messages = stats.get('total_messages', 0)
    positive_interactions = stats.get('positive_interactions', 0)
    negative_interactions = stats.get('negative_interactions', 0)
    role = stats.get('role', 'User')

    # Get localized level name and reaction
    level_name = language_manager.get_relationship_level_name(level, language)
    footer = language_manager.get_relationship_reaction(level, language)
    
    # Build the response with better formatting
    level_emoji = get_level_emoji(level)
    
    # Progress requirements text
    if level < 4:  # Not max level
        if language == "en":
            requirements = f"Needed: {next_interaction_req} interactions & {next_affection_req} affection"
        else:
            requirements = f"Butuh: {next_interaction_req} interaksi & {next_affection_req} affection"
    else:
        if language == "en":
            requirements = "Maximum level reached! 🎉"
        else:
            requirements = "Level maksimal tercapai! 🎉"

    # Build response based on language
    stats_title = language_manager.get_text("commands.stats_title", language, name=name, role=role)
    
    if language == "en":
        return (
            f"<b>{stats_title}</b>\n\n"
            
            f"<b>{level_emoji} Level:</b> {level} - {level_name}\n"
            f"{progress_bar(progress_percent)} <code>{progress_percent:.1f}%</code>\n"
            f"<i>{requirements}</i>\n\n"
            
            f"<b>💕 Affection Points:</b> {affection_points}\n"
            f"{progress_bar(affection_percent)} <code>{affection_percent:.1f}%</code>\n\n"
            
            f"<b>📊 Interactions:</b>\n"
            f"├ 📨 <b>Total Messages:</b> {total_messages}\n"
            f"├ 😊 <b>Positive Interactions:</b> {positive_interactions}\n"
            f"└ 😠 <b>Negative Interactions:</b> {negative_interactions}\n\n"
            
            f"<i>{footer}</i>"
        )
    else:
        return (
            f"<b>{stats_title}</b>\n\n"
            
            f"<b>{level_emoji} Level:</b> {level} - {level_name}\n"
            f"{progress_bar(progress_percent)} <code>{progress_percent:.1f}%</code>\n"
            f"<i>{requirements}</i>\n\n"
            
            f"<b>💕 Affection Points:</b> {affection_points}\n"
            f"{progress_bar(affection_percent)} <code>{affection_percent:.1f}%</code>\n\n"
            
            f"<b>📊 Interaksi:</b>\n"
            f"├ 📨 <b>Total Pesan:</b> {total_messages}\n"
            f"├ 😊 <b>Interaksi Positif:</b> {positive_interactions}\n"
            f"└ 😠 <b>Interaksi Negatif:</b> {negative_interactions}\n\n"
            
            f"<i>{footer}</i>"
        )