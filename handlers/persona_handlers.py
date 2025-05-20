"""
Persona Handlers for Alya Telegram Bot.

This module manages persona selection and switching for the bot,
allowing users to change Alya's personality traits.
"""

import logging
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from core.personas import persona_manager, get_persona_context
from utils.formatters import format_markdown_response, escape_markdown_v2
from utils.context_manager import context_manager

logger = logging.getLogger(__name__)

# Persona descriptions for user interface
PERSONA_DESCRIPTIONS = {
    "tsundere": "Tsundere: Sinis di luar, peduli di dalam",
    "waifu": "Waifu: Manis dan perhatian",
    "toxic": "Toxic: Agresif dan sarkastik",
    "informative": "Informative: Cerdas dan penuh pengetahuan",
    "professional": "Professional: Formal dan serius"
}

# Emoji for each persona
PERSONA_EMOJI = {
    "tsundere": "😤",
    "waifu": "💖",
    "toxic": "🔥",
    "informative": "📚",
    "professional": "👔"
}

async def handle_mode_change(update: Update, context: CallbackContext) -> None:
    """
    Handle mode/persona change command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    message = update.message
    
    # Extract mode name if provided directly
    if hasattr(context, 'user_data') and 'command_text' in context.user_data:
        command_text = context.user_data['command_text']
        parts = command_text.split(maxsplit=1)
        
        # If mode is specified directly (!mode waifu)
        if len(parts) > 1:
            mode_name = parts[1].lower()
            await _set_persona(update, context, mode_name)
            return
    
    # No mode specified, show selection menu
    await _show_persona_menu(update, context)

async def _show_persona_menu(update: Update, context: CallbackContext) -> None:
    """
    Show persona selection menu.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    
    # Get current persona
    current_persona = persona_manager.get_current_persona(user.id)
    
    # Build keyboard with available personas
    keyboard = []
    available_personas = persona_manager.get_available_personas()
    
    for persona in ["tsundere", "waifu", "toxic", "informative", "professional"]:
        if persona in available_personas:
            emoji = PERSONA_EMOJI.get(persona, "")
            description = PERSONA_DESCRIPTIONS.get(persona, persona.capitalize())
            current_marker = "✓ " if persona == current_persona else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{current_marker}{emoji} {description}",
                    callback_data=f"persona_{persona}"
                )
            ])
    
    # Create reply markup
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send selection menu
    await update.message.reply_text(
        f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Pilih mode kepribadian Alya\\:\n\n"
        f"Mode saat ini\\: *{escape_markdown_v2(current_persona)}* {PERSONA_EMOJI.get(current_persona, '')}",
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

async def _set_persona(update: Update, context: CallbackContext, persona_name: str) -> None:
    """
    Set persona for a user.
    
    Args:
        update: Telegram update object
        context: Callback context
        persona_name: Name of persona to set
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Validate persona
    if not persona_manager.set_user_persona(user.id, persona_name):
        # Invalid persona
        await update.message.reply_text(
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Gomenasai\\! Mode \"{escape_markdown_v2(persona_name)}\" tidak valid\\.\n\n"
            f"Mode yang tersedia\\: tsundere, waifu, toxic, informative, professional",
            parse_mode='MarkdownV2'
        )
        return
    
    # Save persona preference to context
    persona_context = {
        'timestamp': int(context_manager.get_current_timestamp()),
        'persona': persona_name,
        'set_by_user_id': user.id,
        'set_by_username': user.username or user.first_name
    }
    
    context_manager.save_context(user.id, chat_id, 'persona', persona_context)
    
    # Get emoji for selected persona
    emoji = PERSONA_EMOJI.get(persona_name, "")
    
    # Confirmation message
    await update.message.reply_text(
        f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Mode Alya sekarang\\: *{escape_markdown_v2(persona_name)}* {emoji}",
        parse_mode='MarkdownV2'
    )
    
    # Generate a greeting in the new persona
    try:
        # Get persona context
        persona_traits = get_persona_context(persona_name)
        
        # Simple greeting prompt
        greeting_prompt = f"Greet {user.first_name} with your new {persona_name} personality. Just a short greeting."
        
        # Generate greeting
        from core.models import generate_response
        greeting = await generate_response(greeting_prompt, persona_context=persona_traits)
        
        if greeting:
            # Format and send greeting
            formatted_greeting = format_markdown_response(greeting)
            await update.message.reply_text(formatted_greeting, parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Error generating persona greeting: {e}")
        # No need to send error message, the persona change was successful

async def handle_persona_callback(query, context: CallbackContext, persona_name: str) -> None:
    """
    Handle persona selection from inline keyboard.
    
    Args:
        query: CallbackQuery object
        context: CallbackContext
        persona_name: Selected persona name
    """
    user = query.from_user
    chat_id = query.message.chat_id
    
    # Set persona
    if not persona_manager.set_user_persona(user.id, persona_name):
        # Invalid persona
        await query.answer(f"Mode {persona_name} tidak valid.")
        return
    
    # Save persona preference to context
    persona_context = {
        'timestamp': int(context_manager.get_current_timestamp()),
        'persona': persona_name,
        'set_by_user_id': user.id,
        'set_by_username': user.username or user.first_name
    }
    
    context_manager.save_context(user.id, chat_id, 'persona', persona_context)
    
    # Get emoji for selected persona
    emoji = PERSONA_EMOJI.get(persona_name, "")
    
    # Update message to confirm change
    try:
        await query.edit_message_text(
            f"*{escape_markdown_v2(user.first_name)}\\-kun*\\~ Mode Alya sekarang\\: *{escape_markdown_v2(persona_name)}* {emoji}",
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error updating persona message: {e}")
        await query.answer(f"Mode diubah ke {persona_name}")
