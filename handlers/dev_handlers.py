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
            # Git pull
            git_output = subprocess.check_output(['git', 'pull', 'origin', 'main']).decode()
            
            # Get TMUX session
            tmux_session = "alya-bot"
            
            # Restart command
            restart_cmd = f"""
            tmux send-keys -t {tmux_session} C-c
            sleep 2
            tmux send-keys -t {tmux_session} 'python main.py' Enter
            """
            
            subprocess.run(restart_cmd, shell=True)
            
            await msg.edit_text(
                f"*Update Complete\\!*\n```\n{git_output}```\n_Restarting bot\\.\\.\\._ ✨",
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await msg.edit_text(
                f"*Update Failed\\!*\n```\n{str(e)}```",
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
        
        await update.message.reply_text(
            f"*Bot Statistics*\n```\n{json.dumps(stats, indent=2)}```",
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
            
            # Format debug info with emojis
            debug_text = (
                "*🔍 Debug Information*\n\n"
                f"*System Status:*\n"
                f"💾 Memory: `{memory.rss / 1024 / 1024:.2f} MB`\n"
                f"🔄 CPU: `{psutil.cpu_percent()}%`\n"
                f"💻 PID: `{os.getpid()}`\n\n"
                f"*Bot Status:*\n"
                f"🤖 Mode: `{'DEBUG ON' if context.bot_data['debug_mode'] else 'DEBUG OFF'}`\n"
                f"👥 Users: `{len(context.bot_data.get('users', []))}`\n"
                f"💬 Chats: `{len(context.bot_data.get('chats', []))}`\n"
                f"📊 Commands: `{context.bot_data.get('command_count', 0)}`\n\n"
                f"*Performance:*\n"
                f"⚡ Last Response: `{context.bot_data.get('last_response', {}).get('time_taken', 'N/A')}`\n"
                f"📈 Messages Today: `{context.bot_data.get('daily_messages', 0)}`\n\n"
                f"*Debug Status:*\n"
                f"{'🟢 Debug Mode ON' if context.bot_data['debug_mode'] else '🔴 Debug Mode OFF'} ✨"
            )
            
            await update.message.reply_text(
                debug_text,
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            error_msg = str(e).replace('.', '\\.').replace('-', '\\-')
            await update.message.reply_text(
                f"*❌ Debug Error:*\n`{error_msg}`",
                parse_mode='MarkdownV2'
            )
    
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
            output = subprocess.check_output(shlex.split(command)).decode()
            await update.message.reply_text(
                f"```\n{output}```",
                parse_mode='MarkdownV2'
            )
        except subprocess.CalledProcessError as e:
            await update.message.reply_text(
                f"Command failed with error:\n```\n{e}```",
                parse_mode='MarkdownV2'
            )
    
    return await dev_command_wrapper(update, context, handler)

# More commands will be added here...
