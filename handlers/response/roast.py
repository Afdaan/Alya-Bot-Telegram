"""
Roast command handler for Alya Bot.
"""
import logging
import random
import os
import re
from typing import List, Dict, Any, Optional
import yaml

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config.settings import ADMIN_IDS, PERSONA_DIR
from core.gemini_client import GeminiClient
from core.persona import PersonaManager
from core.database import DatabaseManager
from utils.formatters import format_response

logger = logging.getLogger(__name__)

class RoastHandler:
    """Handler for roast commands (!roast, !gitroast)."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        persona_manager: PersonaManager,
        db_manager: DatabaseManager
    ) -> None:
        """Initialize the roast handler.
        
        Args:
            gemini_client: Gemini client for AI generation
            persona_manager: Persona manager for response formatting
            db_manager: Database manager for user operations
        """
        self.gemini = gemini_client
        self.persona = persona_manager
        self.db = db_manager
        self.roast_data = self._load_roast_data()
        
    def _load_roast_data(self) -> Dict[str, Any]:
        """Load roast data from YAML file.
        
        Returns:
            Dictionary with roast data
        """
        try:
            roast_path = os.path.join(PERSONA_DIR, "roast.yml")
            if os.path.exists(roast_path):
                with open(roast_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    logger.info("Loaded roast data from YAML")
                    return data
            else:
                logger.warning(f"Roast file not found at {roast_path}")
                return self._get_default_roast_data()
        except Exception as e:
            logger.error(f"Error loading roast data: {e}")
            return self._get_default_roast_data()
    
    def _get_default_roast_data(self) -> Dict[str, Any]:
        """Get default roast data if YAML file is not found.
        
        Returns:
            Default roast data dictionary
        """
        return {
            "prompts": {
                "general": "Roast the user with savage but funny insults. Be creative and ruthless.",
                "github": "Roast the user's GitHub profile with savage but funny insults about their code quality, commit history, and project choices."
            },
            "templates": {
                "prefix": [
                    "Baiklah, {username}-kun, Alya akan memanggang kamu...",
                    "Hmph! Alya punya sesuatu untuk {username}-kun yang sok keren ini...",
                    "{username}-kun, bersiaplah untuk kebenaran yang menyakitkan..."
                ],
                "suffix": [
                    "Fufu~ Jangan tersinggung ya {username}-kun, ini hanya untuk hiburan~",
                    "A-Alya hanya bercanda... jangan diambil hati ya... M-Mungkin.",
                    "Hm... hanya orang kuat yang bisa menerima roast dari wakil ketua OSIS."
                ]
            },
            "emotions": {
                "roasting": {
                    "expressions": [
                        "menyeringai nakal",
                        "memasang wajah meremehkan",
                        "tersenyum mengejek"
                    ],
                    "emoji": ["😏", "😈", "💢", "🔥"],
                    "responses": [
                        "Hmph! {username}-kun memang pantas mendapatkannya!",
                        "A-Alya tidak bermaksud kasar... tapi {username}-kun memang seperti itu."
                    ]
                }
            },
            "examples": {
                "general": [
                    "Alya pikir kemampuan sosial {username}-kun sebanding dengan kemampuan matematikanya... yaitu NOL BESAR.",
                    "Jika kegagalan adalah seni, {username}-kun pasti seniman terhebat sepanjang masa."
                ],
                "github": [
                    "Repository GitHub {username}-kun seperti museum... tempat menyimpan barang-barang usang yang tidak ada yang peduli.",
                    "Commit history {username}-kun lebih berantakan daripada kamarnya..."
                ]
            }
        }
        
    def get_handlers(self) -> List:
        """Get all roast command handlers.
        
        Returns:
            List of handlers for the dispatcher
        """
        return [
            MessageHandler(filters.Regex(r"^!roast\b"), self.roast_command),
            MessageHandler(filters.Regex(r"^!gitroast\b"), self.git_roast_command)
        ]
        
    async def roast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle !roast command.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        message_text = update.message.text
        
        # Extract target with improved context awareness
        # Look for @ mentions, text after space, or quotes
        target = self._extract_roast_target(message_text)
        
        # If no specific target found, fallback to command sender
        if not target:
            target = user.first_name
        
        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        try:
            # Track command use
            self.db.track_command_use(user.id)
            
            # Get templates dictionary first
            templates = self.roast_data.get("templates", {})
            
            # Now access prefix and suffix safely
            prefix_templates = templates.get("prefix", [])
            suffix_templates = templates.get("suffix", [])
            
            # Safely get a random template
            prefix = random.choice(prefix_templates) if prefix_templates else "Alya akan memanggang {target}..."
            suffix = random.choice(suffix_templates) if suffix_templates else "Let me cook🔥🔥🔥💀💀💀, {target}~"
            
            # Format prefix with target name, not username of command sender
            prefix = prefix.format(target=target)
            suffix = suffix.format(target=target)
            
            # Create roast prompt from updated structure - pass both command sender and target
            prompt_template = self.roast_data.get("roast_prompt_templates", {}).get("personal", "")
            if not prompt_template:
                prompt = self.roast_data.get("prompts", {}).get("general", "Roast the user with savage but funny insults.")
            else:
                prompt = prompt_template.format(name=target)
            
            # Generate roast with Gemini - enhanced prompt with clearer context
            full_prompt = (
                f"Target to roast: {target}\n"
                f"Prompt: {prompt}\n\n"
                "Generate an extremely funny yet savage roast in Bahasa Indonesia. "
                "Make it sound like something a tsundere anime girl would say. "
                "Use common Indonesian slang when appropriate. "
                "Make it LONGER (3-4 sentences) and VERY BRUTAL. "
                "Use HTML tags like <b>bold</b>, <i>italic</i>. "
                "Target insults specifically at the target's characteristics. "
                "Include a brutal roleplay action in parentheses () about your reaction to the target. "
                "DO NOT include any disclaimers or warnings - stay in character 100% of the time. "
                "Do not explain this is fictional. Do not apologize for the roast."
            )
            
            # Generate roast
            response = await self.gemini.generate_content(
                user_input=full_prompt,
                system_prompt="You are Alya in toxic savage form. Generate an extremely brutal and offensive roast in Bahasa Indonesia. No disclaimers, no breaking character, no apologies. Pure toxicity.",
                history=None,
                safe_mode=False  # Allow roasting content
            )
            
            if response:
                # Process the response to properly format HTML and remove any disclaimers
                processed_response = self._process_roast_response(response)
                
                # Format with prefix and suffix
                full_response = f"{prefix}\n\n{processed_response}\n\n{suffix}"
                
                # Send formatted response with proper context
                formatted_response = format_response(
                    full_response,
                    mood="roasting",
                    emotion="anger",
                    intensity=0.9,
                    username=user.first_name,
                    target_name=target,
                    persona_name="waifu"
                )
                
                await update.message.reply_html(formatted_response)
            else:
                # Use personal templates as fallback
                personal_templates = self.roast_data.get("personal_templates", [])
                if personal_templates:
                    roast = random.choice(personal_templates).format(name=target)
                    full_response = f"{prefix}\n\n{roast}\n\n{suffix}"
                    
                    formatted_response = format_response(
                        full_response,
                        mood="roasting",
                        emotion="anger",
                        intensity=0.9,
                        username=user.first_name,
                        target_name=target,
                        persona_name="waifu"
                    )
                    
                    await update.message.reply_html(formatted_response)
                else:
                    # Ultimate fallback
                    await update.message.reply_html(
                        "<i>melihat dengan kesal</i>\n\n"
                        f"Maaf {user.first_name}-kun, Alya sedang tidak mood untuk memanggang {target} saat ini. "
                        "Mungkin Alya akan lebih terinspirasi nanti... 😏"
                    )
        except Exception as e:
            logger.error(f"Error in roast command: {e}")
            await update.message.reply_html(
                "<i>terlihat bingung</i>\n\n"
                f"G-gomen {user.first_name}-kun! Alya tidak bisa memanggang {target} saat ini... "
                "Ada sesuatu yang salah dengan mode toxic Alya... 😳"
            )
    
    def _extract_roast_target(self, message_text: str) -> str:
        """Extract the target for roasting from message text.
        
        Args:
            message_text: Original message text
            
        Returns:
            Extracted target name or text
        """
        # Remove the command itself
        text_without_command = message_text.split(' ', 1)
        if len(text_without_command) < 2:
            return ""
            
        target_text = text_without_command[1].strip()
        
        # Check for @username mentions
        username_match = re.search(r'@(\w+)', target_text)
        if username_match:
            return f"@{username_match.group(1)}"
            
        # Check for quoted targets like "John Doe"
        quoted_match = re.search(r'"([^"]+)"', target_text)
        if quoted_match:
            return quoted_match.group(1)
            
        # Just return everything after the command
        return target_text
    
    def _process_roast_response(self, response: str) -> str:
        """Process and format a roast response to ensure proper HTML formatting.
        
        Args:
            response: Raw response from Gemini
            
        Returns:
            Processed response with proper HTML formatting
        """
        # Basic HTML formatting
        processed = response
        
        # Replace *text* with <b>text</b> (bold) if not already using HTML tags
        if "<b>" not in processed:
            processed = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', processed)
        
        # Replace _text_ with <i>text</i> (italic) if not already using HTML tags
        if "<i>" not in processed:
            processed = re.sub(r'_([^_]+)_', r'<i>\1</i>', processed)
        
        # Make sure roleplay actions are in italic
        processed = re.sub(r'\(([^)]+)\)', r'<i>(\1)</i>', processed)
        
        # Ensure CAPS words are properly emphasized if not already bold
        processed = re.sub(r'\b([A-Z]{3,})\b(?![^<]*>)', r'<b>\1</b>', processed)
        
        # Remove any disclaimer paragraphs
        disclaimer_patterns = [
            r'\*?\(?Disclaimer:.*?\)?',
            r'\*?\(?Note:.*?\)?',
            r'This is fictional.*?only\.?',
            r'Just for fun.*?only\.?',
            r'This is just a joke.*?',
            r'Please remember.*?',
            r'Please don\'t take.*?',
        ]
        
        for pattern in disclaimer_patterns:
            processed = re.sub(pattern, '', processed, flags=re.IGNORECASE | re.DOTALL)
        
        # Add appropriate HTML emoji formatting if needed
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001FAFF"  # Emoji ranges
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        
        # Group emojis together and ensure there are enough
        emojis = emoji_pattern.findall(processed)
        if len(emojis) < 3:  # We want at least 3 emojis
            # Add more toxic emojis from our collection
            toxic_emojis = ["🤮", "💀", "🤡", "🗑️", "💩", "🖕", "😤", "🙄", "💅", "🤢"]
            extra_emojis = random.sample(toxic_emojis, min(3, len(toxic_emojis)))
            processed += " " + "".join(extra_emojis)
        
        return processed
    
    async def git_roast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle !gitroast command for GitHub roasting.
        
        Args:
            update: The update from Telegram
            context: The callback context
        """
        user = update.effective_user
        message_text = update.message.text
        
        # Extract GitHub username if specified
        parts = message_text.split(' ', 1)
        github_user = parts[1].strip() if len(parts) > 1 else None
        
        if not github_user:
            await update.message.reply_html(
                "<i>melihat dengan kesal</i>\n\n"
                f"{user.first_name}-kun, Alya butuh username GitHub untuk diroast! "
                "Contoh: !gitroast afdaanb"
            )
            return
        
        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        try:
            # Track command use
            self.db.track_command_use(user.id)
            
            # Get templates dictionary first
            templates = self.roast_data.get("templates", {})
            
            # Now access prefix and suffix safely
            prefix_templates = templates.get("prefix", [])
            suffix_templates = templates.get("suffix", [])
            
            # Safely get a random template
            prefix = random.choice(prefix_templates) if prefix_templates else "Alya akan memanggangmu, {username}-kun..."
            suffix = random.choice(suffix_templates) if suffix_templates else "Jangan tersinggung ya, {username}-kun~"
            
            # Format prefix with username
            prefix = prefix.format(username=user.first_name)
            suffix = suffix.format(username=user.first_name)
            
            # Create git roast prompt from updated structure
            prompt_template = self.roast_data.get("roast_prompt_templates", {}).get("github", "")
            if not prompt_template:
                prompt = self.roast_data.get("prompts", {}).get("github", "Roast the GitHub profile with savage insults.")
            else:
                prompt = prompt_template.format(github_repo=github_user)
            
            # Generate roast with Gemini
            full_prompt = (
                f"GitHub Username: {github_user}\n"
                f"Prompt: {prompt}\n\n"
                "Generate an extremely funny yet savage roast about this GitHub user in Bahasa Indonesia. "
                "Make it sound like something a tsundere anime girl who understands programming would say. "
                "Include programming jokes and GitHub-specific humor. "
                "Keep it PG-13 but ruthless. Use common Indonesian slang when appropriate. "
                "Keep it short and impactful - maximum 3 sentences."
            )
            
            # Generate roast
            response = await self.gemini.generate_content(
                user_input=full_prompt,
                system_prompt="You are Alya, a tsundere anime girl who knows programming. Generate a savage but hilarious GitHub-related roast in Bahasa Indonesia.",
                history=None,
                safe_mode=False  # Allow roasting content
            )
            
            if response:
                # Format with prefix and suffix
                full_response = f"{prefix}\n\n{response}\n\n{suffix}"
                
                # Send formatted response
                formatted_response = format_response(
                    full_response,
                    mood="roasting",
                    emotion="anger",
                    intensity=0.8,
                    username=user.first_name,
                    persona_name="waifu"
                )
                
                await update.message.reply_html(formatted_response)
            else:
                # If Gemini fails, use a pre-written example
                github_templates = self.roast_data.get("github_templates", [])
                if github_templates:
                    example_roast = random.choice(github_templates).format(github_repo=github_user)
                    full_response = f"{prefix}\n\n{example_roast}\n\n{suffix}"
                    
                    # Send formatted response
                    formatted_response = format_response(
                        full_response,
                        mood="roasting",
                        emotion="anger",
                        intensity=0.9,
                        username=user.first_name,
                        persona_name="waifu"
                    )
                    
                    await update.message.reply_html(formatted_response)
                else:
                    # Use examples as fallback
                    examples = self.roast_data.get("examples", {}).get("github", [])
                    if examples:
                        git_roast = random.choice(examples).format(username=github_user)
                        full_response = f"{prefix}\n\n{git_roast}\n\n{suffix}"
                        
                        formatted_response = format_response(
                            full_response,
                            mood="roasting", 
                            emotion="anger",
                            intensity=0.8,
                            username=user.first_name,
                            persona_name="waifu"
                        )
                        
                        await update.message.reply_html(formatted_response)
                    else:
                        await update.message.reply_html(
                            "<i>terlihat bingung</i>\n\n"
                            f"G-gomen {user.first_name}-kun! Alya tidak bisa memanggang GitHub saat ini... "
                            "Mungkin repository-nya private? 😳"
                        )
                
        except Exception as e:
            logger.error(f"Error in gitroast command: {e}")
            await update.message.reply_html(
                "<i>terlihat bingung</i>\n\n"
                f"G-gomen {user.first_name}-kun! Alya tidak bisa memanggang GitHub saat ini... "
                "Mungkin repository-nya private? 😳"
            )
