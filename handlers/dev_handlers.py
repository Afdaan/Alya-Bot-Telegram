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
from telegram.ext import CallbackContext, CommandHandler, Application
from telegram.constants import ParseMode

from config.settings import (
    DEVELOPER_IDS, 
    DEV_COMMANDS, 
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE
)
from utils.formatters import format_markdown_response, escape_markdown_v2, format_dev_message
from utils.context_manager import context_manager
from config.logging_config import log_command

logger = logging.getLogger(__name__)

# Process start time for uptime calculation
process_start_time = time.time()

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
        "*Step 1:* Pulling latest changes\\.\\.\\.",
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
            "*Step 2:* Restarting bot\\.\\.\\.",
            parse_mode='MarkdownV2'
        )
        
        # Log the update
        logger.info(f"Bot update initiated by developer {user_id}")
        logger.info(f"Git pull output: {stdout}")
        
        # Get latest commit info
        changelog = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%h %s"],
            text=True
        )
        
        # Send final confirmation with changelog
        await status_msg.edit_text(
            f"✅ *Update Complete*\n\n"
            f"*Changelog:*\n"
            f"```\n{escape_markdown_v2(changelog)}\n```",
            parse_mode='MarkdownV2'
        )
        
        # Schedule restart after a short delay
        await asyncio.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        logger.error(f"Error during update: {e}")
        safe_error = escape_markdown_v2(str(e))
        await status_msg.edit_text(
            f"❌ *Update Failed*\n\n"
            f"Error: {safe_error}",
            parse_mode='MarkdownV2'
        )

@log_command(logger)
async def stats_command(update: Update, context: CallbackContext) -> None:
    """
    Display bot statistics.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    
    # Check if it's a developer or admin
    if user.id not in DEVELOPER_IDS:
        await update.message.reply_text(
            f"*{escape_markdown_v2(user.first_name)}\\-kun\\~* Maaf, command ini hanya untuk developer\\.",
            parse_mode='MarkdownV2'
        )
        return
        
    # Show processing status
    status_msg = await update.message.reply_text(
        "Mengumpulkan statistik...",
        parse_mode=None
    )
    
    try:
        # Get system stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get bot stats
        uptime = time.time() - process_start_time
        uptime_str = format_uptime(int(uptime))
        
        # Get database stats
        db_stats = context_manager.get_db_stats()
        
        # Get memory stats
        memory_stats = context_manager.get_memory_stats(user.id)
        
        # Get API key stats (if available)
        try:
            from utils.rate_limiter import api_key_manager
            key_stats = api_key_manager.get_key_stats()
            keys_info = "\n".join([
                f"• Key {i+1}: {'🟢 ' if s.get('is_current') else '🔴 '}"
                f"{s.get('key_prefix', '')} "
                f"{'(cooldown until ' + str(s.get('cooldown_ends')) + ')' if s.get('in_cooldown') else ''}"
                for i, s in enumerate(key_stats)
            ])
        except Exception as key_err:
            logger.error(f"Error getting key stats: {key_err}")
            keys_info = "Error retrieving API key information"
        
        # Format response
        response = (
            f"*🤖 ALYA BOT STATISTICS*\n\n"
            f"*System:*\n"
            f"• CPU: {psutil.cpu_percent()}%\n"
            f"• RAM: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)\n"
            f"• Disk: {disk.percent}% ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)\n"
            f"• Uptime: {uptime_str}\n\n"
            
            f"*Database:*\n"
            f"• Total users: {db_stats.get('user_count', 0)}\n"
            f"• Total messages: {db_stats.get('total_messages', 0)}\n"
            f"• Active users (24h): {db_stats.get('active_users_24h', 0)}\n"
            f"• DB size: {db_stats.get('db_size_mb', 0):.1f} MB\n\n"
            
            f"*API Keys:*\n{keys_info}\n\n"
            
            f"*User Memory:*\n"
            f"• Messages: {memory_stats.get('total_messages', 0)}\n"
            f"• Memory usage: {memory_stats.get('memory_usage_percent', 0)}%\n"
            f"• Personal facts: {memory_stats.get('personal_facts', 0)}\n"
        )
        
        # Format response with markdown
        formatted_response = format_dev_message(response)
        
        # Send response
        await status_msg.edit_text(
            formatted_response,
            parse_mode='MarkDownV2'
        )
        
    except Exception as e:
        logger.error(f"Error generating stats: {e}")
        await status_msg.edit_text(
            f"Error generating stats: {str(e)}",
            parse_mode=None
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
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    args = context.args
    
    if not args or len(args) != 1:
        # Show language selection keyboard
        keyboard = []
        row = []
        
        for code, name in SUPPORTED_LANGUAGES.items():
            # Escape parentheses in button text for MarkdownV2
            safe_name = escape_markdown_v2(name)
            button = InlineKeyboardButton(f"{name}", callback_data=f"lang_{code}")
            row.append(button)
            
            # Two buttons per row
            if len(row) == 2:
                keyboard.append(row)
                row = []
                
        # Add any remaining buttons
        if row:
            keyboard.append(row)
            
        markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*{escape_markdown_v2(user.first_name)}\\-kun\\~* Silakan pilih bahasa yang ingin kamu gunakan:",
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
        return
        
    # Get requested language
    requested_lang = args[0].lower()
    
    # Validate language
    if requested_lang not in SUPPORTED_LANGUAGES:
        valid_langs = ", ".join(SUPPORTED_LANGUAGES.keys())
        await update.message.reply_text(
            f"*{escape_markdown_v2(user.first_name)}\\-kun\\~* Bahasa `{escape_markdown_v2(requested_lang)}` tidak didukung\\.\n\n"
            f"Bahasa yang didukung: `{escape_markdown_v2(valid_langs)}`",
            parse_mode='MarkdownV2'
        )
        return
    
    # Update language preference
    language_context = {
        'timestamp': int(time.time()),
        'language': requested_lang,
        'set_by_user_id': user.id,
        'set_by_username': user.username or user.first_name
    }
    
    context_manager.save_context(user.id, chat_id, 'language', language_context)
    language_name = SUPPORTED_LANGUAGES[requested_lang]
    
    await update.message.reply_text(
        f"*{escape_markdown_v2(user.first_name)}\\-kun\\~* Alya akan menggunakan bahasa "
        f"{escape_markdown_v2(language_name)} \\({escape_markdown_v2(requested_lang)}\\) sekarang\\.",
        parse_mode='MarkdownV2'
    )

def format_uptime(seconds: int) -> str:
    """Format seconds into days, hours, minutes, seconds string."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)

# Map command names to handler functions
DEV_HANDLERS = {
    'update': update_command,
    'stats': stats_command,
    'debug': debug_command,
    'shell': shell_command,
    'lang': lang_command,
}

# Function to register all developer command handlers
def register_dev_handlers(app: Application) -> None:
    """Register all developer command handlers."""
    for cmd_name, handler_func in DEV_HANDLERS.items():
        cmd_config = DEV_COMMANDS.get(cmd_name, {})
        if cmd_config.get('enabled', True):
            logger.info(f"Registering developer command: /{cmd_name}")
            app.add_handler(CommandHandler(cmd_name, handler_func))
