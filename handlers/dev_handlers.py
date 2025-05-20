"""
Developer Command Handlers for Alya Telegram Bot.

This module contains handlers for developer-only commands that provide
administrative functionality for bot management.
"""

import logging
import os
import subprocess
import sys
import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler

from config.settings import DEVELOPER_IDS, DEV_COMMANDS
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.context_manager import context_manager
from config.logging_config import log_command

logger = logging.getLogger(__name__)

# =========================
# Developer Commands
# =========================

@log_command(logger)
async def update_command(update: Update, context: CallbackContext) -> None:
    """
    Pull latest changes and restart the bot.
    Developer only command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user_id = update.effective_user.id
    
    # Check if user is developer
    if user_id not in DEVELOPER_IDS:
        await update.message.reply_text(
            "⛔ *Access Denied*\n\nOnly developers can use this command.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Send updating message
    status_msg = await update.message.reply_text(
        "🔄 *Updating Bot*\n\n"
        "*Step 1:* Pulling latest changes...",
        parse_mode='MarkdownV2'
    )
    
    try:
        # Pull latest changes
        process = subprocess.Popen(
            ["git", "pull"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            # Error during git pull
            error_output = stderr or "Unknown error"
            error_msg = f"❌ *Git Pull Failed*\n\n```\n{escape_markdown_v2(error_output)}\n```"
            await status_msg.edit_text(error_msg, parse_mode='MarkdownV2')
            return
            
        # Update status message
        await status_msg.edit_text(
            "🔄 *Updating Bot*\n\n"
            "*Step 1:* ✅ Latest changes pulled\n"
            "*Step 2:* Restarting bot...",
            parse_mode='MarkdownV2'
        )
        
        # Log the update
        logger.info(f"Bot update initiated by developer {user_id}")
        logger.info(f"Git pull output: {stdout}")
        
        # Final confirmation and restart
        await status_msg.edit_text(
            "✅ *Update Completed*\n\n"
            "Bot will restart now. Please wait a moment...",
            parse_mode='MarkdownV2'
        )
        
        # Schedule restart after a short delay
        await asyncio.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        logger.error(f"Error during update: {e}")
        await status_msg.edit_text(
            f"❌ *Update Failed*\n\n"
            f"Error: {escape_markdown_v2(str(e))}",
            parse_mode='MarkdownV2'
        )

@log_command(logger)
async def stats_command(update: Update, context: CallbackContext) -> None:
    """
    Get detailed bot statistics.
    Developer only command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user_id = update.effective_user.id
    
    # Check if user is developer
    if user_id not in DEVELOPER_IDS:
        await update.message.reply_text(
            "⛔ *Access Denied*\n\nOnly developers can use this command.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Start gathering stats
    await update.message.reply_text(
        "📊 *Gathering Bot Statistics*\n\nPlease wait...",
        parse_mode='MarkdownV2'
    )
    
    try:
        # Get basic system info
        process = psutil.Process(os.getpid())
        cpu_percent = process.cpu_percent(interval=1.0)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        uptime = time.time() - process.create_time()
        
        # Format uptime
        days = int(uptime // (24 * 3600))
        uptime %= (24 * 3600)
        hours = int(uptime // 3600)
        uptime %= 3600
        minutes = int(uptime // 60)
        uptime_str = f"{days}d {hours}h {minutes}m"
        
        # Get user count from context manager
        user_count = context_manager.get_unique_user_count()
        active_users = context_manager.get_active_user_count(days=1)
        total_messages = context_manager.get_total_message_count()
        
        # Get API key stats from rate limiter
        from utils.rate_limiter import get_api_key_manager
        key_stats = get_api_key_manager().get_key_stats()
        
        # Format key usage - using plain text instead of markdown
        key_usage_str = "\n".join([f"{key}: {count}" for key, count in key_stats.items()])
        
        # Create stats message - USING PLAIN TEXT INSTEAD OF MARKDOWN
        stats_text = (
            "📊 Bot Statistics\n\n"
            f"System Stats:\n"
            f"CPU Usage: {cpu_percent:.1f}%\n"
            f"Memory Usage: {memory_mb:.1f} MB\n"
            f"Uptime: {uptime_str}\n\n"
            
            f"User Stats:\n"
            f"Total Users: {user_count}\n"
            f"Active Today: {active_users}\n"
            f"Total Messages: {total_messages}\n\n"
            
            f"API Usage:\n"
            f"{key_usage_str}\n\n"
        )
        
        # Send stats WITHOUT parse_mode to avoid Markdown errors
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Error generating stats: {e}")
        await update.message.reply_text(
            f"❌ Stats Error\n\nError: {str(e)}"
        )

@log_command(logger)
async def debug_command(update: Update, context: CallbackContext) -> None:
    """
    Toggle debug mode.
    Developer only command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user_id = update.effective_user.id
    
    # Check if user is developer
    if user_id not in DEVELOPER_IDS:
        await update.message.reply_text(
            "⛔ *Access Denied*\n\nOnly developers can use this command.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Toggle debug mode in context
    current_mode = context.bot_data.get('debug_mode', False)
    new_mode = not current_mode
    context.bot_data['debug_mode'] = new_mode
    
    # Set logger level based on debug mode
    if new_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # Confirm mode change
    mode_str = "ON" if new_mode else "OFF"
    await update.message.reply_text(
        f"🐞 Debug mode: *{mode_str}*\n\n"
        f"Logger level: {'DEBUG' if new_mode else 'INFO'}",
        parse_mode='MarkdownV2'
    )

@log_command(logger)
async def shell_command(update: Update, context: CallbackContext) -> None:
    """
    Execute shell commands.
    Developer only command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user_id = update.effective_user.id
    
    # Check if user is developer
    if user_id not in DEVELOPER_IDS:
        await update.message.reply_text(
            "⛔ *Access Denied*\n\nOnly developers can use this command.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Get command from message
    message_text = update.message.text
    if message_text.startswith("/shell "):
        cmd = message_text[7:].strip()
    else:
        await update.message.reply_text(
            "Usage: `/shell command`\n\n"
            "Example: `/shell ls -la`",
            parse_mode='MarkdownV2'
        )
        return
    
    # Safety check - don't allow dangerous commands
    dangerous_commands = ["rm", "mkfs", "dd", ">", "sudo"]
    if any(dc in cmd.split() for dc in dangerous_commands):
        await update.message.reply_text(
            "⚠️ *Dangerous Command Blocked*\n\n"
            "For safety reasons, potentially harmful commands are blocked.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Execute command
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Format output
        if stdout:
            output = stdout.decode()
        elif stderr:
            output = f"ERROR: {stderr.decode()}"
        else:
            output = "Command executed successfully with no output."
        
        # Limit output length
        if len(output) > 3900:
            output = output[:3900] + "...\n[Output truncated]"
        
        # Send result
        await update.message.reply_text(
            f"📝 *Shell Command Result*\n\n"
            f"Command: `{escape_markdown_v2(cmd)}`\n\n"
            f"```\n{escape_markdown_v2(output)}\n```",
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Error executing shell command: {e}")
        await update.message.reply_text(
            f"❌ *Execution Error*\n\n"
            f"Error: {escape_markdown_v2(str(e))}",
            parse_mode='MarkdownV2'
        )

@log_command(logger)
async def lang_command(update: Update, context: CallbackContext) -> None:
    """
    Change bot language.
    Developer only command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    from config.settings import SUPPORTED_LANGUAGES
    
    user_id = update.effective_user.id
    
    # Check if user is developer
    if user_id not in DEVELOPER_IDS:
        await update.message.reply_text(
            "⛔ *Access Denied*\n\nOnly developers can use this command.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Get language code from message
    message_parts = update.message.text.split()
    if len(message_parts) > 1:
        lang_code = message_parts[1].lower()
        
        # Check if language is supported
        if lang_code in SUPPORTED_LANGUAGES:
            # Set language in context
            context.bot_data['language'] = lang_code
            
            # Confirm change
            lang_name = SUPPORTED_LANGUAGES[lang_code]
            await update.message.reply_text(
                f"🌐 Bot language changed to: *{escape_markdown_v2(lang_name)}* ({lang_code})",
                parse_mode='MarkdownV2'
            )
        else:
            # List supported languages
            langs = "\n".join([f"• {code} - {name}" for code, name in SUPPORTED_LANGUAGES.items()])
            await update.message.reply_text(
                f"❌ Unsupported language code: {lang_code}\n\n"
                f"Supported languages:\n{langs}",
                parse_mode=None
            )
    else:
        # Show current language and usage info
        current_lang = context.bot_data.get('language', 'id')
        lang_name = SUPPORTED_LANGUAGES.get(current_lang, 'Unknown')
        
        await update.message.reply_text(
            f"🌐 Current language: *{escape_markdown_v2(lang_name)}* ({current_lang})\n\n"
            f"Usage: `/lang code`\n\n"
            f"Example: `/lang en`",
            parse_mode='MarkdownV2'
        )

# Map command names to handler functions
DEV_HANDLERS = {
    'update': update_command,
    'stats': stats_command,
    'debug': debug_command,
    'shell': shell_command,
    'lang': lang_command
}

# Function to register all developer command handlers
def register_dev_handlers(app):
    """Register all developer command handlers."""
    for cmd_name, handler_func in DEV_HANDLERS.items():
        cmd_config = DEV_COMMANDS.get(cmd_name, {})
        if cmd_config.get('enabled', True):
            logger.info(f"Registering developer command: /{cmd_name}")
            app.add_handler(CommandHandler(cmd_name, handler_func))
