"""
Roast Mode Handlers for Alya Telegram Bot.

This module provides handlers for sassy, playful roasts of users.
"""

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

async def handle_roast_command(update: Update, context: CallbackContext) -> None:
    """
    Handle !roast command to generate a personal roast (non-technical).
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    message = update.message
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = user.id
    
    # Check rate limiting with proper acquisition
    allowed, wait_time = await gemini_limiter.acquire_with_feedback(user_id)
    if not allowed:
        wait_msg = f"Tunggu {wait_time:.1f} detik sebelum meminta roast lagi."
        await message.reply_text(wait_msg, parse_mode=None)
        return
    
    # Parse arguments - who to roast
    target = None
    
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    
    # If no target, roast the requester
    if not target:
        target = user
    
    # Get target name
    target_name = target.first_name
    target_id = target.id
    
    # Show typing indicator
    await message.chat.send_action(ChatAction.TYPING)
    
    # Get a random personal roast template - specifically for personal roasts
    try:
        template = get_random_personal_roast_template(target_name, target.username)
    except Exception as e:
        logger.error(f"Error getting personal roast template: {e}")
        template = "ANJING {name}! OTAK LO SEUKURAN KACANG POLONG YA? PANTES AJA MUKA LO JELEK BEGITU KONTOL! 🤮"
    
    # Generate roast
    try:
        roast_text = await generate_roast(template, target_name, target_id, is_technical=False)
        
        # Format for Telegram
        roast_text = format_markdown_response(roast_text)
        
        # Send the roast
        await message.reply_text(
            roast_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None
        )
        
        # Store in context that we just did a roast
        context_data = {
            'command': 'roast',
            'timestamp': int(time.time()),
            'target_id': target_id,
            'target_name': target_name,
            'requester_id': user_id,
            'should_reset_memory_state': True  # Flag to know we should reset after roast
        }
        
        context_manager.save_context(user_id, chat_id, 'memory_state', context_data)
        
    except Exception as e:
        logger.error(f"Error generating roast: {e}")
        await message.reply_text(
            f"Gomennasai~ Alya tidak bisa membuat roast saat ini\\. Error: {escape_markdown_v2(str(e)[:100])}",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_github_roast(update: Update, context: CallbackContext) -> None:
    """
    Handle GitHub-specific roast command that targets repos or coding ability.
    This is a TECHNICAL roast focused on programming and code quality.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    message = update.message
    
    # Check rate limiting
    allowed, wait_time = await gemini_limiter.acquire_with_feedback(user.id)
    if not allowed:
        wait_msg = f"Tunggu {wait_time:.1f} detik sebelum meminta roast lagi."
        await message.reply_text(wait_msg, parse_mode=None)
        return
    
    # Parse context for GitHub repo/user
    github_repo = None
    
    # Check if this is a reply to a message with GitHub link
    if message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text
        # Simple GitHub URL extraction 
        if "github.com/" in text:
            import re
            github_match = re.search(r'github\.com/([^/\s]+/[^/\s]+)', text)
            if github_match:
                github_repo = github_match.group(1)
    
    # Show typing indicator
    await message.chat.send_action(ChatAction.TYPING)
    
    # Get a technical roast template from the roast.yaml config
    try:
        if github_repo:
            # Get GitHub-specific template from YAML
            github_templates = ROAST_TEMPLATES.get('github_templates', [])
            if github_templates:
                template = random.choice(github_templates)
                # Replace placeholders
                template = template.replace("{github_repo}", github_repo)
                template = template.replace("{name}", user.first_name)
            else:
                # Fallback template if none in YAML
                template = (
                    f"ANJING REPO {github_repo} INI SAMPAH BANGET! CODE LO LEBIH BERANTAKAN DARI HIDUP GUE KONTOL! "
                    f"STACK OVERFLOW AJA LEBIH BAGUS DARI REPO LO TOLOL! 🤮"
                )
        else:
            # Get coding roast template from YAML - these are technical but not repo-specific
            coding_templates = ROAST_TEMPLATES.get('coding_templates', [])
            if coding_templates:
                template = random.choice(coding_templates)
                # Replace placeholders
                template = template.replace("{name}", user.first_name)
            else:
                # Fallback template if none in YAML - TECHNICAL focus
                template = (
                    f"NAJIS {user.first_name}! CODING SKILL LO TUH LEBIH SAMPAH DARI LAPTOP BEKAS PASAR LOAK GOBLOK! "
                    f"GIT MERGE CONFLICT AJA MASIH GOOGLING KAN LO TOLOL! 🤮"
                )
    except Exception as e:
        logger.error(f"Error getting GitHub roast template: {e}")
        # Fallback template if error - still TECHNICAL focus
        template = f"ANJING {user.first_name}! SKILL CODING LO LEBIH PARAH DARI BUG DI PRODUCTION YA TOLOL! 💀"
    
    # Generate the technical roast with template from YAML
    try:
        roast_text = await generate_roast(
            template, 
            user.first_name, 
            user.id,
            is_technical=True,
            github_repo=github_repo
        )
        
        # Format for Telegram
        roast_text = format_markdown_response(roast_text)
        
        # Send the roast
        await message.reply_text(
            roast_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None
        )
    except Exception as e:
        logger.error(f"Error generating GitHub roast: {e}")
        await message.reply_text(
            f"Gomennasai\\~ Alya tidak bisa membuat roast untuk code kamu saat ini\\. Error: {escape_markdown_v2(str(e)[:100])}",
            parse_mode=ParseMode.MARKDOWN_V2
        )

