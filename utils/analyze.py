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
        lang = get_user_lang(user_id)
        
        try:
            # For images, we need to get the content description first
            if media_type in ("image", "photo"):
                image = self._to_pil_image(media_content)
                # Prepare image description message based on language
                describe_message = "Describe this image in detail." if lang == 'en' else "Deskripsikan gambar ini secara detail."
                media_context = await self.gemini_client.generate_response(
                    user_id=user_id,
                    username="User", # Username is not critical for this part
                    message=describe_message,
                    context="",
                    relationship_level=0,
                    is_admin=False,
                    lang=lang,
                    is_media_analysis=True,
                    media_context=image # Pass the image object directly if supported
                )
                logger.debug(f"Image analysis completed for user {user_id}, context length: {len(media_context)}")
                
            elif media_type == "document":
                # Try to extract text from document
                extracted_text = self._to_text(media_content, media_type)
                
                # If extraction was successful (not a placeholder message)
                if extracted_text and not extracted_text.startswith("Document"):
                    media_context = extracted_text
                    logger.info(f"Successfully extracted {len(extracted_text)} chars from document for user {user_id}")
                else:
                    # For binary documents (PDF, DOCX), try to get OCR/description from Gemini
                    # Note: This requires Gemini File API or converting doc to image
                    logger.info(f"Binary document detected for user {user_id}, attempting image-based analysis")
                    try:
                        # Try to treat document as image (some formats like PDF first page)
                        image = self._to_pil_image(media_content)
                        describe_message = "Extract and describe the content of this document." if lang == 'en' else "Ekstrak dan deskripsikan isi dokumen ini."
                        media_context = await self.gemini_client.generate_response(
                            user_id=user_id,
                            username="User",
                            message=describe_message,
                            context="",
                            relationship_level=0,
                            is_admin=False,
                            lang=lang,
                            is_media_analysis=True,
                            media_context=image
                        )
                        logger.debug(f"Document image analysis completed for user {user_id}")
                    except Exception as img_error:
                        # If image conversion fails, use extracted text even if it's a placeholder
                        logger.warning(f"Could not process document as image for user {user_id}: {img_error}")
                        media_context = extracted_text
                        
            elif media_type == "text":
                media_context = str(media_content)
                logger.debug(f"Text analysis for user {user_id}, length: {len(media_context)}")
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
        """
        Convert document content to text for analysis.
        
        Note: This currently attempts basic text decoding. For advanced document 
        processing (PDF, DOCX), Gemini's vision API handles the document image directly.
        """
        try:
            if isinstance(media_content, (bytes, bytearray)):
                # Try UTF-8 decode for plain text files
                decoded = media_content.decode('utf-8', errors='replace')
                # If decoded successfully and has readable content, return it
                if decoded.strip() and len(decoded) > 10:
                    logger.debug(f"Successfully decoded {media_type} as text ({len(decoded)} chars)")
                    return decoded
                else:
                    # Empty or very short content - likely binary file
                    logger.debug(f"Document appears to be binary, Gemini will handle via vision API")
                    return "Document content will be analyzed via image processing."
                    
            elif hasattr(media_content, 'read'):
                # If it's a file-like object
                content_bytes = media_content.read()
                return self._to_text(content_bytes, media_type)
            
            # Fallback for unsupported types
            logger.info(f"Using Gemini vision API for {media_type} analysis")
            return "Document will be analyzed using AI vision capabilities."
            
        except UnicodeDecodeError:
            # Binary file (PDF, DOCX, etc.) - let Gemini handle it
            logger.debug(f"Binary {media_type} detected, using Gemini vision API")
            return "Document will be analyzed using AI vision capabilities."
        except Exception as e:
            logger.error(f"Error processing {media_type}: {e}")
            return "Document will be analyzed using AI capabilities."

    @staticmethod
    async def handle_analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Static method to handle the command from the handler."""
        user = update.effective_user
        message = update.effective_message
        
        # This check is important to ensure the instances are created and available
        if "gemini_client" not in context.bot_data or "persona_manager" not in context.bot_data:
            logger.error("GeminiClient or PersonaManager not found in bot_data")
            lang = get_user_lang(user.id)
            await message.reply_html(get_system_error_response(lang))
            return
            
        analyzer = MediaAnalyzer(context.bot_data["gemini_client"], context.bot_data["persona_manager"])
        
        media_content = None
        media_type = None
        query = ""
        
        # Check if this is a reply to message with media
        if message.reply_to_message:
            replied_message = message.reply_to_message
            if replied_message.photo:
                media_content_file = await replied_message.photo[-1].get_file()
                media_content_bytes = await media_content_file.download_as_bytearray()
                media_content = bytes(media_content_bytes)
                media_type = "image"
            elif replied_message.document:
                media_content_file = await replied_message.document.get_file()
                media_content_bytes = await media_content_file.download_as_bytearray()
                media_content = bytes(media_content_bytes)
                media_type = "document"
            # Extract query from the reply text
            query = message.text.replace("!ask", "").strip() if message.text else ""
        # Check if message itself contains media
        elif message.photo:
            media_content_file = await message.photo[-1].get_file()
            media_content_bytes = await media_content_file.download_as_bytearray()
            media_content = bytes(media_content_bytes)
            media_type = "image"
            # Extract query from caption
            query = (message.caption or "").replace("!ask", "").strip()
        elif message.document:
            media_content_file = await message.document.get_file()
            media_content_bytes = await media_content_file.download_as_bytearray()
            media_content = bytes(media_content_bytes)
            media_type = "document"
            # Extract query from caption
            query = (message.caption or "").replace("!ask", "").strip()
        # Plain text query
        elif message.text and "!ask" in message.text:
            media_content = message.text.replace("!ask", "").strip()
            media_type = "text"
            query = media_content  # For text analysis, content and query are the same
        
        # If no media content found, show usage
        if not media_content:
            lang = get_user_lang(user.id)
            from handlers.response.analyze import analyze_response
            await message.reply_html(analyze_response(lang))
            return
        
        # If no query specified for media, use default
        if not query and media_type != "text":
            lang = get_user_lang(user.id)
            query = "Analyze this for me, please." if lang == 'en' else "Tolong analisis ini."

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        try:
            result = await analyzer.analyze_media(
                media_content=media_content,
                media_type=media_type,
                query=query,
                user_id=user.id
            )
            # Use analysis formatter for informative responses (not persona conversation)
            from utils.analysis_formatter import format_analysis_response
            lang = get_user_lang(user.id)
            formatted_result = format_analysis_response(
                text=result,
                lang=lang,
                username=user.first_name
            )
            
            # Handle if result is a list (long message split)
            if isinstance(formatted_result, list):
                for part in formatted_result:
                    await message.reply_html(part, disable_web_page_preview=True)
            else:
                await message.reply_html(formatted_result, disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to handle analysis command for user {user.id}: {e}", exc_info=True)
            lang = get_user_lang(user.id)
            await message.reply_html(get_system_error_response(lang))
