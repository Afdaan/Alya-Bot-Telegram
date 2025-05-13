import os
import time
import platform
import psutil
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext

async def ping_command(update: Update, context: CallbackContext) -> None:
    """Handle ping command with system information."""
    try:
        # Calculate ping
        message_time = update.message.date.timestamp()
        ping_time = (datetime.now().timestamp() - message_time)

        # Get system info
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Build response with limited info
        response = (
            f"🏓 *Pong\\!* `{ping_time:.2f}s`\n\n"
            f"*Uptime:* `{get_uptime()}`\n"
            f"*CPU Usage:* `{cpu_percent}%`\n"
            f"*Memory:* `{bytes_to_gb(memory.used)} / {bytes_to_gb(memory.total)} ({memory.percent}%)`"
        )

        await update.message.reply_text(
            response,
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        await update.message.reply_text(
            "Gomen ne\\~ Ada masalah saat mengecek sistem 🥺",
            parse_mode='MarkdownV2'
        )

def bytes_to_gb(bytes_value: int) -> str:
    """Convert bytes to GB with 2 decimal places."""
    return f"{bytes_value / (1024**3):.2f} GB"

def get_uptime() -> str:
    """Get system uptime in hours and minutes."""
    uptime = time.time() - psutil.boot_time()
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    return f"{hours} hours, {minutes} minutes"
