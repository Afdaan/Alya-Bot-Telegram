import io
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, BinaryIO

from PIL import Image, UnidentifiedImageError
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from core.persona import PersonaManager
from core.gemini_client import GeminiClient
from database.database_manager import db_manager, get_user_lang
from handlers.response.system import get_system_error_response

logger = logging.getLogger(__name__)


class MediaAnalyzer:
    """Handles media analysis operations using Gemini API."""

    def __init__(self, gemini_client: GeminiClient, persona_manager: PersonaManager) -> None:
        self.gemini_client = gemini_client
        self.persona_manager = persona_manager
        self.db_manager = db_manager

    async def analyze_media(
        self,
        media_content: Union[str, bytes, BinaryIO, bytearray],
        media_type: str,
        query: str,
        user_id: int,
    ) -> str:
        """
        Analyzes media content using Gemini and returns a formatted response.

        Args:
            media_content: The content of the media to analyze.
            media_type: The type of media ('image', 'document', 'text').
            query: The user's query about the media.
            user_id: The ID of the user requesting the analysis.

        Returns:
            A string containing the analysis result.
        """
        lang = get_user_lang(user_id, self.db_manager)
        
        try:
            # For images, we need to get the content description first
            if media_type in ("image", "photo"):
                image = self._to_pil_image(media_content)
                # This is a simplified call to get a description.
                # In a real scenario, you might have a specific prompt for just description.
                media_context = await self.gemini_client.generate_response(
                    user_id=user_id,
                    username="User", # Username is not critical for this part
                    message="Describe this image.",
                    context="",
                    relationship_level=0,
                    is_admin=False,
                    lang=lang,
                    is_media_analysis=True,
                    media_context=image # Pass the image object directly if supported
                )
            elif media_type == "document":
                media_context = self._to_text(media_content, media_type)
            elif media_type == "text":
                media_context = str(media_content)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            # Now, generate the final response based on the user's query and the extracted context
            analysis_result = await self.gemini_client.generate_response(
                user_id=user_id,
                username="User", # Or fetch the real username
                message=query,
                context="", # No prior chat context needed for one-off analysis
                relationship_level=0,
                is_admin=False,
                lang=lang,
                is_media_analysis=True,
                media_context=media_context
            )

            if not analysis_result:
                raise ValueError("API returned an empty response.")

            return analysis_result

        except Exception as e:
            logger.error(f"Error analyzing {media_type} for user {user_id}: {e}", exc_info=True)
            return get_system_error_response(lang)

    def _to_pil_image(self, media_content: Union[bytes, BinaryIO, bytearray]) -> Image.Image:
        """Converts binary media content to a PIL Image."""
        try:
            image_stream = io.BytesIO(media_content)
            return Image.open(image_stream)
        except UnidentifiedImageError:
            logger.error("Cannot identify image file.")
            raise ValueError("Invalid or unsupported image format.")
        except Exception as e:
            logger.error(f"Error converting to PIL image: {e}")
            raise

    def _to_text(self, media_content: Union[bytes, BinaryIO, bytearray], media_type: str) -> str:
        """A placeholder to convert document content to text."""
        # In a real implementation, you would use libraries like PyPDF2 for PDFs
        # or python-docx for DOCX files to extract text.
        logger.warning(f"Text extraction for '{media_type}' is a placeholder.")
        try:
            if isinstance(media_content, (bytes, bytearray)):
                # Attempt to decode as UTF-8, with fallbacks.
                return media_content.decode('utf-8', errors='replace')
            elif hasattr(media_content, 'read'):
                # If it's a file-like object
                content_bytes = media_content.read()
                return content_bytes.decode('utf-8', errors='replace')
            return "Document content extraction is not fully implemented."
        except Exception as e:
            logger.error(f"Error extracting text from document: {e}")
            return "Failed to extract text from the document."

    @staticmethod
    async def handle_analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Static method to handle the command from the handler."""
        user = update.effective_user
        message = update.effective_message
        
        # This check is important to ensure the instances are created and available
        if "gemini_client" not in context.bot_data or "persona_manager" not in context.bot_data:
            logger.error("GeminiClient or PersonaManager not found in bot_data")
            await message.reply_html("Sorry, the analysis service is not configured correctly.")
            return
            
        analyzer = MediaAnalyzer(context.bot_data["gemini_client"], context.bot_data["persona_manager"])
        
        media_content = None
        media_type = None
        
        if message.photo:
            media_content_file = await message.photo[-1].get_file()
            media_content_bytes = await media_content_file.download_as_bytearray()
            media_content = bytes(media_content_bytes)
            media_type = "image"
        elif message.document:
            media_content_file = await message.document.get_file()
            media_content_bytes = await media_content_file.download_as_bytearray()
            media_content = bytes(media_content_bytes)
            media_type = "document"
        elif message.text and "!ask" in message.text:
            media_content = message.text.replace("!ask", "").strip()
            media_type = "text"
        
        query = " ".join(context.args) if context.args else (message.caption or "").replace("!ask", "").strip()
        if not query and media_type != "text":
            # If there's no specific question for media, use a default one.
            lang = get_user_lang(user.id, db_manager)
            query = "Analyze this for me, please." if lang == 'en' else "Tolong analisis ini."

        if not media_content:
            lang = get_user_lang(user.id, db_manager)
            await message.reply_html(get_system_error_response(lang, error_type="no_media"))
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        try:
            result = await analyzer.analyze_media(
                media_content=media_content,
                media_type=media_type,
                query=query,
                user_id=user.id
            )
            await message.reply_html(result)
        except Exception as e:
            logger.error(f"Failed to handle analysis command for user {user.id}: {e}", exc_info=True)
            lang = get_user_lang(user.id, db_manager)
            await message.reply_html(get_system_error_response(lang))
