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
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config.settings import DEVELOPER_IDS, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from core.models import get_user_history
from utils.language_handler import get_response
from utils.cache_manager import response_cache

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
    """
    Git pull and restart bot.
    
    Updates the bot with latest code from repository and restarts
    the bot process within its TMUX session.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    async def handler(update: Update, context: CallbackContext):
        # Send initial message
        msg = await update.message.reply_text(
            "*Updating Bot System*\n_Please wait_ 🔄",
            parse_mode='MarkdownV2'
        )
        
        try:
            # Get current commit hash before pull
            old_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
            
            # Git pull without specifying branch
            git_output = subprocess.check_output(['git', 'pull']).decode()
            
            # Get new commit hash after pull
            new_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
            
            # Get commit messages between old and new (if different)
            commit_messages = ""
            if old_hash != new_hash:
                # Format: [hash] commit message
                commit_log = subprocess.check_output(
                    ['git', 'log', '--pretty=format:• `%h` %s', f'{old_hash}..{new_hash}']
                ).decode()
                commit_messages = commit_log if commit_log else "No new commits"
            else:
                commit_messages = "No changes detected"
            
            # Install/update dependencies
            pip_output = "Dependencies updated successfully"
            subprocess.check_output(['pip', 'install', '-r', 'requirements.txt'])
            
            # Get TMUX session
            tmux_session = "alya-bot"
            # Restart command
            restart_cmd = f"""
            tmux send-keys -t {tmux_session} C-c
            sleep 2
            tmux send-keys -t {tmux_session} 'python main.py' Enter
            """
            subprocess.run(restart_cmd, shell=True)

            # Perhatikan cara escape karakter # dengan variabel terpisah
            escaped_commit_messages = commit_messages.replace('#', '\\#')
            
            # Format final update message with commit details
            update_message = (
                "*Update Complete* ✨\n\n"
                "*Changes Applied:*\n"
                f"{escaped_commit_messages}\n\n"
                "*Dependencies:* Updated\n"
                "*Status:* Bot restarting\n\n"
                "_Alya\\-chan will be back online shortly\\!_ 🌸"
            )
            
            await msg.edit_text(
                update_message,
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            # Create safe error message
            error_msg = str(e)
            safe_error = ""
            for char in error_msg[:200]:
                if char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n":
                    safe_error += char
                else:
                    safe_error += " "
                    
            await msg.edit_text(
                f"*Update Failed*\n\n{safe_error}",
                parse_mode='MarkdownV2'
            )
    
    # Run with developer authorization
    return await dev_command_wrapper(update, context, handler)

# =========================
# Monitoring Commands
# =========================

async def stats_command(update: Update, context: CallbackContext) -> None:
    """
    Get bot statistics and system information.
    
    Provides memory usage, user counts, and other operational statistics.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    async def handler(update: Update, context: CallbackContext):
        # Gather system information
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Compile statistics
        stats = {
            'System': {
                'CPU': f"{psutil.cpu_percent()}%",
                'Memory': f"{memory.percent}%",
                'Disk': f"{disk.percent}%"
            },
            'Bot': {
                'Users': len(context.bot_data.get('users', [])),
                'Chats': len(context.bot_data.get('chats', [])),
                'Commands': context.bot_data.get('command_count', 0)
            }
        }
        
        # Convert to formatted JSON string
        stats_json = json.dumps(stats, indent=2)[:2000]  # Limit to 2000 chars
        
        # Send statistics message
        await update.message.reply_text(
            f"*Bot Statistics*\n```\n{stats_json}```",
            parse_mode='MarkdownV2'
        )
    
    # Run with developer authorization
    return await dev_command_wrapper(update, context, handler)

