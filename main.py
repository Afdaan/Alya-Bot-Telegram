"""
Main entry point for Alya Bot.
"""
from core.bot import configure_logging, run_bot

if __name__ == "__main__":
    configure_logging()
    run_bot()
