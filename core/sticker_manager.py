"""Manages sticker and GIF selection based on mood and context."""
from typing import Optional, List
import random
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, config_path: str = "config/persona/sticker_packs.yml"):
        self.config = self._load_config(config_path)
        self.last_sticker: Optional[str] = None  # Avoid repetition
    
    def _load_config(self, config_path: str) -> dict:
        """Load sticker pack configuration from YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
    
    def get_sticker_for_mood(
        self,
        mood: str,
        user_message: Optional[str] = None,
        relationship_level: int = 1
    ) -> Optional[str]:
        packs = self.config.get("sticker_packs", {})
        pack = packs.get("default", {}).get(mood) or packs.get(mood)
        
        logger.debug(
            f"[StickerManager] get_sticker_for_mood: "
            f"mood={mood}, message={user_message[:50] if user_message else None}, "
            f"pack_found={pack is not None}"
        )
        
        if not pack or not pack.get("stickers"):
            logger.warning(f"[StickerManager] No sticker pack found for mood: {mood}")
            return None
        
        # Check if message triggers specific sticker
        sticker = self._match_trigger_sticker(pack, user_message, mood)
        if sticker:
            logger.info(f"[StickerManager] Matched trigger sticker for mood '{mood}': {sticker}")
            return sticker
        
        # Random sticker from pack (avoid repetition)
        stickers = pack.get("stickers", [])
        available = [s for s in stickers if s != self.last_sticker]
        
        if not available:
            available = stickers
        
        if available:
            chosen = random.choice(available)
            self.last_sticker = chosen
            logger.info(f"[StickerManager] Selected random sticker for mood '{mood}': {chosen}")
            return chosen
        
        logger.warning(f"[StickerManager] No available stickers for mood '{mood}'")
        return None
    
    def get_gif_url_for_mood(
        self,
        mood: str,
        user_message: Optional[str] = None
    ) -> Optional[str]:
        packs = self.config.get("sticker_packs", {})
        pack = packs.get("default", {}).get(mood) or packs.get(mood)
        if not pack or not pack.get("gifs"):
            return None
        
        # Check for trigger-based GIF
        gif = self._match_trigger_gif(pack, user_message, mood)
        if gif:
            return gif
        
        # Random GIF from pack
        gifs = pack.get("gifs", [])
        return random.choice(gifs) if gifs else None
    
    def _match_trigger_sticker(
        self,
        pack: dict,
        user_message: Optional[str],
        mood: str
    ) -> Optional[str]:
        """Match sticker based on trigger keywords."""
        if not user_message or not pack.get("triggers"):
            return None
        
        message_lower = user_message.lower()
        logger.debug(f"[StickerManager] Checking triggers for mood '{mood}', message: {message_lower[:50]}")
        
        for trigger in pack.get("triggers", []):
            keywords = trigger.get("keyword", [])
            required_mood = trigger.get("mood_requirement")
            
            logger.debug(
                f"[StickerManager] Trigger check - keywords: {keywords}, "
                f"required_mood: {required_mood}, current_mood: {mood}"
            )
            
            # Check if mood matches requirement
            if required_mood and required_mood != mood:
                logger.debug(f"[StickerManager] Mood mismatch: {required_mood} != {mood}")
                continue
            
            # Check if any keyword matches
            if any(kw in message_lower for kw in keywords):
                sticker = trigger.get("sticker")
                logger.info(f"[StickerManager] Trigger matched! Sticker: {sticker}")
                if sticker:
                    return sticker
        
        logger.debug(f"[StickerManager] No trigger matches for mood '{mood}'")
        return None
    
    def _match_trigger_gif(
        self,
        pack: dict,
        user_message: Optional[str],
        mood: str
    ) -> Optional[str]:
        """Match GIF based on trigger keywords."""
        if not user_message or not pack.get("triggers"):
            return None
        
        message_lower = user_message.lower()
        
        for trigger in pack.get("triggers", []):
            keywords = trigger.get("keyword", [])
            required_mood = trigger.get("mood_requirement")
            
            if required_mood and required_mood != mood:
                continue
            
            if any(kw in message_lower for kw in keywords):
                gif = trigger.get("gif")
                if gif:
                    return gif
        
        return None