async def debug_command(update: Update, context: CallbackContext) -> None:
    """
    Toggle debug mode and show debug information.
    
    Enables verbose logging and shows detailed system information.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    async def handler(update: Update, context: CallbackContext):
        try:
            # Toggle debug mode
            current_mode = context.bot_data.get('debug_mode', False)
            context.bot_data['debug_mode'] = not current_mode
            
            # Get memory information
            process = psutil.Process()
            memory = process.memory_info()
            
            # Format values for display
            memory_mb = "{:.2f}".format(memory.rss / 1024 / 1024)
            cpu_percent = str(psutil.cpu_percent())
            pid = str(os.getpid())
            users_count = str(len(context.bot_data.get('users', [])))
            chats_count = str(len(context.bot_data.get('chats', [])))
            commands_count = str(context.bot_data.get('command_count', 0))
            last_response = context.bot_data.get('last_response', {}).get('time_taken', 'N/A')
            daily_messages = str(context.bot_data.get('daily_messages', 0))
            mode_status = 'DEBUG ON' if context.bot_data['debug_mode'] else 'DEBUG OFF'
            
            # Build debug information message
            debug_text = (
                "*🔍 Debug Information*\n\n"
                "*System Status:*\n"
                "💾 Memory: `{} MB`\n"
                "🔄 CPU: `{}%`\n"
                "💻 PID: `{}`\n\n"
                "*Bot Status:*\n"
                "🤖 Mode: `{}`\n"
                "👥 Users: `{}`\n"
                "💬 Chats: `{}`\n"
                "📊 Commands: `{}`\n\n"
                "*Performance:*\n"
                "⚡ Last Response: `{}`\n"
                "📈 Messages Today: `{}`\n\n"
                "*Debug Status:*\n"
                "{} ✨"
            ).format(
                memory_mb, cpu_percent, pid,
                mode_status, users_count, chats_count, commands_count,
                last_response, daily_messages,
                "🟢 Debug Mode ON" if context.bot_data['debug_mode'] else "🔴 Debug Mode OFF"
            )
            
            await update.message.reply_text(debug_text, parse_mode='MarkdownV2')
            
        except Exception as e:
            # Format error message for MarkdownV2
            error_msg = str(e).replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('`', '\\`')
            msg = "*❌ Error in debug:*\n`{}`".format(error_msg)
            await update.message.reply_text(msg, parse_mode='MarkdownV2')
    
    # Run with developer authorization
    return await dev_command_wrapper(update, context, handler)

async def shell_command(update: Update, context: CallbackContext) -> None:
    """
    Execute shell commands on the host system.
    
    Allows developers to run basic system maintenance commands.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    async def handler(update: Update, context: CallbackContext):
        # Get command from arguments
        command = ' '.join(context.args)
        if not command:
            await update.message.reply_text(
                "Please provide a command to execute\\.",
                parse_mode='MarkdownV2'
            )
            return
        
        try:
            # Execute command with security precautions
            output = subprocess.check_output(shlex.split(command), stderr=subprocess.STDOUT).decode()
            
            # Import helper for long message splitting
            from utils.formatters import split_long_message
            
            # Escape special characters for MarkdownV2
            def escape_markdown(text):
                special_chars = '_*[]()~`>#+-=|{}.!'
                return ''.join('\\' + c if c in special_chars else c for c in text)
            
            escaped_output = escape_markdown(output)
            
            # Split output if too long
            if len(escaped_output) > 4000:
                parts = split_long_message(escaped_output)
                await update.message.reply_text(
                    f"*Command Output* \\(split into {len(parts)} parts due to length\\):",
                    parse_mode='MarkdownV2'
                )
                
                for i, part in enumerate(parts):
                    await update.message.reply_text(
                        f"*Part {i+1}/{len(parts)}*\n```\n{part}```",
                        parse_mode='MarkdownV2'
                    )
            else:
                await update.message.reply_text(
                    f"```\n{escaped_output}```",
                    parse_mode='MarkdownV2'
                )
                
        except subprocess.CalledProcessError as e:
            # Handle command execution errors
            error_output = e.output.decode() if hasattr(e, 'output') else str(e)
            # Truncate long error messages
            error_output = error_output[:1000] + "..." if len(error_output) > 1000 else error_output
            
            # Escape markdown characters
            error_output = escape_markdown(error_output)
            
            await update.message.reply_text(
                f"*Command failed with error:*\n```\n{error_output}```",
                parse_mode='MarkdownV2'
            )
    
    # Run with developer authorization 
    return await dev_command_wrapper(update, context, handler)

