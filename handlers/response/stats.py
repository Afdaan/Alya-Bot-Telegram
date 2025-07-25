import random
from typing import Dict

def stats_response(
    name: str,
    relationship: dict,
    affection: dict,
    stats: dict
) -> str:
    """Generate a formatted stats response for the user.

    Args:
        name: User's display name
        relationship: Relationship info dict
        affection: Affection info dict
        stats: Stats info dict

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

    # Footer messages per relationship level (randomized)
    level_footers = {
        0: [
            "Hmm? K-kenapa kamu ingin tahu? Alya belum mengenalmu! 😤",
            "Alya masih belum akrab sama kamu, jangan kepedean ya... 😳"
        ],
        1: [
            "Alya mulai mengingatmu sedikit... 🤔",
            "Kita udah lumayan sering ngobrol, tapi jangan GR dulu ya! 😏"
        ],
        2: [
            "Alya pikir kita sudah cukup berteman... ✨",
            "Kamu udah jadi temen deket Alya, tapi jangan aneh-aneh ya! 💫"
        ],
        3: [
            "A-alya senang bisa mengobrol denganmu sejauh ini! 💕",
            "Kamu spesial banget buat Alya... tapi jangan bilang siapa-siapa! 😳"
        ],
        4: [
            "Alya merasa kita sudah sangat dekat... 💖",
            "Kamu sudah jadi soulmate Alya, jangan sakiti hati Alya ya! 💞"
        ]
    }

    # Extract relationship data
    level = relationship.get('level', 0)
    level_name = relationship.get('name', 'Stranger')
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

    # Get appropriate footer
    footer = random.choice(level_footers.get(level, ["Alya belum mengenalmu! 😤"]))
    
    # Build the response with better formatting
    level_emoji = get_level_emoji(level)
    
    # Progress requirements text
    if level < 4:  # Not max level
        requirements = f"Butuh: {next_interaction_req} interaksi & {next_affection_req} affection"
    else:
        requirements = "Level maksimal tercapai! 🎉"

    return (
        f"<b>🌸 Statistik Hubungan {name} [{role}] 🌸</b>\n\n"
        
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