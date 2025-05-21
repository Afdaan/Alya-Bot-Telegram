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

    # Parse target and keywords
    target = None
    target_name = None
    keywords = []
    
    # Get command parts: !roast @user keyword1 keyword2... 
    # Or: !roast "Custom Name" keyword1 keyword2...
    parts = message.text.split()
    if len(parts) > 1:
        # Check for quoted name first
        text = message.text
        quote_match = re.match(r'^!roast\s*"([^"]+)"', text)
        
        if quote_match:
            # Use custom name in quotes
            target_name = quote_match.group(1)
            # Get keywords after quoted name
            keywords = text[text.find('"', text.find('"')+1)+1:].strip().split()
        
        # If no quotes, check for mention
        elif parts[1].startswith('@'):
            target_username = parts[1][1:]  # Remove @ symbol
            try:
                chat_member = await message.chat.get_member(target_username)
                if chat_member:
                    target = chat_member.user
                    target_name = target.first_name
                keywords = parts[2:] if len(parts) > 2 else []
            except Exception:
                # Invalid username, use as literal name
                target_name = target_username
                keywords = parts[2:] if len(parts) > 2 else []
                
        # Check if replying to someone
        elif message.reply_to_message:
            target = message.reply_to_message.from_user
            target_name = target.first_name
            keywords = parts[1:] # Use all parts after command as keywords

    # If still no target/name, roast the requester
    if not target_name:
        target = user 
        target_name = user.first_name
        keywords = parts[1:] if len(parts) > 1 else []

    # Show typing indicator
    await message.chat.send_action(ChatAction.TYPING)

    try:
        # Generate roast with keywords
        template = get_random_personal_roast_template(target_name)
        roast_text = await generate_roast(
            template=template,
            target_name=target_name,
            target_id=target.id if target else user.id,
            keywords=keywords,
            is_technical=False
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
            'target_id': target.id if target else None,
            'target_name': target_name,
            'requester_id': user_id,
            'keywords': keywords,
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
    keywords: Optional[List[str]] = None,
    is_technical: bool = False,
    github_repo: Optional[str] = None
) -> str:
    """Generate enhanced savage roast content."""
    try:
        # Get roast persona and config
        persona_type = "tech_roast" if is_technical else "personal_roast"
        persona_context = get_persona_context(persona_type)
        
        # Get format settings from YAML
        format_config = ROAST_TEMPLATES.get('format', {})
        structure = format_config.get('structure', {})
        prompt_template = format_config.get('prompt_template', '')
        
        # Format keyword prompt if keywords provided
        keyword_section = ""
        if keywords:
            keyword_prompts = format_config.get('keyword_prompts', {})
            keyword_section = keyword_prompts.get('body', '').format(
                keywords='\n'.join(f"- {k}" for k in keywords)
            ) + '\n\n' + keyword_prompts.get('example', '')

        # Build prompt with proper format and structure
        prompt = f"""You are Alya, currently in SUPER TOXIC QUEEN mode. {persona_context}

TARGET INFO:
- Name: {target_name}
{f'- GitHub: {github_repo}' if github_repo else ''}

{keyword_section if keywords else ''}

FORMAT & STRUCTURE:
{prompt_template.format(
    min_roleplay=structure.get('roleplay', {}).get('min_actions', 2),
    max_roleplay=structure.get('roleplay', {}).get('max_actions', 3),
    min_lines=structure.get('main_roast', {}).get('min_lines', 5),
    max_lines=structure.get('main_roast', {}).get('max_lines', 6),
    min_chains=structure.get('chain_roasts', {}).get('min_chains', 2),
    max_chains=structure.get('chain_roasts', {}).get('max_chains', 3),
    min_emoji=4,
    max_emoji=8
)}
"""

        # Generate response
        response = await generate_chat_response(
            message=prompt,
            user_id=target_id,
            persona_context=persona_context,
            language="id"
        )
        
        return response if response else "NAJIS ERROR! GA BISA ROAST SEKARANG KONTOL! 💀"
        
    except Exception as e:
        logger.error(f"Error in roast generation: {e}")
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
