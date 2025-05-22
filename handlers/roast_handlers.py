"""
Roast Mode Handlers for Alya Telegram Bot.

This module provides handlers for sassy, playful roasts of users.
"""

import re
import logging
import random
import asyncio
import yaml
import os
import time
from typing import Dict, List, Any, Optional, Tuple

from telegram import Update
from telegram.constants import ParseMode, ChatAction  # Pindahkan ChatAction ke constants
from telegram.ext import CallbackContext

from core.models import generate_chat_response
from utils.rate_limiter import gemini_limiter
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.context_manager import context_manager
from config.settings import GROUP_CHAT_REQUIRES_PREFIX, MAX_ROAST_LENGTH
from core.personas import get_persona_context
import aiohttp  # Add this import for async HTTP requests

# Setup logger
logger = logging.getLogger(__name__)

# Load roast templates
ROAST_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                "config", "persona", "roast.yaml")

try:
    with open(ROAST_CONFIG_PATH, 'r', encoding='utf-8') as f:
        ROAST_TEMPLATES = yaml.safe_load(f) or {}
except Exception as e:
    logger.error(f"Error loading roast templates: {e}")
    ROAST_TEMPLATES = {}

def parse_roast_target(text: str) -> Tuple[str, str, str]:
    """Parse roast command naturally to get target and context."""
    try:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return "", "", ""

        cmd_text = parts[1]
        
        # Parse: !roast @user <context>
        # Or: !roast "name with space" <context>
        # Or: !roast name <context>
        
        if '"' in cmd_text:
            # Extract quoted name
            name_end = cmd_text.find('"', 1)
            if name_end != -1:
                target_name = cmd_text[1:name_end]
                context = cmd_text[name_end + 1:].strip()
                return target_name, context, cmd_text
                
        # Check for basic name + context
        target_parts = cmd_text.split(maxsplit=1)
        target_name = target_parts[0].strip('@')
        context = target_parts[1] if len(target_parts) > 1 else ""
        
        return target_name, context, cmd_text
            
    except Exception as e:
        logger.error(f"Error parsing roast target: {e}")
        return "", "", ""

