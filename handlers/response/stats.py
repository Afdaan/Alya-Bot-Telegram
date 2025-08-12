import random
from typing import Dict, Literal, Any

def get_stats_response(lang: Literal['id', 'en'], db_manager: Any, **kwargs) -> str:
    """
    Fetches user stats and generates a formatted response in the specified language.

    Args:
        lang: The language for the response ('id' or 'en').
        db_manager: The database manager instance to fetch stats.
        **kwargs: Should contain user_id.

    Returns:
        HTML-formatted stats string.
    """
    user_id = kwargs.get("user_id")
    if not user_id or not db_manager:
        return "Error: Could not retrieve stats."

    # Get actual user data from database
    try:
        # Get user info from database
        user_info = db_manager.get_user(user_id)
        relationship_info = db_manager.get_user_relationship_info(user_id)
        
        # Extract user name - prefer first_name, fallback to username, then "User"
        user_name = "User"
        if user_info:
            user_name = user_info.get("first_name", "").strip()
            if not user_name:
                user_name = user_info.get("username", "").strip()
            if not user_name:
                user_name = "User"
        
        # Set default relationship data if not found
        if relationship_info and "relationship" in relationship_info:
            relationship = relationship_info["relationship"]
            affection = relationship_info.get("affection", {"points": 0, "progress_percent": 0})
            stats = relationship_info.get("stats", {"total_messages": 0, "positive_interactions": 0, "negative_interactions": 0, "role": "User"})
        else:
            # Default values for new users
            relationship = {"level": 0, "name": "Stranger", "progress_percent": 0, "next_level_at_interaction": 50, "next_level_at_affection": 100}
            affection = {"points": 0, "progress_percent": 0}
            stats = {"total_messages": 0, "positive_interactions": 0, "negative_interactions": 0, "role": "User"}
        
        user_data = {
            "name": user_name,
            "relationship": relationship,
            "affection": affection,
            "stats": stats
        }
        
    except Exception as e:
        # Fallback to mock data if database fails
        user_data = {
            "name": "User",
            "relationship": {"level": 1, "name": "Acquaintance", "progress_percent": 50.0, "next_level_at_interaction": 100, "next_level_at_affection": 200},
            "affection": {"points": 75, "progress_percent": 37.5},
            "stats": {"total_messages": 150, "positive_interactions": 20, "negative_interactions": 5, "role": "User"}
        }
    
    name = user_data["name"]
    relationship = user_data["relationship"]
    affection = user_data["affection"]
    stats = user_data["stats"]

    def progress_bar(percent: float, length: int = 15, filled_char: str = "█", empty_char: str = "░") -> str:
        """Create a visual progress bar."""
        blocks = int(percent * length / 100)
        return f"[{filled_char * blocks}{empty_char * (length - blocks)}]"
    
    def get_level_emoji(level: int) -> str:
        """Get emoji for relationship level."""
        emojis = {0: "👋", 1: "😊", 2: "🤝", 3: "💫", 4: "💖"}
        return emojis.get(level, "❓")

    if lang == 'id':
        level_footers = {
            0: ["Hmm? K-kenapa kamu ingin tahu? Alya belum mengenalmu! 😤", "Alya masih belum akrab sama kamu, jangan kepedean ya... 😳"],
            1: ["Alya mulai mengingatmu sedikit... 🤔", "Kita udah lumayan sering ngobrol, tapi jangan GR dulu ya! 😏"],
            2: ["Alya pikir kita sudah cukup berteman... ✨", "Kamu udah jadi temen deket Alya, tapi jangan aneh-aneh ya! 💫"],
            3: ["A-alya senang bisa mengobrol denganmu sejauh ini! 💕", "Kamu spesial banget buat Alya... tapi jangan bilang siapa-siapa! 😳"],
            4: ["Alya merasa kita sudah sangat dekat... 💖", "Kamu sudah jadi soulmate Alya, jangan sakiti hati Alya ya! 💞"]
        }
        level_names = {0: "Orang Asing", 1: "Kenalan", 2: "Teman", 3: "Teman Dekat", 4: "Belahan Jiwa"}
        title = f"<b>🌸 Statistik Hubungan {name} [{stats.get('role', 'User')}] 🌸</b>"
        level_text = "Level"
        affection_text = "Affection Points"
        requirements_text = "Butuh"
        interactions_text = "interaksi"
        affection_req_text = "affection"
        max_level_text = "Level maksimal tercapai! 🎉"
        interaction_stats_text = "📊 Interaksi:"
        total_messages_text = "📨 Total Pesan:"
        positive_interactions_text = "😊 Interaksi Positif:"
        negative_interactions_text = "😠 Interaksi Negatif:"
    else:
        level_footers = {
            0: ["Hmm? W-why do you want to know? Alya doesn't know you yet! 😤", "Alya is not familiar with you yet, don't get too full of yourself... 😳"],
            1: ["Alya is starting to remember you a little... 🤔", "We've talked quite a bit, but don't get the wrong idea! 😏"],
            2: ["Alya thinks we're pretty good friends... ✨", "You've become a close friend of Alya, but don't do anything weird! 💫"],
            3: ["A-alya is happy to have talked with you this much! 💕", "You're very special to Alya... but don't tell anyone! 😳"],
            4: ["Alya feels we've become very close... 💖", "You've become Alya's soulmate, don't break Alya's heart! 💞"]
        }
        level_names = {0: "Stranger", 1: "Acquaintance", 2: "Friend", 3: "Close Friend", 4: "Soulmate"}
        title = f"<b>🌸 Relationship Stats for {name} [{stats.get('role', 'User')}] 🌸</b>"
        level_text = "Level"
        affection_text = "Affection Points"
        requirements_text = "Requires"
        interactions_text = "interactions"
        affection_req_text = "affection"
        max_level_text = "Max level reached! 🎉"
        interaction_stats_text = "📊 Interactions:"
        total_messages_text = "📨 Total Messages:"
        positive_interactions_text = "😊 Positive Interactions:"
        negative_interactions_text = "😠 Negative Interactions:"

    level = relationship.get('level', 0)
    level_name = level_names.get(level, "Unknown")
    current_interactions = relationship.get('interactions', 0)
    progress_percent = relationship.get('progress_percent', 0.0)
    next_interaction_req = relationship.get('next_level_at_interaction', 100)
    next_affection_req = relationship.get('next_level_at_affection', 200)
    
    affection_points = affection.get('points', 0)
    affection_percent = affection.get('progress_percent', 0.0)
    
    # Extract interaction stats
    total_messages = stats.get('total_messages', 0)
    positive_interactions = stats.get('positive_interactions', 0)
    negative_interactions = stats.get('negative_interactions', 0)

    footer = random.choice(level_footers.get(level, ["..."]))
    level_emoji = get_level_emoji(level)
    
    if level < 4:
        requirements = f"{requirements_text}: {next_interaction_req} {interactions_text} & {next_affection_req} {affection_req_text}"
    else:
        requirements = max_level_text

    return (
        f"{title}\n\n"
        f"<b>{level_emoji} {level_text}:</b> {level} - {level_name}\n"
        f"{progress_bar(progress_percent)} <code>{progress_percent:.1f}%</code>\n"
        f"<i>{requirements}</i>\n\n"
        f"<b>💕 {affection_text}:</b> {affection_points}\n"
        f"{progress_bar(affection_percent)} <code>{affection_percent:.1f}%</code>\n\n"
        f"<b>{interaction_stats_text}</b>\n"
        f"├ {total_messages_text} {total_messages}\n"
        f"├ {positive_interactions_text} {positive_interactions}\n"
        f"└ {negative_interactions_text} {negative_interactions}\n\n"
        f"<i>{footer}</i>"
    )