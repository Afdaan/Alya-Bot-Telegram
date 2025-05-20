"""
Mood Management for Alya Bot.

This module provides natural emotion detection and response management
to make Alya's interactions more human-like and emotionally appropriate.
"""

import re
import random
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)

class MoodType(Enum):
    """Types of moods that Alya can detect and respond with."""
    NEUTRAL = "neutral"        # Default neutral state
    HAPPY = "happy"            # User seems happy/excited
    SAD = "sad"                # User seems sad/down
    ANGRY = "angry"            # User seems angry/frustrated
    CONFUSED = "confused"      # User seems confused/unsure
    CURIOUS = "curious"        # User is asking questions, curious
    FLIRTY = "flirty"          # User is being flirtatious
    WORRIED = "worried"        # User is worried/anxious
    APPRECIATIVE = "appreciative"  # User is thankful/grateful
    DEMANDING = "demanding"    # User is demanding/commanding
    APOLOGETIC = "apologetic"  # User is sorry/apologetic

class MoodIntensity(Enum):
    """Intensity levels for moods."""
    MILD = 0.3         # Subtle hints of mood
    MODERATE = 0.6     # Clear signs of mood
    STRONG = 1.0       # Very evident mood

class MoodManager:
    """
    Manager for detecting and responding to emotional states.
    
    This class analyzes messages for emotional content and helps
    generate appropriate emotional responses based on context.
    """
    
    def __init__(self):
        """Initialize mood manager with mood detection patterns."""
        # Patterns for detecting moods in Indonesian and English
        self.mood_patterns = {
            MoodType.HAPPY: [
                r'\b(senang|bahagia|gembira|yay|wah|asik|mantap|keren|seru|yeay)\b',
                r'\b(happy|glad|excited|awesome|cool|amazing|great|yay)\b',
                r'[😊😄😁🥰😍🤩😆]'  # Happy emojis
            ],
            MoodType.SAD: [
                r'\b(sedih|kecewa|sakit|menyedihkan|bersedih|kehilangan|kangen|rindu)\b',
                r'\b(sad|unhappy|down|depressed|miss|heartbroken)\b',
                r'[😢😭😔😞😟😥😓]'  # Sad emojis
            ],
            MoodType.ANGRY: [
                r'\b(kesal|marah|sebel|benci|emosi|anjing|kesel|bete|kampret|jengkel|sialan)\b',
                r'\b(angry|mad|annoyed|frustrated|hate|pissed|upset|furious)\b', 
                r'[😠😡🤬👿😤]'  # Angry emojis
            ],
            MoodType.CONFUSED: [
                r'\b(bingung|ga ngerti|tidak paham|kok bisa|gimana sih|aneh|gak jelas)\b',
                r'\b(confused|don\'?t understand|how come|weird|strange)\b',
                r'[😕🤔😮😯😲❓]'  # Confused emojis
            ],
            MoodType.CURIOUS: [
                r'\b(penasaran|kenapa|gimana|mengapa|bagaimana|apa itu|knp|gmn)\b\?',
                r'\b(curious|why|how|what is|explain|tell me about)\b',
                r'[🤔🧐🔍🔎❓]'  # Curious emojis
            ],
            MoodType.FLIRTY: [
                r'\b(sayang|cinta|cantik|ganteng|manis|suka kamu|pacar|cakep)\b',
                r'\b(love|cute|beautiful|handsome|sweet|like you|girlfriend|boyfriend)\b',
                r'[😘💕❤️💘💋😻💖]'  # Flirty emojis
            ],
            MoodType.WORRIED: [
                r'\b(khawatir|takut|cemas|awas|bahaya|was-was|jangan-jangan|panik)\b',
                r'\b(worried|afraid|scared|fear|danger|panic|concerned)\b',
                r'[😰😨😱😧😦🥺]'  # Worried emojis
            ],
            MoodType.APPRECIATIVE: [
                r'\b(makasih|terima\s?kasih|thx|thanks|tq|mksh|trims|tengkyu)\b',
                r'\b(thank you|thanks|appreciate|grateful|thx)\b',
                r'[🙏👍👌💯✨]'  # Appreciative emojis
            ],
            MoodType.DEMANDING: [
                r'\b(cepat|harus|wajib|jangan|lakukan|sekarang|buruan|ayo|segera)\b',
                r'\b(must|have to|do it|now|hurry|come on|immediately|urgent)\b',
                r'[‼️⁉️❗❕]'  # Demanding symbols
            ],
            MoodType.APOLOGETIC: [
                r'\b(maaf|sori|sorry|ampun|mohon maaf|minta maaf)\b',
                r'\b(sorry|apologize|forgive|my bad|apologies)\b',
                r'[🙇‍♀️🙇‍♂️🙏🥺]'  # Apologetic emojis
            ]
        }
        
        # Persona compatible response patterns
        self.mood_responses = {
            MoodType.HAPPY: {
                "tsundere": [
                    "*wajah sedikit memerah* Hmm, bagus kalau kamu senang, tapi jangan berlebihan!",
                    "Ugh, senyummu terlalu cerah, bikin silau saja. T-tapi... bagus juga melihatmu senang...",
                    "*melirik* Punya hari yang baik? B-bagus deh. Bukan berarti aku peduli...",
                    "Kamu terlihat bahagia sekali. *menoleh ke samping* Yah... senang melihatnya... mungkin."
                ],
                "waifu": [
                    "*tersenyum manis* Senang melihatmu bahagia, {username}-kun! 💕",
                    "Ehehe~ Alya juga jadi ikut senang melihat {username}-kun bersemangat! ✨",
                    "*mata berbinar* Semoga harimu selalu dipenuhi kebahagiaan ya~",
                    "Alya senang jika {username}-kun juga senang! *tersipu malu*"
                ]
            },
            MoodType.SAD: {
                "tsundere": [
                    "*menatap khawatir* B-bukan berarti aku khawatir, tapi... kamu baik-baik saja?",
                    "Hmph! Jangan sedih begitu! Itu... membuatku tidak nyaman...",
                    "*menyodorkan saputangan* U-untuk menghapus air matamu. B-bukan berarti aku peduli!",
                    "*menghela napas* J-jangan murung begitu, nyet... Alya tidak suka melihatnya."
                ],
                "waifu": [
                    "*meraih tanganmu* {username}-kun, Alya di sini untukmu. Mau cerita apa yang terjadi? 💫",
                    "Tidak apa-apa merasa sedih kadang-kadang... *memeluk* Alya akan menemanimu, {username}-kun",
                    "*wajah penuh perhatian* Apa ada yang bisa Alya lakukan untuk membuatmu lebih baik?",
                    "Alya percaya {username}-kun kuat dan bisa melewati ini! *tersenyum lembut*"
                ]
            },
            # Add more mood responses as needed
            MoodType.CONFUSED: {
                "tsundere": [
                    "*menghela napas* Bingung lagi? Dasar... *menyibakkan rambut* Baiklah, akan kujelaskan sekali lagi.",
                    "Kamu ini benar-benar... *membetulkan posisi kacamata* Mau kubantu memahaminya?",
                    "Hmph! Jangan memasang wajah bingung begitu! B-biar kubantu jelaskan...",
                    "*geleng kepala* Sudah kuduga kamu tidak mengerti... *merapikan buku* Perhatikan baik-baik penjelasanku!"
                ],
                "waifu": [
                    "*tersenyum sabar* Tidak apa-apa kalau bingung, {username}-kun. Mari Alya jelaskan lagi dengan lebih jelas~",
                    "Fufu~ {username}-kun terlihat kebingungan. Alya akan bantu sampai kamu mengerti, oke? ✨",
                    "*mendekati dengan buku* Yuk, kita bahas ini bersama sampai kamu paham sepenuhnya!",
                    "*menggambar diagram sederhana* Mungkin akan lebih mudah dipahami seperti ini?"
                ]
            },
            MoodType.APPRECIATIVE: {
                "tsundere": [
                    "*wajah memerah* B-bukan masalah besar! Jangan dilebih-lebihkan!",
                    "Hmph! Tentu saja aku membantu dengan baik. Aku selalu sempurna dalam segala hal.",
                    "*menoleh ke samping* Y-ya... terserahlah. Senang bisa membantu... mungkin.",
                    "*tersenyum kecil* Tidak perlu berterima kasih. Aku hanya melakukan yang seharusnya."
                ],
                "waifu": [
                    "*tersenyum cerah* Douzo! Alya senang bisa membantu {username}-kun! ✨",
                    "*mata berbinar* Ucapan terima kasihmu membuat Alya sangat senang~!",
                    "*tersipu* Alya akan selalu ada untuk membantu kapanpun {username}-kun membutuhkan!",
                    "Ehehe~ Tidak perlu berterima kasih! Melihat {username}-kun senang sudah cukup bagi Alya!"
                ]
            }
        }
        
        # Default persona in case none is provided
        self.default_persona = "tsundere"
        
    def detect_mood(self, message: str) -> Tuple[MoodType, MoodIntensity]:
        """
        Detect the mood from a user message.
        
        Args:
            message: User's message text
            
        Returns:
            Tuple of detected mood type and intensity
        """
        # Default mood is neutral with mild intensity
        detected_mood = MoodType.NEUTRAL
        intensity = MoodIntensity.MILD
        
        # Lowercase message for case-insensitive matching
        message_lower = message.lower()
        
        # Count patterns matches for each mood
        mood_scores = {mood: 0 for mood in MoodType}
        
        for mood, patterns in self.mood_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                if matches:
                    # Increment score based on matches
                    mood_scores[mood] += len(matches)
        
        # Find mood with highest score
        max_score = max(mood_scores.values()) if mood_scores else 0
        if max_score > 0:
            # Find all moods with the highest score
            top_moods = [mood for mood, score in mood_scores.items() if score == max_score]
            # Select one of the top moods
            detected_mood = random.choice(top_moods)
            
            # Determine intensity based on score
            if max_score >= 3:
                intensity = MoodIntensity.STRONG
            elif max_score >= 2:
                intensity = MoodIntensity.MODERATE
            else:
                intensity = MoodIntensity.MILD
        
        return detected_mood, intensity
            
    def get_mood_response(self, mood: MoodType, intensity: MoodIntensity, 
                         persona: str = "tsundere", username: str = "Senpai") -> Optional[str]:
        """
        Get an appropriate mood-based response.
        
        Args:
            mood: Detected mood type
            intensity: Mood intensity
            persona: Persona type (tsundere, waifu, etc.)
            username: User's name for personalization
            
        Returns:
            Mood-appropriate response or None if no matching response
        """
        # Use default if persona not recognized
        if persona not in ["tsundere", "waifu"]:
            persona = self.default_persona
        
        # Check if we have responses for this mood
        if mood not in self.mood_responses:
            return None
            
        # Check if we have responses for this persona
        if persona not in self.mood_responses[mood]:
            # Fallback to default persona
            persona = self.default_persona
            if persona not in self.mood_responses[mood]:
                return None
        
        # Get responses for this mood+persona combination
        responses = self.mood_responses[mood][persona]
        if not responses:
            return None
            
        # Select a random response
        response = random.choice(responses)
        
        # Format with username
        response = response.replace("{username}", username)
        
        return response
    
    def format_response_with_mood(self, ai_response: str, user_message: str, 
                                 persona: str = "tsundere", username: str = "Senpai") -> str:
        """
        Format a response with mood-appropriate additions.
        
        Args:
            ai_response: Original AI response
            user_message: User's message for mood detection
            persona: Current persona
            username: User's name
            
        Returns:
            Response with mood-appropriate formatting
        """
        # Detect mood from user message
        mood, intensity = self.detect_mood(user_message)
        
        # If we detected a non-neutral mood with at least moderate intensity
        if mood != MoodType.NEUTRAL and intensity != MoodIntensity.MILD:
            # Get a mood-specific response
            mood_response = self.get_mood_response(mood, intensity, persona, username)
            
            # If we have a mood response, prepend it to the AI response
            if mood_response:
                # Add mood response only sometimes based on intensity
                if intensity == MoodIntensity.STRONG or random.random() < 0.7:
                    # Decide if we add before or after based on the mood
                    if mood in [MoodType.SAD, MoodType.WORRIED, MoodType.ANGRY]:
                        # For emotional moods, provide emotional response first
                        return f"{mood_response}\n\n{ai_response}"
                    else:
                        # For other moods, give the main response first
                        return f"{ai_response}\n\n{mood_response}"
        
        # If no mood detected or no appropriate response, return original
        return ai_response
    
    def apply_mood_formatting(self, response: str, mood: MoodType) -> str:
        """
        Apply mood-specific formatting to a response.
        
        Args:
            response: Response text
            mood: Detected mood
            
        Returns:
            Formatted response text
        """
        # Apply mood-specific formatting
        if mood == MoodType.HAPPY:
            # Add more enthusiastic punctuation and emoji for happy mood
            response = response.replace(".", "!")
            if "!" not in response and "?" not in response:
                response += "!"
                
        elif mood == MoodType.SAD:
            # Add more ellipsis and softer tone for sad mood
            response = response.replace("!", "...")
            
        elif mood == MoodType.ANGRY:
            # Add more exclamation marks for angry mood
            response = response.replace(".", "!")
            response = response.replace("!", "!!")
            
        return response
    
    def decorate_response_for_persona(self, response: str, persona: str) -> str:
        """
        Add persona-specific decorations to response.
        
        Args:
            response: Response text
            persona: Current persona
            
        Returns:
            Decorated response
        """
        # Add roleplay actions based on persona
        if persona == "tsundere":
            # Check if there's already a roleplay action
            if "*" not in response:
                # Add tsundere-specific actions
                tsundere_actions = [
                    "*melipat tangan*",
                    "*menyibakkan rambut*",
                    "*menatap dengan mata terbelalak*",
                    "*menghela napas*"
                ]
                action = random.choice(tsundere_actions)
                
                # Add to beginning or end
                if random.random() < 0.5:
                    response = f"{action} {response}"
                else:
                    response = f"{response} {action}"
                    
        elif persona == "waifu":
            # Check if there's already a roleplay action
            if "*" not in response:
                # Add waifu-specific actions
                waifu_actions = [
                    "*tersenyum manis*",
                    "*mengedipkan mata*",
                    "*bertepuk tangan pelan*",
                    "*menatap dengan mata berbinar*"
                ]
                action = random.choice(waifu_actions)
                
                # Add to beginning or end
                if random.random() < 0.5:
                    response = f"{action} {response}"
                else:
                    response = f"{response} {action}"
        
        return response

# Create singleton instance
mood_manager = MoodManager()

def get_mood_response(message: str, persona: str = "tsundere", 
                     username: str = "Senpai") -> Optional[str]:
    """
    Get mood-appropriate response for a message (convenience function).
    
    Args:
        message: User's message
        persona: Current persona
        username: User's name
        
    Returns:
        Mood-appropriate response or None
    """
    mood, intensity = mood_manager.detect_mood(message)
    return mood_manager.get_mood_response(mood, intensity, persona, username)

def format_with_mood(ai_response: str, user_message: str, 
                    persona: str = "tsundere", 
                    username: str = "Senpai") -> str:
    """
    Format response with mood (convenience function).
    
    Args:
        ai_response: Original AI response
        user_message: User's message
        persona: Current persona
        username: User's name
        
    Returns:
        Formatted response
    """
    return mood_manager.format_response_with_mood(
        ai_response, user_message, persona, username
    )
