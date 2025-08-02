def ping_response(latency_ms: float = None, language: str = None) -> str:
    """Generate a ping response for the bot."""
    
    if latency_ms is not None:
        if language == "en":
            return f"🏓 Pong! Latency: {latency_ms:.2f}ms\nAlya is ready for you~ 💫"
        else:  # Indonesian
            return f"🏓 Pong! Latency: {latency_ms:.2f}ms\nAlya siap sedia buat kamu kok~ 💫"
    
    # Base response without latency
    if language == "en":
        return "🏓 Pong! Alya is on fire right now~ 💫"
    else:  # Indonesian  
        return "🏓 Pong! Alya lagi on fire nih~ 💫"