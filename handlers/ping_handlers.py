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

        # Get system info with escaped special characters
        memory = psutil.virtual_memory()
        system = platform.uname()
        
        # Format system info safely
        safe_info = {
            'node': system.node.replace('-', '\\-').replace('.', '\\.'),
            'system': f"{system.system} {system.release}".replace('-', '\\-').replace('.', '\\.'),
            'machine': system.machine.replace('-', '\\-'),
            'processor': (system.processor or 'Unknown').replace('-', '\\-'),
        }

        # Build response with properly escaped characters
        response = (
            f"🏓 *Pong\\!* `{ping_time:.2f}s`\n\n"
            f"*Hostname:* `{safe_info['node']}`\n"
            f"*Uptime:* `{get_uptime()}`\n\n"
            f"*OS:* `{safe_info['system']} {safe_info['machine']}`\n"
            f"*CPU:* `{safe_info['processor']}`\n"
            f"*Memory:* `{bytes_to_gb(memory.used)} / {bytes_to_gb(memory.total)} ({memory.percent}%)`\n\n"
            "*Storage:*\n"
            f"{get_disk_info()}"
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

def get_disk_info() -> str:
    """Get formatted disk information."""
    disk_info = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            device = partition.device.replace('-', '\\-').replace('/', '\\/')
            mountpoint = partition.mountpoint.replace('-', '\\-').replace('/', '\\/')
            
            disk_info.append(
                f"*Device:* `{device}`\n"
                f"Size: `{bytes_to_gb(usage.total)}`\n"
                f"Used: `{bytes_to_gb(usage.used)}`\n"
                f"Free: `{bytes_to_gb(usage.free)}`\n"
                f"Usage: `{usage.percent}%`\n"
                f"Mount: `{mountpoint}`\n"
            )
        except:
            continue
    
    return "\n".join(disk_info) if disk_info else "No disk information available"
