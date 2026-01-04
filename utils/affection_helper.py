"""Helper methods for affection calculation."""

from config.settings import AFFECTION_POINTS

def calculate_affection_delta_from_context(message_context: dict) -> int:
    if not message_context:
        return AFFECTION_POINTS.get("conversation", 1)

    affection_delta = 0
    emotion = message_context.get("emotion", "")
    intent = message_context.get("intent", "")
    signals = message_context.get("relationship_signals", {})

    if emotion in ["happy", "excited", "grateful", "joy", "love", "admiration"]:
        affection_delta += AFFECTION_POINTS.get("positive_emotion", 2)
    elif emotion in ["sad", "worried", "disappointed"]:
        affection_delta += AFFECTION_POINTS.get("mild_positive_emotion", 1)
    elif emotion in ["angry", "frustrated", "annoyed"]:
        if message_context.get("directed_at_alya", True):
            affection_delta += AFFECTION_POINTS.get("anger", -3)
        else:
            affection_delta += AFFECTION_POINTS.get("mild_positive_emotion", 1)

    intent_map = {
        "gratitude": "gratitude", "apology": "apology", "affection": "affection",
        "greeting": "greeting", "compliment": "compliment", "question": "question",
        "meaningful_conversation": "meaningful_conversation",
        "asking_about_alya": "asking_about_alya",
        "remembering_details": "remembering_details",
        "insult": "insult", "abuse": "insult",
        "toxic": "toxic_behavior", "toxic_behavior": "toxic_behavior",
        "bullying": "toxic_behavior", "rudeness": "rudeness",
        "ignoring": "ignoring", "inappropriate": "inappropriate",
        "command": "command", "departure": "command"
    }
    
    if intent in intent_map:
        affection_delta += AFFECTION_POINTS.get(intent_map[intent], 0)

    signal_delta = (
        signals.get("friendliness", 0) * AFFECTION_POINTS.get("friendliness", 6) +
        signals.get("romantic_interest", 0) * AFFECTION_POINTS.get("romantic_interest", 10) +
        signals.get("conflict", 0) * AFFECTION_POINTS.get("conflict", -3)
    )
    affection_delta += signal_delta

    if affection_delta < 0:
        affection_delta = max(affection_delta, AFFECTION_POINTS.get("min_penalty", -4))
    
    return affection_delta if affection_delta != 0 else AFFECTION_POINTS.get("conversation", 1)
