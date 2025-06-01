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

logger = logging.getLogger(__name__)


class MediaAnalyzer:
    """Handles media analysis operations using Gemini API."""

    def __init__(self, gemini_client: GeminiClient, persona_manager: PersonaManager) -> None:
        self.gemini_client = gemini_client
        self.persona_manager = persona_manager

    async def analyze_media(
        self,
        media_content: Union[str, bytes, BinaryIO, bytearray],
        media_type: str,
        persona: str = "analyze",
    ) -> Dict[str, Any]:
        persona_data = self.persona_manager.get_persona(persona) or \
            self.persona_manager.get_persona("analyze")
        if not persona_data or "analysis_template" not in persona_data:
            logger.error("Missing analysis template in persona configuration")
            raise ValueError(f"Missing analysis template for persona '{persona}'")

        analysis_template = self._select_template(persona_data, media_type)
        try:
            if media_type == "text":
                system_prompt = (
                    f"Kamu adalah Alya menganalisis teks. {analysis_template}\n\n"
                    "FORMAT PENTING: Pastikan responsmu konsisten dengan format berikut:\n"
                    "1. Gunakan heading yang jelas untuk setiap bagian analisis\n"
                    "2. Beri jarak antar paragraf agar mudah dibaca\n"
                    "3. Batasi emoji maksimal 2 buah dan tempatkan di posisi strategis\n"
                    "4. Ringkas poin-poin dalam format bullet point dengan tanda •\n"
                    "5. Akhiri dengan insight atau kesimpulan singkat (1-2 kalimat)"
                )
                analysis_result = await self.gemini_client.generate_content(
                    media_content, system_prompt=system_prompt
                )
            elif media_type in ("image", "photo", "png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"):
                system_prompt = (
                    f"Kamu adalah Alya menganalisis gambar. {analysis_template}\n\n"
                    "FORMAT PENTING: Responsmu harus terstruktur dengan format berikut:\n"
                    "<b>Deskripsi Gambar:</b>\n"
                    "[Deskripsi 2-3 kalimat]\n\n"
                    "<b>Detail yang Terlihat:</b>\n"
                    "• [Detail 1]\n"
                    "• [Detail 2]\n"
                    "• [Detail 3]\n\n"
                    "<b>Kesan & Analisis:</b>\n"
                    "[Analisis 2-3 kalimat dengan sentuhan tsundere Alya]\n\n"
                    "Gunakan maksimal 2 emoji di posisi yang tepat."
                )
                image = self._to_pil_image(media_content)
                analysis_result = await self.gemini_client.generate_content(
                    image, system_prompt=system_prompt
                )
            elif media_type in ("document", "pdf", "doc", "docx"):
                system_prompt = (
                    f"Kamu adalah Alya menganalisis dokumen {media_type}. {analysis_template}\n\n"
                    "FORMAT PENTING: Responsmu harus mengikuti struktur berikut:\n"
                    "<b>Tema Dokumen:</b> [Tema dokumen]\n\n"
                    "<b>Ringkasan:</b>\n"
                    "[Ringkasan singkat 2-3 kalimat]\n\n"
                    "<b>Poin Penting:</b>\n"
                    "• [Poin 1]\n"
                    "• [Poin 2]\n"
                    "• [Poin 3]\n\n"
                    "<b>Kesimpulan:</b>\n"
                    "[Kesimpulan singkat dengan sentuhan tsundere Alya]"
                )
                text_content = self._to_text(media_content, media_type)
                analysis_result = await self.gemini_client.generate_content(
                    text_content, system_prompt=system_prompt
                )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            if not analysis_result:
                raise ValueError("Tidak dapat menganalisis media, API mengembalikan respons kosong")

            formatted_result = self._post_process_analysis(analysis_result, media_type)
            return {"summary": formatted_result}
        except Exception as e:
            logger.error(f"Error analyzing {media_type} content: {str(e)}", exc_info=True)
            raise

    def _select_template(self, persona_data: Dict[str, Any], media_type: str) -> str:
        if media_type == "text" and "text_analysis_template" in persona_data:
            return persona_data["text_analysis_template"]
        if media_type in ("image", "photo") and "image_analysis_template" in persona_data:
            return persona_data["image_analysis_template"]
        if media_type in ("document", "pdf", "doc", "docx") and "document_analysis_template" in persona_data:
            return persona_data["document_analysis_template"]
        return persona_data["analysis_template"]

    def _to_pil_image(self, media_content: Union[bytes, bytearray, BinaryIO]) -> Image.Image:
        try:
            if isinstance(media_content, bytearray):
                media_content = bytes(media_content)
            if isinstance(media_content, bytes):
                image = Image.open(io.BytesIO(media_content))
                image.load()
                if image.mode not in ["RGB", "RGBA"]:
                    image = image.convert("RGB")
                return image
            raise ValueError("Unsupported image format")
        except UnidentifiedImageError:
            raise ValueError("File bukan format gambar yang valid")
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            raise ValueError(f"Gagal memproses gambar: {str(e)}")

    def _to_text(self, media_content: Union[str, bytes, bytearray], media_type: str) -> str:
        if isinstance(media_content, str):
            return media_content
        try:
            if isinstance(media_content, bytearray):
                media_content = bytes(media_content)
            return media_content.decode('utf-8', errors='ignore')
        except Exception:
            return f"[Dokumen {media_type} tidak dapat dikonversi ke teks]"

    def _post_process_analysis(self, text: str, media_type: str) -> str:
        if "<b>" in text or "<i>" in text:
            return text
        if media_type == "text":
            return f"<b>Analisis Teks:</b>\n\n{text}"
        if media_type in ("image", "photo", "png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"):
            return f"<b>Analisis Gambar:</b>\n\n{text}"
        if media_type in ("document", "pdf", "doc", "docx"):
            return f"<b>Analisis Dokumen {media_type.upper()}:</b>\n\n{text}"
        return text

    @classmethod
    async def handle_analysis_command(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        username = user.first_name or "user"
        message = update.message

        gemini_client = context.bot_data.get("gemini_client")
        persona_manager = context.bot_data.get("persona_manager")
        if not gemini_client or not persona_manager:
            await message.reply_text(
                "Maaf, Alya sedang mengalami gangguan sistem... 😔",
                reply_to_message_id=message.message_id
            )
            return

        analyzer = cls(gemini_client, persona_manager)
        persona = "analyze"
        if context.args and context.args[0] in ["waifu", "roast", "academic"]:
            persona = context.args[0]
            context.args = context.args[1:]

        try:
            await cls._send_typing_action(update, context)
            result = await cls._process_media_content(update, context, analyzer, persona)
            from utils.formatters import format_response

            if not result or not result.get("summary"):
                if update.effective_chat.type in ["group", "supergroup"] and not context.args:
                    from handlers.response.analyze import analyze_response
                    await message.reply_html(
                        analyze_response(),
                        reply_to_message_id=message.message_id
                    )
                    return
                await message.reply_text(
                    f"Maaf {username}-kun, Alya tidak bisa menganalisis media ini... 😔",
                    reply_to_message_id=message.message_id
                )
                return

            summary = result.get("summary", "Analisis tidak tersedia")
            formatted_response = format_response(
                str(summary),
                username=username,
                emotion="academic_serious",
                mood="academic_serious"
            )
            await message.reply_html(formatted_response, reply_to_message_id=message.message_id)
        except ValueError as e:
            await message.reply_text(
                f"Maaf {username}-kun, {str(e)} 😔",
                reply_to_message_id=message.message_id
            )
        except Exception as e:
            logger.error(f"Error in media analysis: {str(e)}", exc_info=True)
            await message.reply_text(
                f"Маленькая ошибка! Alya tidak bisa menganalisis media ini... 😔\n\n"
                f"Detail error: {str(e)[:100]}...",
                reply_to_message_id=message.message_id
            )

    @staticmethod
    async def _send_typing_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        try:
            if getattr(message, "message_thread_id", None):
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.TYPING,
                    message_thread_id=message.message_thread_id
                )
            else:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.TYPING
                )
        except Exception as e:
            logger.warning(f"Failed to send typing action: {e}")

    @staticmethod
    async def _process_media_content(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        analyzer: "MediaAnalyzer",
        persona: str
    ) -> Optional[Dict[str, Any]]:
        message = update.message

        # 1. Direct photo
        if message.photo:
            photo_file = await context.bot.get_file(message.photo[-1].file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            return await analyzer.analyze_media(photo_bytes, "image", persona)

        # 2. Direct document
        if message.document:
            document = message.document
            doc_file = await context.bot.get_file(document.file_id)
            doc_bytes = await doc_file.download_as_bytearray()
            if document.mime_type and document.mime_type.startswith('image/'):
                return await analyzer.analyze_media(doc_bytes, "image", persona)
            file_ext = Path(document.file_name).suffix.lower()[1:] if document.file_name else ""
            media_type = file_ext if file_ext in ["pdf", "doc", "docx"] else "document"
            return await analyzer.analyze_media(doc_bytes, media_type, persona)

        # 3. Reply to photo/document
        reply = getattr(message, "reply_to_message", None)
        if reply:
            if reply.photo:
                photo = reply.photo[-1]
                photo_file = await context.bot.get_file(photo.file_id)
                photo_bytes = await photo_file.download_as_bytearray()
                return await analyzer.analyze_media(photo_bytes, "image", persona)
            if reply.document:
                document = reply.document
                doc_file = await context.bot.get_file(document.file_id)
                doc_bytes = await doc_file.download_as_bytearray()
                if document.mime_type and document.mime_type.startswith('image/'):
                    return await analyzer.analyze_media(doc_bytes, "image", persona)
                file_ext = Path(document.file_name).suffix.lower()[1:] if document.file_name else ""
                media_type = file_ext if file_ext in ["pdf", "doc", "docx"] else "document"
                return await analyzer.analyze_media(doc_bytes, media_type, persona)

        # 4. Text command
        if context.args:
            text_content = " ".join(context.args)
            return await analyzer.analyze_media(text_content, "text", persona)

        return None
