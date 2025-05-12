import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from telegram import Update
from telegram.ext import Application
from config.settings import TELEGRAM_TOKEN
from core.bot import setup_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Main function to run the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("Telegram token not found. Please check your .env file")
        return
        
    # Create application instance
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Setup all handlers
    setup_handlers(application)
    
    # Start bot
    logger.info("Starting Alya Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()