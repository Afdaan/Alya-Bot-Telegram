"""
Service implementations for external APIs and models.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

from ..domain.entities import User, AIResponse, EmotionType, PersonaConfig
from ..domain.services import AIService, SentimentService
from config.settings import settings

logger = logging.getLogger(__name__)


class GeminiAIService(AIService):
    """Google Gemini AI service implementation."""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=1000,
        )
    
    async def generate_response(
        self, 
        message: str, 
        context: str, 
        persona: PersonaConfig,
        user: User
    ) -> AIResponse:
        """Generate AI response using Gemini."""
        try:
            # Build prompt with persona and context
            prompt = self._build_prompt(message, context, persona, user)
            
            # Generate response asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(
                    prompt, 
                    generation_config=self.generation_config
                )
            )
            
            content = response.text if response.text else "Maaf, saya tidak bisa memproses pesan itu."
            
            return AIResponse(
                content=content,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
                confidence=0.9  # Placeholder
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return AIResponse(
                content="Gomen... ada error nih! 😅 Coba lagi ya~",
                confidence=0.0
            )
    
    def _build_prompt(
        self, 
        message: str, 
        context: str, 
        persona: PersonaConfig, 
        user: User
    ) -> str:
        """Build prompt with persona and context."""
        lang = user.language_code
        base_instructions = persona.base_instructions.get(lang, persona.base_instructions.get("id", ""))
        personality_traits = "\n- ".join(persona.personality_traits.get(lang, []))
        
        # Get relationship-specific instructions
        relationship_instructions = ""
        if user.relationship_level.value < len(persona.relationship_levels.get(lang, [])):
            relationship_instructions = persona.relationship_levels[lang][user.relationship_level.value]
        
        prompt = f"""
{base_instructions}

**Kepribadian Alya:**
- {personality_traits}

**Hubungan dengan {user.first_name or "user"}:**
{relationship_instructions}

**Konteks Percakapan:**
{context if context else "Ini adalah awal percakapan kalian."}

**Pesan dari {user.first_name or "user"}:**
{message}

**Tugasmu:**
Jawab sebagai Alya dengan kepribadian tsundere yang authentic. Gunakan bahasa {lang.upper()}. Sesekali gunakan kata-kata Rusia untuk penekanan emosi.
"""
        return prompt


class HuggingFaceSentimentService(SentimentService):
    """HuggingFace sentiment analysis service."""
    
    def __init__(self):
        self.sentiment_model = None
        self.emotion_model = None
        self._load_models()
    
    def _load_models(self):
        """Load HuggingFace models."""
        try:
            # Load sentiment model
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=settings.sentiment_model,
                return_all_scores=True
            )
            
            # Load emotion model
            self.emotion_pipeline = pipeline(
                "text-classification",
                model=settings.emotion_model,
                return_all_scores=True
            )
            
            logger.info("Sentiment and emotion models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            # Fallback to dummy implementations
            self.sentiment_pipeline = None
            self.emotion_pipeline = None
    
    async def analyze_emotion(self, text: str) -> EmotionType:
        """Analyze emotion from text."""
        if not self.emotion_pipeline:
            return EmotionType.NEUTRAL
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self.emotion_pipeline, text)
            
            # Get the emotion with highest score
            best_emotion = max(results[0], key=lambda x: x['score'])
            emotion_label = best_emotion['label'].lower()
            
            # Map to our emotion types
            emotion_mapping = {
                'joy': EmotionType.HAPPY,
                'sadness': EmotionType.SAD,
                'anger': EmotionType.ANGRY,
                'fear': EmotionType.FEARFUL,
                'surprise': EmotionType.SURPRISED,
                'disgust': EmotionType.DISGUSTED,
                'neutral': EmotionType.NEUTRAL
            }
            
            return emotion_mapping.get(emotion_label, EmotionType.NEUTRAL)
            
        except Exception as e:
            logger.error(f"Error analyzing emotion: {e}")
            return EmotionType.NEUTRAL
    
    async def get_sentiment_score(self, text: str) -> float:
        """Get sentiment score (-1 to 1)."""
        if not self.sentiment_pipeline:
            return 0.0
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self.sentiment_pipeline, text)
            
            # Convert to -1 to 1 scale
            for result in results[0]:
                if result['label'] == 'POSITIVE':
                    return result['score']
                elif result['label'] == 'NEGATIVE':
                    return -result['score']
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting sentiment score: {e}")
            return 0.0
