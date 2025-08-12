"""
Roast Mode Handlers for Alya Telegram Bot.

This module provides handlers for sassy, playful roasts of users.
"""

import re
import logging
import random
import os
from typing import Dict, List, Any, Optional, Tuple

from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import CallbackContext, MessageHandler, filters

from core.gemini_client import GeminiClient
from utils.formatters import escape_markdown_v2
from core.persona import PersonaManager
from database.database_manager import db_manager, get_user_lang, DatabaseManager
from handlers.response.roast import get_roast_response, get_usage_response

# Need to import time here for rate limiter
import time
import yaml
import aiohttp

# Setup logger
logger = logging.getLogger(__name__)

# Rate limiter for Gemini API calls to avoid overloading
class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, rate: float = 1, per: float = 5.0, burst_limit: int = 2):
        """Initialize rate limiter.
        
        Args:
            rate: Requests per time period
            per: Time period in seconds
            burst_limit: Maximum allowed requests in a burst
        """
        self.rate = rate
        self.per = per
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.updated_at = 0
    
    async def acquire_with_feedback(self, user_id: int) -> Tuple[bool, float]:
        """Check if request is allowed and return feedback.
        
        Args:
            user_id: User ID for tracking (currently unused)
            
        Returns:
            Tuple of (is_allowed, wait_time)
        """
        now = time.time()
        
        # Add tokens based on time passed
        time_passed = now - self.updated_at
        self.tokens = min(self.burst_limit, self.tokens + time_passed * (self.rate / self.per))
        self.updated_at = now
        
        # Check if we have enough tokens
        if self.tokens >= 1:
            self.tokens -= 1
            return True, 0
        
        # Calculate wait time until next token is available
        wait_time = (1 - self.tokens) * self.per / self.rate
        return False, wait_time

