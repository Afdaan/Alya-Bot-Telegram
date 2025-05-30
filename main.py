"""
Main entry point for Alya Bot.
"""
import logging
from core.bot import run_bot, configure_logging

if __name__ == "__main__":

    configure_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Alya Bot starting...")
    
    run_bot()
