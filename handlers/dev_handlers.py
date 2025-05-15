"""
Developer Command Handlers for Alya Telegram Bot.

This module provides handlers for administrative commands restricted to developers,
including system management, debugging, statistics, and language settings.
"""

import logging
import os
import psutil
import subprocess
import json
import shlex
import re
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config.settings import DEVELOPER_IDS, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from core.models import get_user_history
from utils.language_handler import get_response
from utils.cache_manager import response_cache
from config.logging_config import log_command

logger = logging.getLogger(__name__)

# =========================
# Developer Authorization
# =========================

def is_developer(user_id: int) -> bool:
    """
    Check if user is authorized as a developer.
    
    Args:
        user_id: Telegram user ID to check
        
    Returns:
        True if user is a developer, False otherwise
    """
    return user_id in DEVELOPER_IDS

async def dev_command_wrapper(update: Update, context: CallbackContext, handler):
    """
    Security wrapper for developer commands.
    
    Ensures only authorized developers can execute restricted commands.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
        handler: Async handler function to execute if authorized
        
    Returns:
        Result of handler if authorized, or unauthorized message
    """
    if not is_developer(update.effective_user.id):
        await update.message.reply_text(
            get_response("dev_only", context),
            parse_mode='MarkdownV2'
        )
        return
    return await handler(update, context)

# =========================
# System Management Commands
# =========================

async def update_command(update: Update, context: CallbackContext) -> None:
    """Git pull and restart bot. Usage: /update [branch]"""
    async def handler(update: Update, context: CallbackContext):
        # Get target branch
        branch = context.args[0] if context.args else 'main'
        
        # Send initial message
        msg = await update.message.reply_text(
            f"*Updating Bot System*\n_Switching to branch:_ `{branch}` 🔄",
            parse_mode='MarkdownV2'
        )
        
        try:
            # Stash any changes
            subprocess.run(['git', 'stash'], check=True)
            
            # Switch branch and pull
            old_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
            subprocess.run(['git', 'checkout', branch], check=True)
            git_output = subprocess.check_output(['git', 'pull', 'origin', branch]).decode()
            new_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
            
            # Get commit messages & escape special chars
            if old_hash != new_hash:
                commit_log = subprocess.check_output(
                    ['git', 'log', '--pretty=format:• %s', f'{old_hash}..{new_hash}']
                ).decode()
                # Escape special characters for MarkdownV2
                commit_log = re.sub(r'([_*\[\]()~`>#+=|{}.!-])', r'\\\1', commit_log)
            else:
                commit_log = "No changes detected"

            # Update deps & restart
            subprocess.check_output(['pip', 'install', '-r', 'requirements.txt'])
            
            # Format update message with proper escaping
            update_message = (
                f"*Update Complete* ✨\n\n"
                f"*Branch:* `{branch}`\n"
                f"*Changes:*\n"
                f"{commit_log}\n\n"
                f"*Status:* Bot restarting\n\n"
                f"_Alya\\-chan will be back online shortly\\!_ 🌸"
            )
            
            await msg.edit_text(
                update_message,
                parse_mode='MarkdownV2'
            )
            
            # Restart bot via tmux
            try:
                subprocess.run(['tmux', 'send-keys', '-t', 'alya-bot', 'C-c'], check=True)
                subprocess.run(['sleep', '2'])
                subprocess.run(['tmux', 'send-keys', '-t', 'alya-bot', 'python main.py', 'Enter'], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restart bot in tmux: {e}")
                raise Exception("Failed to restart bot - check tmux session")
            
        except Exception as e:
            error_msg = str(e)
            safe_error = re.sub(r'([_*\[\]()~`>#+=|{}.!-])', r'\\\1', error_msg[:200])
            await msg.edit_text(
                f"*Update Failed*\n\n{safe_error}",
                parse_mode='MarkdownV2'
            )
            
    return await dev_command_wrapper(update, context, handler)

# =========================
# Monitoring Commands
# =========================

@log_command(logger)
async def stats_command(update: Update, context: CallbackContext) -> None:
    """Show bot statistics. Usage: /stats"""
    if not is_developer(update.effective_user.id):
        return

    stats = {
        "Memory": f"{psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB",
        "CPU": f"{psutil.cpu_percent()}%",
        "Users": len(context.bot_data.get('users', [])),
        "Chats": len(context.bot_data.get('chats', [])),
        "Commands": context.bot_data.get('command_count', 0)
    }
    
    text = "📊 *Bot Statistics*:\n" + "\n".join(f"• {k}: {v}" for k, v in stats.items())
    await update.message.reply_text(text, parse_mode='MarkdownV2')

@log_command(logger)
async def debug_command(update: Update, context: CallbackContext) -> None:
    """Toggle debug mode. Usage: /debug"""
    if not is_developer(update.effective_user.id):
        return
        
    context.bot_data['debug_mode'] = not context.bot_data.get('debug_mode', False)
    mode = "ON" if context.bot_data['debug_mode'] else "OFF"
    await update.message.reply_text(f"🔧 Debug Mode: {mode}")

@log_command(logger)
async def shell_command(update: Update, context: CallbackContext) -> None:
    """Execute shell command. Usage: /shell [command]"""
    if not is_developer(update.effective_user.id):
        await update.message.reply_text("Command ini khusus developer! 🚫")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /shell [command]")
        return
        
    cmd = " ".join(context.args)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout or result.stderr or "No output"
        # Escape markdown v2 special chars
        output = output.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        await update.message.reply_text(f"Command Output:\n```\n{output}\n```", parse_mode='MarkdownV2')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

@log_command(logger) 
async def clear_cache_command(update: Update, context: CallbackContext) -> None:
    """Clear response cache. Usage: /clearcache"""
    if not is_developer(update.effective_user.id):
        return
        
    count = response_cache.clear_all()
    await update.message.reply_text(f"Cache cleared: {count} entries removed")

# =========================
# Language Settings
# =========================

@log_command(logger)
async def set_language_command(update: Update, context: CallbackContext) -> None:
    """Set bot language. Usage: /setlang [id/en]"""
    if not is_developer(update.effective_user.id):
        return
        
    if not context.args or context.args[0] not in ['id', 'en']:
        await update.message.reply_text("Usage: /setlang [id/en]")
        return
        
    context.bot_data['language'] = context.args[0]
    await update.message.reply_text(f"Language set to: {context.args[0]}")