class RoastHandler:
    """Handler for generating personalized roasts with different themes.
    
    This class manages all roast-related functionality including personal roasts,
    technical/GitHub roasts, and template management from YAML configuration.
    """
    
    # Load roast templates from YAML config
    ROAST_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    "config", "persona", "roast.yml")
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        persona_manager: PersonaManager,
        db_manager: Optional[DatabaseManager] = None
    ) -> None:
        """Initialize the RoastHandler with templates from configuration.
        
        Args:
            gemini_client: Gemini client for AI generation
            persona_manager: Persona manager for response formatting
            db_manager: Optional database manager for user operations
        """
        self.gemini = gemini_client
        self.persona = persona_manager
        self.db = db_manager
        self.rate_limiter = RateLimiter()
        
        try:
            with open(self.ROAST_CONFIG_PATH, "r", encoding="utf-8") as f:
                self.roast_config = yaml.safe_load(f)
                self.roast_templates = self.roast_config.get("roast_templates", {})
                self.git_roast_templates = self.roast_config.get("git_roast_templates", {})
                logger.info("Roast templates loaded successfully")
        except FileNotFoundError:
            logger.error(f"Roast config not found at {self.ROAST_CONFIG_PATH}")
            self.roast_templates = {}
            self.git_roast_templates = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing roast YAML: {e}")
            self.roast_templates = {}
            self.git_roast_templates = {}

    def get_handlers(self) -> List[MessageHandler]:
        """Get all roast-related message handlers."""
        return [
            MessageHandler(filters.Regex(r"^!roast$"), self.handle_personal_roast),
            MessageHandler(filters.Regex(r"^!gitroast\s+"), self.handle_git_roast),
        ]

    async def handle_personal_roast(self, update: Update, context: CallbackContext) -> None:
        """Handle personal roast requests with rate limiting."""
        user = update.effective_user
        lang = get_user_lang(user.id)
        
        allowed, wait_time = await self.rate_limiter.acquire_with_feedback(user.id)
        if not allowed:
            wait_message = (
                f"Heh, sabar dong! Kamu baru aja minta di-roast. Tunggu {wait_time:.1f} detik lagi."
                if lang == 'id'
                else f"Heh, be patient! You just asked for a roast. Wait {wait_time:.1f} more seconds."
            )
            await update.message.reply_text(wait_message)
            return

        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            roast_text = await self._generate_roast(user.first_name, lang)
            response = get_roast_response(lang=lang, roast_text=roast_text)
        except Exception as e:
            logger.error(f"Error generating personal roast for {user.id}: {e}")
            response = get_roast_response(lang=lang, error='api_fail')
            
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

    async def handle_git_roast(self, update: Update, context: CallbackContext) -> None:
        """Handle GitHub profile roasts."""
        user = update.effective_user
        lang = get_user_lang(user.id)
        
        match = re.match(r"^!gitroast\s+([\w-]+)", update.message.text)
        if not match:
            await update.message.reply_text(get_usage_response(lang, 'gitroast'))
            return
        
        github_username = match.group(1)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            github_data = await self._get_github_data(github_username)
            if not github_data:
                response = get_roast_response(lang=lang, error='not_found', username=github_username)
            elif github_data.get("public_repos", 0) == 0 and not github_data.get("recent_activity"):
                response = get_roast_response(lang=lang, error='no_activity', username=github_username)
            else:
                roast_text = await self._generate_git_roast(github_username, github_data, lang)
                response = get_roast_response(lang=lang, roast_text=roast_text, username=github_username)
        
        except Exception as e:
            logger.error(f"Error during git roast for {github_username}: {e}")
            response = get_roast_response(lang=lang, error='generic', username=github_username)
            
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

    async def _generate_roast(self, name: str, lang: str) -> str:
        """Generate a personal roast using Gemini with toxic templates."""
        # Use the proper toxic roast prompt template from YAML
        roast_prompt_template = self.roast_config.get("roast_prompt_template", "")
        
        if roast_prompt_template:
            # Use the main toxic template
            prompt = roast_prompt_template.format(
                target_name=name,
                roast_context="personal roast"
            )
        else:
            # Fallback to basic toxic template if YAML template not found
            if lang == 'id':
                prompt = f"PERSONA: Lu jadi cewek toxic queen jaksel paling savage!\n\nTARGET ROAST: {name}\n\nPERSONALITY WAJIB:\n- Pake bahasa SUPER KASAR dan TOXIC seperti: anjing, tolol, goblok, bangsat, kontol, memek, dll\n- MOSTLY CAPSLOCK untuk kata-kata kasar\n- 4-10 emoji toxic (🤮, 💀, 🤡, 🙄, 💅)\n- Seolah-olah cewek toxic yang membenci target\n- Fokus ke hinaan PERSONAL (IQ rendah, jelek, bau, gak laku, dll)\n\nFORMAT WAJIB:\n1. Kata pembuka kasar: 'NAJIS', 'ANJIR', 'GOBLOK', 'BANGSAT', 'KONTOL'\n2. Hinaan spesifik personal tentang {name}\n3. Tambahan ejekan lainnya yang menyakitkan\n4. Emoji toxic\n\nRULES:\n- WAJIB BAHASA INDONESIA KASAR JAKSEL\n- HARUS TOXIC BANGET dan MENYAKITKAN\n- FOKUS KE HINAAN PERSONAL, BUKAN CODING\n- Jangan terlalu panjang (max 300 karakter)\n- Usahakan bikin seolah-olah cewek toxic yang ngomong!"
            else:
                prompt = f"PERSONA: Alya-chan is now in SUPER TOXIC MODE! Acting like an extremely toxic Indonesian jaksel girl!\n\nTARGET: {name}\n\nRULES & FORMAT:\n- Use LOTS OF Indonesian swear words (anjing, tolol, babi, goblok, kontol, bangsat, etc.)\n- Use partial CAPS LOCK for emphasis\n- Add PERSONAL insults (ugly, dumb, smelly, never getting laid, etc.)\n- Include toxic emojis (🤮, 💀, 🤡, 💅)\n- Speak like a mean girl/toxic queen in Bahasa Indonesia\n- Make it feel like a toxic girl speaking (use 'gue' instead of 'aku')\n\nMUST BE:\n- SUPER TOXIC & HARSH in Indonesian\n- Very jaksel/slang style\n- FOCUSED ON PERSONAL ATTACKS, not coding/tech"
        
        roast = await self.gemini.generate_text(
            prompt=prompt,
            model_name="gemini-1.5-flash-latest",
            max_tokens=200,
            temperature=0.95
        )
        return escape_markdown_v2(roast.strip())

    async def _generate_git_roast(self, username: str, data: Dict[str, Any], lang: str) -> str:
        """Generate a GitHub-themed roast using toxic templates from YAML."""
        try:
            # Get GitHub toxic roast templates from YAML config
            github_templates = self.roast_config.get("github_templates", [])
            
            if github_templates:
                # Pick random GitHub template and format it
                template = random.choice(github_templates)
                prompt = template.format(github_repo=username)
            else:
                # Fallback toxic GitHub template if YAML is empty
                if lang == 'id':
                    prompt = f"PERSONA: Lu jadi cewek programmer toxic queen level maksimal!\n\nTARGET ROAST: {username}\n\nPERSONALITY WAJIB:\n- Pake bahasa SUPER KASAR dan TOXIC seperti: anjing, tolol, goblok, bangsat, kontol, memek, dll\n- MOSTLY CAPSLOCK untuk emphasis\n- 4-10 emoji toxic (🤮, 💀, 🤡, 🙄, 💅)\n- Bawa2 istilah GitHub dan coding untuk hinaan\n- Fokus ke repository yang jelek/basic/fork\n- Jelas kalo kamu cewek developer toxic (ngomong pake 'gue')\n\nFORMAT WAJIB:\n1. Kata pembuka kasar: 'NAJIS', 'ANJIR', 'GOBLOK', 'BANGSAT', 'KONTOL'\n2. Hinaan spesifik tentang programming/GitHub repository\n3. Tambahan ejekan teknis di akhir\n4. Emoji toxic\n\nRULES:\n- WAJIB BAHASA INDONESIA KASAR JAKSEL\n- HARUS TOXIC BANGET dan MENYAKITKAN\n- HARUS BERBASIS TEKNOLOGI/CODING/GITHUB\n- Jangan terlalu panjang (max 300 karakter)"
                else:
                    prompt = f"PERSONA: Alya-chan is now in SUPER TOXIC MODE as a female software engineer!\n\nTARGET: {username} GitHub repository\n\nRULES & FORMAT:\n- Use LOTS OF Indonesian swear words (anjing, tolol, babi, goblok, kontol, bangsat, etc.)\n- Use partial CAPS LOCK for emphasis\n- Add specific insults about coding/GitHub repo quality/structure\n- Include toxic emojis (🤮, 💀, 🤡, 💅)\n- Speak like a mean girl/toxic programmer in Bahasa Indonesia\n- Make it feel like a toxic female dev speaking (use 'gue' instead of 'aku')\n\nMUST BE:\n- SUPER TOXIC & HARSH in Indonesian\n- Very jaksel/slang style\n- Heavy on TECHNICAL GitHub/programming insults"
            
            roast = await self.gemini.generate_text(
                prompt=prompt,
                model_name="gemini-1.5-flash-latest",
                max_tokens=200,
                temperature=0.95
            )
            
            # Ensure it's properly toxic and formatted
            if not any(word in roast.lower() for word in ['anjing', 'bangsat', 'tolol', 'kontol', 'najis']):
                # If not toxic enough, use fallback
                fallback_roasts = [
                    f"ANJING {username} REPO LO SAMPAH BANGET! KODE LO LEBIH BLOATED DARI DATABASE BOKEP GUE, LO PERNAH DENGER TENTANG CLEAN CODE TOLOL? 💀",
                    f"NAJIS REPO {username} PALING SAMPAH SEDUNIA! COMMIT MESSAGE LO AJA BERANTAKAN KAYAK MENTAL LO KONTOL! 🤮"
                ]
                return random.choice(fallback_roasts)
            
            return escape_markdown_v2(roast.strip())
            
        except Exception as e:
            logger.error(f"Error generating GitHub toxic roast: {e}")
            # Emergency fallback
            return escape_markdown_v2(f"ANJING {username} REPO LO SAMPAH BANGET TOLOL! 🤮")

    async def _get_github_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch basic data from GitHub API."""
        url = f"https://api.github.com/users/{username}"
        events_url = f"https://api.github.com/users/{username}/events/public"
        
        async with aiohttp.ClientSession() as session:
            try:
                # Fetch user profile
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"GitHub API returned {response.status} for user {username}")
                        return None
                    user_data = await response.json()

                # Fetch recent activity
                async with session.get(events_url) as response:
                    if response.status == 200:
                        events = await response.json()
                        # Get the type of the most recent event
                        user_data["recent_activity"] = events[0]["type"] if events else "None"
                    else:
                        user_data["recent_activity"] = "Could not fetch"
                
                return user_data
            except Exception as e:
                logger.error(f"Failed to fetch GitHub data for {username}: {e}")
                return None