"""
Roast Command Handlers for Alya Telegram Bot.

This module provides roast functionality for the bot, allowing it to
playfully "roast" users with sass and humor.
"""

import logging
import time
import aiohttp
import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from telegram import Update
from telegram.ext import CallbackContext
from telegram.error import BadRequest

# PERBAIKAN: Hapus GITHUB_API_TOKEN yang tidak ada
from config.settings import CHAT_PREFIX
from core.models import generate_response
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.context_manager import context_manager
from utils.rate_limiter import limiter
from core.personas import get_persona_context
from utils.natural_parser import extract_command_parts

logger = logging.getLogger(__name__)

# =========================
# Roast Command Handlers
# =========================

async def handle_roast_command(update: Update, context: CallbackContext) -> None:
    """
    Handle the roast command with natural argument parsing.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    # Check rate limit
    if not await limiter.acquire_with_feedback(update, context, "roast"):
        return

    # Extract message text
    if not update.message or not update.message.text:
        return

    message_text = update.message.text
    user = update.effective_user
    
    # Remove prefix for group chats
    if message_text.startswith(CHAT_PREFIX):
        message_text = message_text.replace(CHAT_PREFIX, "", 1).strip()
    
    # Get command and arguments
    parts = message_text.split(maxsplit=1)
    if len(parts) < 2 or parts[0].lower() != "roast":
        # Not a roast command
        return
    
    argument_text = parts[1].strip()
    
    # Determine roast type and target
    if argument_text.lower().startswith("github"):
        # GitHub roast
        github_parts = argument_text.split(maxsplit=1)
        if len(github_parts) < 2:
            await update.message.reply_text(
                "Cara penggunaan: `roast github <username>`\n\n"
                "Contoh: `roast github octocat`",
                parse_mode='MarkdownV2'
            )
            return
            
        github_username = github_parts[1].strip()
        await handle_github_roast(update, github_username)
        
    else:
        # Regular roast
        await handle_regular_roast(update, argument_text)

async def handle_regular_roast(update: Update, target_text: str) -> None:
    """
    Handle a regular roast command.
    
    Args:
        update: Telegram update object
        target_text: Target text for roasting (name + optional keywords)
    """
    user = update.effective_user
    target_parts = target_text.split()
    
    # Extract target and keywords
    target_name = target_parts[0] if target_parts else "anonymous"
    keywords = target_parts[1:] if len(target_parts) > 1 else []
    
    # Send typing indicator
    await update.message.chat.send_chat_action("typing")
    
    try:
        # Build prompt for roast
        prompt = build_roast_prompt(
            roaster_name=user.first_name or "User",
            target_name=target_name,
            keywords=keywords
        )
        
        # Generate roast content
        toxic_persona = get_persona_context("toxic")  # Get toxic persona context
        response = await generate_response(prompt + "\n\n" + toxic_persona, max_tokens=250)
        
        # Format roast for display
        formatted_response = format_markdown_response(response)
        
        # Send the formatted roast
        await update.message.reply_text(
            formatted_response,
            parse_mode='MarkdownV2'
        )
        
        # Log roast for context
        context_data = {
            'command': 'roast',
            'timestamp': int(time.time()),
            'target': target_name,
            'keywords': keywords,
            'roast_type': 'regular'
        }
        
        await save_roast_context(update, context_data)
        
    except Exception as e:
        logger.error(f"Error generating roast: {e}")
        await update.message.reply_text(
            f"*Gomen ne\\~* Alya tidak bisa membuat roast\\. Error: {escape_markdown_v2(str(e)[:100])}",
            parse_mode='MarkdownV2'
        )

async def handle_github_roast(update: Update, github_username: str) -> None:
    """
    Handle GitHub-specific roasts using GitHub API data.
    
    Args:
        update: Telegram update object
        github_username: GitHub username to roast
    """
    # Send typing indicator
    await update.message.chat.send_chat_action("typing")
    
    # Process message
    processing_message = await update.message.reply_text(
        f"*Mencari data GitHub untuk {escape_markdown_v2(github_username)}\\.\\.\\.*\n",
        parse_mode='MarkdownV2'
    )
    
    try:
        # Get GitHub user data
        github_data = await get_github_user_data(github_username)
        
        if not github_data:
            await processing_message.edit_text(
                f"*{escape_markdown_v2(github_username)}* tidak ditemukan di GitHub\\. Cek username dan coba lagi\\.",
                parse_mode='MarkdownV2'
            )
            return
            
        # Update processing message
        await processing_message.edit_text(
            f"*Menganalisis profil GitHub {escape_markdown_v2(github_username)}\\.\\.\\.*\n"
            "Alya sedang mempersiapkan roast yang panas 🔥",
            parse_mode='MarkdownV2'
        )
        
        # Build GitHub roast prompt
        user = update.effective_user
        prompt = build_github_roast_prompt(
            roaster_name=user.first_name or "User",
            target_name=github_username,
            github_data=github_data
        )
        
        # Generate roast content with toxic persona
        toxic_persona = get_persona_context("toxic")
        response = await generate_response(prompt + "\n\n" + toxic_persona, max_tokens=350)
        
        # Format roast for display
        formatted_response = format_markdown_response(response)
        
        # Send the formatted roast
        await processing_message.edit_text(
            formatted_response,
            parse_mode='MarkdownV2'
        )
        
        # Log roast for context
        context_data = {
            'command': 'roast',
            'timestamp': int(time.time()),
            'target': github_username,
            'roast_type': 'github',
            'github_data': {
                'repos': github_data.get('public_repos'),
                'followers': github_data.get('followers'),
                'bio': github_data.get('bio', '')[:50] # Truncate bio if too long
            }
        }
        
        await save_roast_context(update, context_data)
        
    except Exception as e:
        logger.error(f"Error generating GitHub roast: {e}")
        await processing_message.edit_text(
            f"*Gomen ne\\~* Alya tidak bisa membuat roast untuk GitHub user ini\\. Error: {escape_markdown_v2(str(e)[:100])}",
            parse_mode='MarkdownV2'
        )

async def save_roast_context(update: Update, context_data: Dict[str, Any]) -> None:
    """
    Save roast context for future reference.
    
    Args:
        update: Telegram update object
        context_data: Context data to save
    """
    try:
        if not update.effective_user:
            return
            
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Add additional metadata
        context_data.update({
            'chat_id': chat_id,
            'chat_type': update.effective_chat.type
        })
        
        # Save to context manager
        context_manager.save_context(user_id, chat_id, 'roast', context_data)
        
    except Exception as e:
        logger.error(f"Error saving roast context: {e}")

# =========================
# Helper Functions
# =========================

def build_roast_prompt(roaster_name: str, target_name: str, keywords: List[str] = None) -> str:
    """
    Build a prompt for generating a roast.
    
    Args:
        roaster_name: Name of the person requesting the roast
        target_name: Name of the target to roast
        keywords: Optional keywords to include in the roast
        
    Returns:
        Formatted prompt string
    """
    keywords_str = ", ".join(keywords) if keywords else "general"
    
    # Build prompt for natural roasting
    prompt = (
        f"{roaster_name} has requested you to roast someone named {target_name}.\n\n"
        f"Keywords to include in roast: {keywords_str}\n\n"
        "Create a short, funny, sassy roast (2-4 sentences) in Bahasa Indonesia. "
        "Make it playful and not overly mean. Use your toxic, sassy personality but keep it entertaining. "
        "The roast should be something a playful friend would say, not genuinely hurtful content."
    )
    
    return prompt

def build_github_roast_prompt(roaster_name: str, target_name: str, github_data: Dict[str, Any]) -> str:
    """
    Build a prompt for generating a GitHub-specific roast.
    
    Args:
        roaster_name: Name of the person requesting the roast
        target_name: GitHub username to roast
        github_data: GitHub profile data
        
    Returns:
        Formatted prompt string
    """
    # Extract useful GitHub stats
    repos = github_data.get('public_repos', 0)
    followers = github_data.get('followers', 0)
    following = github_data.get('following', 0)
    bio = github_data.get('bio') or "No bio available"
    created_at = github_data.get('created_at', '')
    
    # Calculate account age if possible
    account_age = ""
    if created_at:
        try:
            created_year = created_at.split('-')[0]
            account_age = f"GitHub account created in {created_year}"
        except:
            account_age = "GitHub account age unknown"
    
    # Get languages if available
    languages = "unknown programming languages"
    if github_data.get('language_data'):
        lang_list = list(github_data['language_data'].keys())[:5]  # Top 5 languages
        if lang_list:
            languages = ", ".join(lang_list)
    
    # Build comprehensive prompt
    prompt = (
        f"{roaster_name} has requested you to roast {target_name}'s GitHub profile.\n\n"
        f"GitHub Stats:\n"
        f"- Username: {target_name}\n"
        f"- Public Repositories: {repos}\n"
        f"- Followers: {followers}\n"
        f"- Following: {following}\n"
        f"- Bio: {bio}\n"
        f"- {account_age}\n"
        f"- Most used languages: {languages}\n\n"
        "Create a funny, sassy roast in Bahasa Indonesia about their GitHub profile "
        "(3-5 sentences). Make it specific to their GitHub statistics and coding habits. "
        "Use your toxic, sassy personality but keep it entertaining. Make jokes about "
        "their repositories, commit patterns, coding languages, or GitHub habits. "
        "Keep it playful like a fellow developer would tease another coder."
    )
    
    return prompt

async def get_github_user_data(username: str) -> Optional[Dict[str, Any]]:
    """
    Get GitHub user data from GitHub API.
    
    Args:
        username: GitHub username
        
    Returns:
        Dictionary with user data or None if not found
    """
    headers = {'Accept': 'application/vnd.github.v3+json'}
    
    try:
        # Get user profile
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://api.github.com/users/{username}',
                headers=headers
            ) as response:
                if response.status != 200:
                    return None
                    
                user_data = await response.json()
                
                # Get top languages
                repos_url = user_data.get('repos_url')
                language_data = {}
                
                if repos_url:
                    # Get repos with a limit
                    async with session.get(
                        f'{repos_url}?per_page=10&sort=pushed',
                        headers=headers
                    ) as repos_response:
                        if repos_response.status == 200:
                            repos = await repos_response.json()
                            
                            # Count languages
                            for repo in repos:
                                lang = repo.get('language')
                                if lang:
                                    language_data[lang] = language_data.get(lang, 0) + 1
                
                # Add language data to user data
                user_data['language_data'] = language_data
                
                return user_data
                
    except Exception as e:
        logger.error(f"Error fetching GitHub user data: {e}")
        return None
