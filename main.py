#!/usr/bin/env python3
"""
Main entry point for Alya Bot v2.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from telegram.ext import Application, ApplicationBuilder
from config.settings import settings
from app.infrastructure.database import create_tables
from app.presentation.container import DIContainer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/alya_bot.log', mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class AlyaBot:
    """Main bot application class."""
    
    def __init__(self):
        self.application: Application = None
        self.container: DIContainer = None
    
    async def initialize(self):
        """Initialize the bot and its dependencies."""
        try:
            logger.info("🌸 Initializing Alya Bot v2...")
            
            # Create logs directory
            Path('logs').mkdir(exist_ok=True)
            
            # Initialize database
            logger.info("Setting up database...")
            create_tables()
            
            # Initialize dependency container
            logger.info("Initializing services...")
            self.container = DIContainer()
            
            # Build Telegram application
            logger.info("Building Telegram application...")
            self.application = ApplicationBuilder().token(settings.telegram_bot_token).build()
            
            # Register handlers
            handlers = self.container.get_telegram_handlers()
            for handler in handlers.get_handlers():
                self.application.add_handler(handler)
            
            logger.info("✅ Alya Bot v2 initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot: {e}")
            raise
    
    async def start(self):
        """Start the bot."""
        try:
            await self.initialize()
            
            logger.info("🚀 Starting Alya Bot v2...")
            logger.info(f"Bot name: {settings.bot_name}")
            logger.info(f"Command prefix: {settings.command_prefix}")
            logger.info(f"Environment: {settings.environment}")
            
            # Start polling
            await self.application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            raise
    
    async def stop(self):
        """Stop the bot gracefully."""
        if self.application:
            logger.info("🛑 Stopping Alya Bot v2...")
            await self.application.stop()
            logger.info("✅ Bot stopped successfully")


async def main():
    """Main function."""
    bot = AlyaBot()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    # Ensure we're using the right event loop policy
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
