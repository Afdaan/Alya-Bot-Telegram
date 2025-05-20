"""
Developer Command Handlers for Alya Telegram Bot.

This module provides handlers for administrative commands restricted to developers,
including system management, debugging, statistics, and language settings.
"""

import logging
import os
import sys
import psutil
import subprocess
import re
import time
from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config.settings import DEVELOPER_IDS, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from utils.language_handler import get_response
from utils.formatters import escape_markdown_v2
from utils.context_manager import context_manager
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

async def dev_command_wrapper(
    update: Update, 
    context: CallbackContext, 
    handler: Callable[[Update, CallbackContext], Awaitable[Any]]
) -> Any:
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

@log_command(logger)
async def update_command(update: Update, context: CallbackContext) -> None:
    """Git pull and restart bot. Usage: /update [branch]"""
    async def handler(update: Update, context: CallbackContext) -> None:
        # Get target branch with safe default
        branch = context.args[0] if context.args else 'main'
        branch = branch.strip()  # Sanitize input
        
        # Send initial message
        msg = await update.message.reply_text(
            f"*Updating Bot System*\n_Switching to branch:_ `{escape_markdown_v2(branch)}` 🔄",
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
            
            # Get commit messages
            commit_log = "No changes detected"
            if old_hash != new_hash:
                commit_log = subprocess.check_output(
                    ['git', 'log', '--pretty=format:• %s', f'{old_hash}..{new_hash}']
                ).decode()
                
                # Limit commit log length
                if len(commit_log) > 500:
                    commit_log = commit_log[:497] + "..."
            
            # Update dependencies silently
            subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True, 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Format update message with proper escaping
            update_message = (
                f"*Update Complete* ✨\n\n"
                f"*Branch:* `{escape_markdown_v2(branch)}`\n"
                f"*Changes:*\n"
                f"{escape_markdown_v2(commit_log)}\n\n"
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
            safe_error = escape_markdown_v2(error_msg[:200])
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
    async def handler(update: Update, context: CallbackContext) -> None:
        # Gather comprehensive statistics
        process = psutil.Process()
        memory_info = process.memory_info()
        
        stats = {
            "System": {
                "Memory Usage": f"{memory_info.rss / 1024 / 1024:.1f} MB",
                "CPU Usage": f"{psutil.cpu_percent()}%",
                "Uptime": _format_uptime(process.create_time()),
                "Python Version": sys.version.split()[0],
            },
            "Bot": {
                "Users": len(context.bot_data.get('users', [])),
                "Chats": len(context.bot_data.get('chats', [])),
                "Commands": context.bot_data.get('command_count', 0),
                "Cached Responses": len(response_cache._cache) if hasattr(response_cache, '_cache') else 0
            }
        }
        
        # Format statistics with markdown
        text = "*📊 Bot Statistics:*\n\n"
        
        for category, items in stats.items():
            text += f"*{category}:*\n"
            for key, value in items.items():
                text += f"• {key}: `{value}`\n"
            text += "\n"
        
        await update.message.reply_text(
            escape_markdown_v2(text), 
            parse_mode='MarkdownV2'
        )
    
    return await dev_command_wrapper(update, context, handler)

def _format_uptime(start_time: float) -> str:
    """Format uptime from start timestamp."""
    uptime_seconds = time.time() - start_time
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{int(days)}d {int(hours)}h {int(minutes)}m"
    elif hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(minutes)}m {int(seconds)}s"

@log_command(logger)
async def debug_command(update: Update, context: CallbackContext) -> None:
    """Toggle debug mode. Usage: /debug"""
    async def handler(update: Update, context: CallbackContext) -> None:
        # Toggle debug mode
        context.bot_data['debug_mode'] = not context.bot_data.get('debug_mode', False)
        mode = "ON ✅" if context.bot_data['debug_mode'] else "OFF ❌"
        
        # Save debug state in context
        debug_context = {
            'timestamp': int(time.time()),
            'enabled': context.bot_data['debug_mode'],
            'toggled_by': update.effective_user.id
        }
        
        try:
            context_manager.save_context(
                update.effective_user.id, 
                update.effective_chat.id,
                'debug_mode', 
                debug_context
            )
        except Exception as e:
            logger.error(f"Failed to save debug mode context: {e}")
        
        await update.message.reply_text(f"🔧 *Debug Mode: {mode}*", parse_mode='MarkdownV2')
    
    return await dev_command_wrapper(update, context, handler)

@log_command(logger)
async def shell_command(update: Update, context: CallbackContext) -> None:
    """Execute shell command. Usage: /shell [command]"""
    async def handler(update: Update, context: CallbackContext) -> None:
        if not context.args:
            await update.message.reply_text("Usage: `/shell [command]`", parse_mode='MarkdownV2')
            return
        
        # Join and sanitize command
        cmd = " ".join(context.args)
        
        # Security checks to prevent dangerous commands
        dangerous_patterns = [
            "rm -rf", "rm -f", "mkfs", "dd", ">", ">>", "|",
            "chmod 777", "chmod -R", "sudo", "passwd", "shutdown",
            "reboot"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in cmd:
                await update.message.reply_text(
                    f"⚠️ Potentially dangerous command detected: `{escape_markdown_v2(pattern)}`\n"
                    "Command rejected for safety.",
                    parse_mode='MarkdownV2'
                )
                return
        
        # Send processing message
        processing_msg = await update.message.reply_text("Executing command...")
        
        try:
            # Execute with timeout
            process = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            # Get output
            stdout = process.stdout or "No standard output"
            stderr = process.stderr or "No error output"
            return_code = process.returncode
            
            # Prepare result message
            result_msg = (
                f"*Command:* `{escape_markdown_v2(cmd)}`\n"
                f"*Exit Code:* `{return_code}`\n\n"
                f"*STDOUT:*\n```\n{escape_markdown_v2(stdout[:1000])}\n```\n\n"
                f"*STDERR:*\n```\n{escape_markdown_v2(stderr[:500])}\n```"
            )
            
            # Handle result too long
            if len(result_msg) > 4000:
                result_msg = result_msg[:3950] + "...\n\n_Output truncated_"
            
            await processing_msg.edit_text(result_msg, parse_mode='MarkdownV2')
            
        except subprocess.TimeoutExpired:
            await processing_msg.edit_text(
                f"⏱️ Command timed out after 30 seconds: `{escape_markdown_v2(cmd)}`",
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            await processing_msg.edit_text(
                f"⚠️ Error executing command:\n`{escape_markdown_v2(str(e))}`",
                parse_mode='MarkdownV2'
            )
    
    return await dev_command_wrapper(update, context, handler)

# =========================
# Database & Cache Management
# =========================

@log_command(logger)
async def clear_cache_command(update: Update, context: CallbackContext) -> None:
    """Clear response cache. Usage: /clearcache"""
    async def handler(update: Update, context: CallbackContext) -> None:
        # Get cache stats before clearing
        count_before = len(response_cache._cache) if hasattr(response_cache, '_cache') else 0
        memory_before = _get_cache_memory_usage()
        
        # Clear cache
        count = response_cache.clear_all()
        
        # Get stats after clearing
        memory_after = _get_cache_memory_usage()
        memory_freed = memory_before - memory_after
        
        # Format and send response
        await update.message.reply_text(
            f"*Cache Cleared* ♻️\n\n"
            f"• Entries removed: `{count}`\n"
            f"• Memory freed: `{memory_freed:.2f} MB`\n\n"
            f"_Cache has been reset to improve performance\\._",
            parse_mode='MarkdownV2'
        )
    
    return await dev_command_wrapper(update, context, handler)

def _get_cache_memory_usage() -> float:
    """Calculate approximate memory usage of the cache in MB."""
    try:
        import sys
        if not hasattr(response_cache, '_cache'):
            return 0.0
            
        # Rough estimate of cache memory usage
        size = 0
        for key, value in response_cache._cache.items():
            size += sys.getsizeof(key)
            size += sys.getsizeof(value)
        
        return size / (1024 * 1024)  # Convert to MB
    except Exception as e:
        logger.error(f"Error calculating cache memory: {e}")
        return 0.0

@log_command(logger)
async def db_stats_command(update: Update, context: CallbackContext) -> None:
    """Get database statistics. Usage: /dbstats"""
    async def handler(update: Update, context: CallbackContext) -> None:
        # Get database statistics
        try:
            stats = context_manager.get_db_stats()
            
            stats_text = (
                "*Database Statistics* 📊\n\n"
                f"*Size:* `{stats['db_size_mb']:.2f}` MB\n"
                f"*User Contexts:* `{stats['user_context_count']}`\n"
                f"*Chat History:* `{stats['chat_history_count']}`\n"
                f"*User Facts:* `{stats['user_facts_count']}`\n"
                f"*Oldest Record:* `{stats['oldest_record_days']:.1f}` days old\n"
                f"*Newest Record:* `{stats['newest_record_days']:.1f}` days old\n"
            )
            
            # Add table stats if available
            if 'tables' in stats:
                stats_text += "\n*Tables:*\n"
                for table, count in stats['tables'].items():
                    stats_text += f"• `{table}`: `{count}` rows\n"
            
            await update.message.reply_text(
                stats_text, 
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            logger.error(f"Error getting DB stats: {e}")
            await update.message.reply_text(
                f"*Error getting database stats:*\n`{escape_markdown_v2(str(e)[:200])}`",
                parse_mode='MarkdownV2'
            )
    
    return await dev_command_wrapper(update, context, handler)

@log_command(logger)
async def rotate_db_command(update: Update, context: CallbackContext) -> None:
    """Force database rotation. Usage: /rotatedb [confirm]"""
    async def handler(update: Update, context: CallbackContext) -> None:
        # Check for confirmation
        if not context.args or context.args[0].lower() != "confirm":
            await update.message.reply_text(
                "⚠️ *WARNING*: This will rotate the database and create a backup!\n\n"
                "To confirm, use: `/rotatedb confirm`",
                parse_mode='MarkdownV2'
            )
            return
        
        # Send processing message
        msg = await update.message.reply_text(
            "*Rotating database...* 🔄\nThis might take a moment.",
            parse_mode='MarkdownV2'
        )
        
        try:
            # Close current context manager and create backup
            context_manager._rotate_database()
            
            # Re-initialize DB with new file
            context_manager._init_db()
            
            await msg.edit_text(
                "✅ *Database rotation successful!*\n\n"
                "• Backup created\n"
                "• New database initialized\n\n"
                "_All data has been preserved\\._",
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            logger.error(f"Error rotating DB: {e}")
            await msg.edit_text(
                f"❌ *Error rotating database:*\n`{escape_markdown_v2(str(e)[:200])}`",
                parse_mode='MarkdownV2'
            )
    
    return await dev_command_wrapper(update, context, handler)

# =========================
# Language Settings
# =========================

@log_command(logger)
async def set_language_command(update: Update, context: CallbackContext) -> None:
    """Set bot default language. Usage: /setlang [id/en]"""
    async def handler(update: Update, context: CallbackContext) -> None:
        # Validate input
        if not context.args or context.args[0] not in SUPPORTED_LANGUAGES:
            language_list = ", ".join(f"`{code}`" for code in SUPPORTED_LANGUAGES)
            await update.message.reply_text(
                f"Usage: `/setlang [language_code]`\n\n"
                f"Supported languages: {language_list}",
                parse_mode='MarkdownV2'
            )
            return
        
        # Set language
        language_code = context.args[0]
        language_name = SUPPORTED_LANGUAGES[language_code]
        context.bot_data['language'] = language_code
        
        # Save globally
        language_context = {
            'timestamp': int(time.time()),
            'language': language_code,
            'set_by_user_id': update.effective_user.id,
            'set_by_username': update.effective_user.username or update.effective_user.first_name,
            'is_global': True
        }
        
        try:
            # Save to a special key for global settings
            context_manager.save_context(
                0,  # 0 = global setting
                0, 
                'global_language',
                language_context
            )
            logger.info(f"Global language set to {language_code} by {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Failed to save global language setting: {e}")
        
        # Confirm change
        await update.message.reply_text(
            f"🌐 *Global language set to {language_name}* ({language_code})\n\n"
            "_This affects default language for all users\\. Individual users can still "
            "set their own language preference with the /lang command\\._",
            parse_mode='MarkdownV2'
        )
    
    return await dev_command_wrapper(update, context, handler)
