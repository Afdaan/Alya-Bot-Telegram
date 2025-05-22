"""
Media Message Handlers for Alya Bot.

This module handles various media types sent to the bot, including
photos, documents, audio, and video files.
"""

import logging
from typing import Optional, List, Dict, Any

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

logger = logging.getLogger(__name__)

