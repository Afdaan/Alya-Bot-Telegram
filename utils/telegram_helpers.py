import asyncio
import logging
from typing import Optional, Union, Any
from telegram import Bot
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

logger = logging.getLogger(__name__)

class ChatActionSender:
    """
    Helper class to send periodic chat actions while a background task is running.
    Improved for project standards: flexible input (context or bot) and explicit interval.
    """
    
    def __init__(
        self, 
        context_or_bot: Union[ContextTypes.DEFAULT_TYPE, Bot], 
        chat_id: int, 
        action: ChatAction, 
        message_thread_id: Optional[int] = None,
        interval: float = 4.0
    ):
        if hasattr(context_or_bot, 'bot'):
            self.bot = context_or_bot.bot
        else:
            self.bot = context_or_bot
            
        self.chat_id = chat_id
        self.action = action
        self.message_thread_id = message_thread_id
        self.interval = interval
        self.stop_event = asyncio.Event()
        self._task = None

    async def _send_loop(self):
        try:
            while not self.stop_event.is_set():
                await self.bot.send_chat_action(
                    chat_id=self.chat_id, 
                    action=self.action, 
                    message_thread_id=self.message_thread_id
                )
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=self.interval)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Error in ChatActionSender loop: {e}")

    async def __aenter__(self):
        self._task = asyncio.create_task(self._send_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        if self._task:
            try:
                # Cancel the task to stop it immediately
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"ChatActionSender task cleanup error: {e}")