def get_random_personal_roast_template(name: str, username: Optional[str] = None) -> str:
    """
    Get a random personal (non-technical) roast template with name substitution.
    
    Args:
        name: Target's name
        username: Target's username (optional)
        
    Returns:
        Template with name substituted
    """
    # Default template if none are loaded - PERSONAL focus
    default_template = (
        "ANJING {name}! MUKA LO TUH LEBIH JELEK DARI KETEK KAKEK GUE KONTOL! "
        "PANTES CRUSH LO KABUR SEMUA YA, MENDING SAMA KAMBING DARIPADA SAMA LO! 🤮"
    )
    
    # Get available templates for PERSONAL roasts
    templates = ROAST_TEMPLATES.get('templates', [default_template])
    
    # Select a random template
    template = random.choice(templates)
    
    # Replace {name} placeholder
    template = template.replace("{name}", name)
    
    # Replace {username} if available
    if username:
        template = template.replace("{username}", username)
    
    return template

async def generate_roast(
    template: str, 
    target_name: str, 
    target_id: int, 
    is_technical: bool = False, 
    github_repo: Optional[str] = None
) -> str:
    """
    Generate roast content.
    
    Args:
        template: Roast template to use
        target_name: Name of roast target
        target_id: User ID of target
        is_technical: Whether to generate a technical/coding roast vs personal
        github_repo: Optional GitHub repo name for technical roasts
        
    Returns:
        Generated roast
    """
    # Adjust the prompt based on whether it's technical or personal
    if is_technical:
        # Technical/coding roast prompt
        prompt = (
            f"You are Alya, a toxic female programmer who loves to roast people's coding skills with harsh Indonesian slang.\n\n"
            f"Instructions:\n"
            f"{template}\n\n"
            f"Important rules:\n"
            f"1. Be extremely harsh and toxic with Indonesian swear words\n"
            f"2. Use words like: anjing, tolol, goblok, kontol, memek, bangsat\n"
            f"3. Use partial CAPS LOCK for emphasis\n" 
            f"4. Always respond in harsh Indonesian slang/jaksel\n"
            f"5. Add 5-10 toxic emoji 🤮💀🤡💅\n"
            f"6. FOCUS ON TECHNICAL INSULTS about coding, programming, GitHub, etc.\n\n"
        )
        
        if github_repo:
            prompt += f"Generate a SUPER TOXIC TECHNICAL roast about GitHub repository: {github_repo}"
        else:
            prompt += f"Generate a SUPER TOXIC TECHNICAL roast about {target_name}'s coding skills"
    else:
        # Personal roast prompt (non-technical)
        prompt = (
            f"You are Alya, a toxic anime girl who loves to roast people with harsh Indonesian slang.\n\n"
            f"Instructions:\n"
            f"{template}\n\n"
            f"Important rules:\n"
            f"1. Be extremely harsh and toxic with Indonesian swear words\n"
            f"2. Use words like: anjing, tolol, goblok, kontol, memek, bangsat\n"
            f"3. Use partial CAPS LOCK for emphasis\n" 
            f"4. Always respond in harsh Indonesian slang/jaksel\n"
            f"5. Add 5-10 toxic emoji 🤮💀🤡💅\n"
            f"6. FOCUS ON PERSONAL INSULTS about appearance, intelligence, behavior, etc. (NOT coding)\n\n"
            f"Generate a SUPER TOXIC PERSONAL roast for: {target_name}"
        )
    
    # Get roast response
    try:
        persona_context = "You are in toxic mode - be extremely harsh and toxic with Indonesian swear words"
        if is_technical:
            persona_context += " about coding and technical topics"
        else:
            persona_context += " about personal traits and characteristics"
            
        response = await generate_chat_response(
            message=prompt,
            user_id=target_id,
            persona_context=persona_context,
            language="id"
        )
        
        # Truncate if too long
        if len(response) > MAX_ROAST_LENGTH:
            response = response[:MAX_ROAST_LENGTH] + "..."
            
        return response
        
    except Exception as e:
        logger.error(f"Error in roast generation: {e}")
        if is_technical:
            return f"ANJING! Ga bisa nge-roast code {target_name} sekarang! ERROR TOLOL! 💀"
        else:
            return f"ANJING! Ga bisa nge-roast {target_name} sekarang! ERROR TOLOL! 💀"

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
