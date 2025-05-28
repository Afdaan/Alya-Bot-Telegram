def ping_response(latency_ms: float = None) -> str:
    """Generate a ping response for the bot."""
    if latency_ms is not None:
        return f"🏓 Pong! Latency: {latency_ms:.2f}ms\nAlya siap sedia buat kamu kok~ 💫"
    return "🏓 Pong! Alya lagi on fire nih~ 💫"
