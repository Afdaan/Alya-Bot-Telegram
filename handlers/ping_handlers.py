"""
Ping and Status Handlers for Alya Telegram Bot.

This module provides system status checking functionalities
for monitoring bot health and performance.
"""

import logging
import platform
import time
import psutil
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from utils.formatters import format_markdown_response
from utils.language_handler import get_response

logger = logging.getLogger(__name__)

# Track bot start time for uptime calculation
BOT_START_TIME = time.time()

async def ping_command(update: Update, context: CallbackContext) -> None:
    """
    Handle /ping command for checking system status.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    try:
        # Calculate uptime
        uptime_seconds = time.time() - BOT_START_TIME
        uptime = str(timedelta(seconds=int(uptime_seconds)))
        
        # Get system info
        system_info = {
            "os": platform.system(),
            "python": platform.python_version(),
            "memory_usage": f"{psutil.Process().memory_info().rss / (1024 * 1024):.1f} MB",
            "cpu_usage": f"{psutil.cpu_percent()}%"
        }
        
        # Format response
        response = (
            "*System Status* 🖥️\n\n"
            f"Status: *Online* ✅\n"
            f"Uptime: `{uptime}`\n"
            f"Memory: `{system_info['memory_usage']}`\n"
            f"CPU: `{system_info['cpu_usage']}`\n"
            f"Python: `{system_info['python']}`\n"
            f"OS: `{system_info['os']}`\n\n"
            "*Alya\\-chan siap melayani\\~\\!* ✨"
        )
        
        await update.message.reply_text(
            response,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Error in ping command: {e}")
        # Get language-specific error response
        error_response = get_response("error", context)
        
        await update.message.reply_text(
            error_response,
            parse_mode='MarkdownV2'
        )