async def clear_cache_command(update: Update, context: CallbackContext) -> None:
    """
    Clear response cache to refresh AI responses.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    async def handler(update: Update, context: CallbackContext):
        try:
            # Clear all cache
            count = response_cache.clear_all()
            
            await update.message.reply_text(
                f"*Cache Cleared Successfully* ✅\n\n{count} cached responses removed\\.",
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            await update.message.reply_text(
                f"*Error Clearing Cache* ❌\n\n`{str(e)}`",
                parse_mode='MarkdownV2'
            )
    
    # Run with developer authorization
    return await dev_command_wrapper(update, context, handler)

# =========================
# Language Settings
# =========================

async def set_language_command(update: Update, context: CallbackContext) -> None:
    """
    Set the bot's default language.
    
    Changes the language used for responses throughout the bot.
    Available languages defined in SUPPORTED_LANGUAGES.
    
    Args:
        update: Telegram Update object
        context: CallbackContext object
    """
    async def handler(update: Update, context: CallbackContext):
        # Get current language
        current_language = context.bot_data.get("language", DEFAULT_LANGUAGE)
        
        # If no arguments provided, show help
        if not context.args:
            # Show current language and instructions
            help_text = get_response("lang_help", context, 
                                    current_code=current_language,
                                    current_name=SUPPORTED_LANGUAGES.get(current_language, "Unknown"))
            
            await update.message.reply_text(
                help_text,
                parse_mode="MarkdownV2"
            )
            return

        # Get requested language code
        language_code = context.args[0].lower()
        
        # Check if valid language code
        if language_code not in SUPPORTED_LANGUAGES:
            invalid_msg = get_response("lang_invalid", context, code=language_code)
            await update.message.reply_text(
                invalid_msg,
                parse_mode="MarkdownV2"
            )
            return

        # Update language setting
        context.bot_data["language"] = language_code
        language_name = SUPPORTED_LANGUAGES.get(language_code)
        
        # Get success message in the NEW language to demonstrate immediate effect
        # Fix parameter name: change language=language_code, language=language_code to language=language_code, language_name=language_name
        success_msg = get_response("lang_success", language=language_code, language_name=language_name)
        
        # Immediately show confirmation message in the new language
        await update.message.reply_text(
            success_msg,
            parse_mode="MarkdownV2"
        )

        # Also add an example response to demonstrate new language is working
        example_responses = {
            "en": "*Language changed successfully\\!* ✨\n\nAlya\\-chan will now communicate in English\\. Is there anything I can help you with\\?",
            "id": "*Bahasa berhasil diubah\\!* ✨\n\nAlya\\-chan akan berkomunikasi dalam Bahasa Indonesia sekarang\\. Ada yang bisa Alya bantu\\?"
        }
        
        # Import asyncio at the top of the file if not already imported
        try:
            # Send an additional message to demonstrate the new language
            await asyncio.sleep(1)  # Small delay for better UX
            await update.message.reply_text(
                example_responses.get(language_code, example_responses["id"]),
                parse_mode="MarkdownV2"
            )
        except NameError:
            # If asyncio is not imported
            import asyncio
            await asyncio.sleep(1)
            await update.message.reply_text(
                example_responses.get(language_code, example_responses["id"]),
                parse_mode="MarkdownV2"
            )
        
        # Log the change
        logger.info(f"Language changed to {language_code} ({language_name}) by user {update.effective_user.id}")

    # Run with developer authorization
    return await dev_command_wrapper(update, context, handler)
