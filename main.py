import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging filters
class HTTPFilter(logging.Filter):
    def filter(self, record):
        # Filter out successful HTTP request logs
        return not (
            'HTTP Request:' in record.getMessage() and 
            'HTTP/1.1 200' in record.getMessage()
        )

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Add filter to root logger
logging.getLogger().addFilter(HTTPFilter())
# Set httpx logger to WARNING level
logging.getLogger("httpx").setLevel(logging.WARNING)
# Set urllib3 logger to WARNING level
logging.getLogger("urllib3").setLevel(logging.WARNING)

from telegram import Update
from telegram.ext import Application
from config.settings import TELEGRAM_TOKEN
from core.bot import setup_handlers

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