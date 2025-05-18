"""
Admin-only handlers for Alya Bot.

This module contains command handlers that should only be accessible
to bot administrators for management and maintenance.
"""

import logging
import os
from typing import List

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from utils.database import reset_database, init_database

# Setup logger
logger = logging.getLogger(__name__)

# Get admin IDs from environment variable
def get_admin_ids() -> List[int]:
    """Get admin IDs from environment variable.
    
    Returns:
        List of admin user IDs
    """
    try:
        # Get environment variable and split by commas
        admin_ids_str = os.getenv("DEVELOPER_IDS", "")
        
        if not admin_ids_str:
            logger.warning("No DEVELOPER_IDS found in environment variables")
            return []
            
        # Convert string IDs to integers
        admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]
        logger.info(f"Loaded {len(admin_ids)} admin IDs from environment")
        return admin_ids
    except Exception as e:
        logger.error(f"Failed to parse DEVELOPER_IDS: {e}")
        return []

# List of admin user IDs from environment
ADMIN_IDS: List[int] = get_admin_ids()

async def reset_db_command(update: Update, context: CallbackContext) -> None:
    """Admin command to reset the database.
    
    Args:
        update: The update object from Telegram
        context: The callback context
    """
    user = update.effective_user
    user_id = user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Maaf, kamu tidak punya izin untuk melakukan ini 😒")
        return
    
    # Ask for confirmation
    if not context.args or context.args[0] != "confirm":
        await update.message.reply_text(
            "⚠️ *PERINGATAN*: Ini akan menghapus SEMUA data dalam database!\n\n"
            "Untuk konfirmasi, tulis:\n`/reset_db confirm`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Reset database
    success = reset_database()
    
    if success:
        await update.message.reply_text("Database berhasil direset! Semua data telah dibersihkan ✨")
        logger.info(f"Database reset by admin {user_id}")
    else:
        await update.message.reply_text("Gagal reset database. Cek log untuk detail errornya.")
        logger.error(f"Failed database reset attempt by admin {user_id}")