async def handle_roast_command(update: Update, context: CallbackContext) -> None:
    """Handle roast command with enhanced savagery."""
    user = update.effective_user
    message = update.message
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = user.id
    
    # Check rate limiting
    allowed, wait_time = await gemini_limiter.acquire_with_feedback(user_id)
    if not allowed:
        wait_msg = f"SABAR KONTOL! TUNGGU {wait_time:.1f} DETIK LAGI! 🤬"
        await message.reply_text(wait_msg, parse_mode=None)
        return

    # Parse command text for github prefix
    message_text = message.text.lower().strip()
    is_github_roast = message_text.startswith(("!gitroast", "/gitroast", "!github", "/github"))
    
    if is_github_roast:
        await handle_github_roast(update, context)
        return

    # Parse target and context naturally
    target_name, roast_context, full_text = parse_roast_target(message.text)
    
    # Show typing indicator
    await message.chat.send_action(ChatAction.TYPING)

    try:
        # Generate context-aware roast
        roast_text = await generate_roast(
            template="", # Template now comes from YAML
            target_name=target_name,  # Pass target_name instead of accessing undefined target
            target_id=user_id,  # Use user_id since we're roasting the target
            roast_context=roast_context
        )

        # Format and send
        roast_text = format_markdown_response(roast_text)
        await message.reply_text(
            roast_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None
        )

        # Store context
        context_data = {
            'command': 'roast',
            'timestamp': int(time.time()),
            'target_id': user_id,
            'target_name': target_name,
            'requester_id': user_id,
            'keywords': roast_context.split(),
            'should_reset_memory_state': True
        }
        
        context_manager.save_context(user_id, chat_id, 'memory_state', context_data)

    except Exception as e:
        logger.error(f"Error generating roast: {e}")
        await message.reply_text(
            f"ANJING ERROR NIH BANGSAT\\! {escape_markdown_v2(str(e)[:100])} 💀",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_github_roast(update: Update, context: CallbackContext) -> None:
    """Handle GitHub roast command with repo validation."""
    user = update.effective_user
    message = update.message
    
    # Check rate limiting
    allowed, wait_time = await gemini_limiter.acquire_with_feedback(user.id)
    if not allowed:
        await message.reply_text(
            f"SABAR KONTOL! TUNGGU {wait_time:.1f} DETIK LAGI! 🤬",
            parse_mode=None
        )
        return
    
    # Parse GitHub username/repo
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.reply_text(
            "Format: `/gitroast <username>` atau `/gitroast <username/repo>`\n"
            "Contoh:\n"
            "• `/gitroast Afdaan`\n"
            "• `/gitroast Afdaan/alya-bot-telegram`",
            parse_mode='MarkdownV2'
        )
        return
        
    target = args[0]
    is_repo = '/' in target
    
    # Show typing indicator
    await message.chat.send_action(ChatAction.TYPING)
    
    try:
        # Get GitHub data
        github_data = await get_github_info(target, not is_repo)
        if not github_data:
            await message.reply_text(
                f"NAJIS! USER/REPO `{escape_markdown_v2(target)}` GAK ADA TOLOL! 🤮",
                parse_mode='MarkdownV2'
            )
            return
            
        # Generate context-aware roast
        roast_context = {
            "type": "github_user" if not is_repo else "github_repo",
            "target": target,
            "data": github_data
        }
        
        roast_text = await generate_roast(
            template="", 
            target_name=target,
            target_id=user.id,
            roast_context=roast_context,
            is_technical=True
        )

        await message.reply_text(
            format_markdown_response(roast_text),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    except Exception as e:
        logger.error(f"Error in GitHub roast: {e}")
        await message.reply_text(
            f"ANJING ERROR NIH BANGSAT\\! {escape_markdown_v2(str(e)[:100])} 💀",
            parse_mode=ParseMode.MARKDOWN_V2
        )

def get_random_personal_roast_template(name: str, username: Optional[str] = None) -> str:
    """Get random personal roast template with name substitution."""
    try:
        # Default template if none are loaded
        default_template = (
            "ANJING {name}! MUKA LO TUH LEBIH JELEK DARI KETEK KAKEK GUE KONTOL! "
            "PANTES CRUSH LO KABUR SEMUA YA, MENDING SAMA KAMBING DARIPADA SAMA LO! 🤮"
        )
        
        # Get templates array from YAML - use 'templates' or 'personal' key
        templates = (ROAST_TEMPLATES.get('personal_templates', []) or 
                    ROAST_TEMPLATES.get('templates', {}).get('personal', []))
        
        if not templates:
            logger.warning("No roast templates found in YAML, using default")
            templates = [default_template]
        
        # Select random template
        template = random.choice(templates)
        if not template:
            logger.error("Empty template selected, using default")
            template = default_template
            
        # Replace placeholders
        template = template.replace("{name}", name)
        if username:
            template = template.replace("{username}", username)
            
        return template
        
    except Exception as e:
        logger.error(f"Error getting roast template: {e}")
        return default_template

async def get_github_info(target: str, is_user: bool = False) -> Dict[str, Any]:
    """Get GitHub repository or user information."""
    try:
        async with aiohttp.ClientSession() as session:
            # Build API URL based on type
            base_url = "https://api.github.com"
            endpoint = f"/users/{target}" if is_user else f"/repos/{target}"
            
            async with session.get(f"{base_url}{endpoint}") as response:
                if response.status == 404:
                    return {}
                    
                data = await response.json()
                
                if is_user:
                    return {
                        "name": data.get("name") or data.get("login"),
                        "bio": data.get("bio"),
                        "public_repos": data.get("public_repos", 0),
                        "followers": data.get("followers", 0),
                        "created_at": data.get("created_at")
                    }
                else:
                    return {
                        "name": data.get("name"),
                        "description": data.get("description"),
                        "language": data.get("language"),
                        "stars": data.get("stargazers_count", 0),
                        "forks": data.get("forks_count", 0),
                        "open_issues": data.get("open_issues_count", 0),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at")
                    }
                    
    except Exception as e:
        logger.error(f"Error fetching GitHub data: {e}")
        return {}

async def generate_roast(
    template: str,
    target_name: str,
    target_id: int,
    roast_context: str = "",
    is_technical: bool = False,
    github_repo: Optional[str] = None
) -> str:
    """Generate enhanced savage roast content."""
    try:
        # Get roast template from YAML
        with open(ROAST_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
            prompt_template = config.get("roast_prompt_template", "")

        # Format context-aware prompt
        prompt = prompt_template.format(
            target_name=target_name,
            roast_context=roast_context,
            github_repo=f"\nGitHub Repo: {github_repo}" if github_repo else ""
        )

        # Generate response with toxic persona
        response = await generate_chat_response(
            message=prompt,
            user_id=target_id,
            persona_context="You are now in SUPER TOXIC MODE! Be extremely savage!",
            language="id"
        )
        
        return response if response else "NAJIS ERROR! GA BISA ROAST SEKARANG KONTOL! 💀"
        
    except Exception as e:
        logger.error(f"Error generating roast: {e}")
        return f"BANGSAT! GA BISA ROAST {target_name}! ERROR TOLOL! 🤬"

async def handle_roast_callback(update: Update, context: CallbackContext) -> None:
    """
    Handle callback queries related to roast functionality.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    query = update.callback_query
    
    if not query or not query.data:
        return
        
    # Extract roast target from callback data
    if query.data.startswith("roast_"):
        # Extract user ID from callback data
        try:
            target_id = int(query.data.split("_")[1])
            
            # Simulate command execution
            update.message = query.message
            update.message.text = f"/roast {target_id}"
            
            # Handle as regular command
            await handle_roast_command(update, context)
            
        except Exception as e:
            logger.error(f"Error handling roast callback: {e}")
            await query.answer("Error processing roast request", show_alert=True)
            
    # Always answer the callback
    await query.answer()
