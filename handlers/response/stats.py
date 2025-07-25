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
    def progress_bar(percent: float, length: int = 10) -> str:
        blocks = int(percent // (100 / length))
        return "[" + "█" * blocks + "░" * (length - blocks) + "]"

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
    level = relationship.get('level', 0)
    footer = random.choice(level_footers.get(level, ["Alya belum mengenalmu! 😤"]))

    # Always show stats, even if 0
    total_messages = stats.get('total_messages', 0)
    positive_interactions = stats.get('positive_interactions', 0)
    negative_interactions = stats.get('negative_interactions', 0)

    # Fetch user role from stats, fallback to "User" if not present
    role = stats.get('role', 'User')

    return (
        f"<b>🌸 Statistik Hubungan {name} [{role}] 🌸</b>\n\n"
        f"<b>Level:</b> {relationship['level']} - {relationship['name']} 💫\n"
        f"{progress_bar(relationship['progress_percent'])} {relationship['progress_percent']:.1f}%\n"
        f"<b>Interaksi:</b> {relationship['interactions']}/{relationship['next_level_at']} ✨\n\n"
        f"<b>Affection Points:</b> {affection['points']} ❤️\n"
        f"{progress_bar(affection['progress_percent'])}\n\n"
        f"<b>📨 Total Pesan:</b> {total_messages}\n"
        f"<b>😊 Interaksi Positif:</b> {positive_interactions}\n"
        f"<b>😠 Interaksi Negatif:</b> {negative_interactions}\n\n"
        f"{footer}"
    )