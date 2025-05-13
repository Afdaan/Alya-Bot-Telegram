"""
Ping Command Handler for Alya Telegram Bot.

This module provides system status monitoring functionality
through the /ping command.
"""

import os
import time
import platform
import psutil
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from utils.system_info import bytes_to_gb, get_uptime

# =========================
# Ping Command Handler
# =========================

async def ping_command(update: Update, context: CallbackContext) -> None:
    """
    Handle /ping command with system information response.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    try:
        # Calculate response time
        message_time = update.message.date.timestamp()
        ping_time = (datetime.now().timestamp() - message_time)

        # Get basic system information
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Format response with Markdown
        response = (
            f"🏓 *Pong\\!* `{ping_time:.2f}s`\n\n"
            f"*Uptime:* `{get_uptime()}`\n"
            f"*CPU Usage:* `{cpu_percent}%`\n"
            f"*Memory:* `{bytes_to_gb(memory.used)} / {bytes_to_gb(memory.total)} ({memory.percent}%)`"
        )

        # Send response
        await update.message.reply_text(
            response,
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        # Handle errors gracefully
        await update.message.reply_text(
            "Gomen ne\\~ Ada masalah saat mengecek sistem 🥺",
            parse_mode='MarkdownV2'
        )
