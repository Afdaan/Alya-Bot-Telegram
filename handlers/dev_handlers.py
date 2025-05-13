import logging
import os
import psutil
import subprocess
import json
import shlex
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config.settings import DEVELOPER_IDS
from core.models import get_user_history

logger = logging.getLogger(__name__)

def is_developer(user_id: int) -> bool:
    """Check if user is a developer."""
    return user_id in DEVELOPER_IDS

async def dev_command_wrapper(update: Update, context: CallbackContext, handler):
    """Wrapper for developer commands."""
    if not is_developer(update.effective_user.id):
        await update.message.reply_text(
            "Ara~ Command ini khusus developer sayang~ 💅✨",
            parse_mode='MarkdownV2'
        )
        return
    return await handler(update, context)

# System Management Commands
async def update_command(update: Update, context: CallbackContext) -> None:
    """Git pull and restart bot."""
    async def handler(update: Update, context: CallbackContext):
        msg = await update.message.reply_text(
            "*Updating Bot System*\n_Please wait\\.\\.\\._ 🔄",
            parse_mode='MarkdownV2'
        )
        
        try:
            # Git pull without specifying branch
            git_output = subprocess.check_output(['git', 'pull']).decode()
            
            # Install/update dependencies
            pip_output = "Dependencies updated successfully."
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

            # Truncate and escape output for MarkdownV2
            git_output_safe = git_output.replace('`', '').replace('\\', '')
            # Telegram MarkdownV2: code block must not contain triple backticks, so use single backtick or none
            update_message = (
                "*Update Complete\\!*\n"
                "*Git Changes:*\n"
                "```\n"
                f"{git_output_safe[:1500]}"
                "\n```\n"
                f"*Status:* {pip_output}\n"
                "_Restarting bot\\.\\.\\._ ✨"
            )
            await msg.edit_text(
                update_message,
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            error_msg = str(e).replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('`', '')
            await msg.edit_text(
                f"*Update Failed\\!*\n```\n{error_msg}\n```",
                parse_mode='MarkdownV2'
            )
    return await dev_command_wrapper(update, context, handler)

# Monitoring Commands
async def stats_command(update: Update, context: CallbackContext) -> None:
    """Get bot statistics."""
    async def handler(update: Update, context: CallbackContext):
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
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
        # Convert to string with limited length
        stats_json = json.dumps(stats, indent=2)[:2000]  # Limit to 2000 chars
        
        await update.message.reply_text(
            f"*Bot Statistics*\n```\n{stats_json}```",
            parse_mode='MarkdownV2'
        )
    
    return await dev_command_wrapper(update, context, handler)

async def debug_command(update: Update, context: CallbackContext) -> None:
    """Toggle debug mode and show debug info."""
    async def handler(update: Update, context: CallbackContext):
        try:
            # Toggle debug mode
            current_mode = context.bot_data.get('debug_mode', False)
            context.bot_data['debug_mode'] = not current_mode
            
            # Get memory info
            process = psutil.Process()
            memory = process.memory_info()
            
            # Pre-format values
            memory_mb = "{:.2f}".format(memory.rss / 1024 / 1024)
            cpu_percent = str(psutil.cpu_percent())
            pid = str(os.getpid())
            users_count = str(len(context.bot_data.get('users', [])))
            chats_count = str(len(context.bot_data.get('chats', [])))
            commands_count = str(context.bot_data.get('command_count', 0))
            last_response = context.bot_data.get('last_response', {}).get('time_taken', 'N/A')
            daily_messages = str(context.bot_data.get('daily_messages', 0))
            mode_status = 'DEBUG ON' if context.bot_data['debug_mode'] else 'DEBUG OFF'
            
            # Build message without f-strings
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
            error_msg = str(e).replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('`', '\\`')
            msg = "*❌ Error in debug:*\n`{}`".format(error_msg)
            await update.message.reply_text(msg, parse_mode='MarkdownV2')
    
    return await dev_command_wrapper(update, context, handler)

async def shell_command(update: Update, context: CallbackContext) -> None:
    """Execute shell command."""
    async def handler(update: Update, context: CallbackContext):
        command = ' '.join(context.args)
        if not command:
            await update.message.reply_text(
                "Please provide a command to execute.",
                parse_mode='MarkdownV2'
            )
            return
        
        try:
            output = subprocess.check_output(shlex.split(command), stderr=subprocess.STDOUT).decode()
            
            # Import the split function
            from utils.formatters import split_long_message
            
            # Split output if too long
            if len(output) > 4000:
                parts = split_long_message(output)
                await update.message.reply_text(
                    f"*Command Output* (split into {len(parts)} parts due to length):",
                    parse_mode='MarkdownV2'
                )
                
                for i, part in enumerate(parts):
                    await update.message.reply_text(
                        f"*Part {i+1}/{len(parts)}*\n```\n{part}```",
                        parse_mode='MarkdownV2'
                    )
            else:
                await update.message.reply_text(
                    f"```\n{output}```",
                    parse_mode='MarkdownV2'
                )
                
        except subprocess.CalledProcessError as e:
            error_output = e.output.decode() if hasattr(e, 'output') else str(e)
            # Truncate error if too long
            error_output = error_output[:1000] + "..." if len(error_output) > 1000 else error_output
            
            # Escape markdown characters
            error_output = error_output.replace('.', '\\.').replace('-', '\\-').replace('!', '\\!').replace('`', '\\`')
            
            await update.message.reply_text(
                f"Command failed with error:\n```\n{error_output}```",
                parse_mode='MarkdownV2'
            )
    
    return await dev_command_wrapper(update, context, handler)

# More commands will be added here...
