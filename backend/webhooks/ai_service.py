import openai
import logging
import time
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from .models import LeadDetail, YelpBusiness, AISettings
import os

logger = logging.getLogger(__name__)

class OpenAIService:
    """Сервіс для роботи з OpenAI API для генерації персоналізованих повідомлень"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Ініціалізація OpenAI клієнта з глобальних налаштувань"""
        try:
            # Спочатку пробуємо отримати API ключ з .env файла
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                # Якщо немає в .env, пробуємо з AISettings моделі
                ai_settings = AISettings.objects.first()
                if ai_settings and ai_settings.openai_api_key:
                    openai_api_key = ai_settings.openai_api_key
            
            if openai_api_key:
                self.client = openai.OpenAI(
                    api_key=openai_api_key
                )
                logger.info("[AI-SERVICE] OpenAI client initialized successfully")
            else:
                logger.error("[AI-SERVICE] No OpenAI API key found in environment variables or database")
                self.client = None
                
        except Exception as e:
            logger.error(f"[AI-SERVICE] Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Перевіряє чи доступний AI сервіс"""
        return self.client is not None
    
    def check_rate_limit(self) -> bool:
        """Перевіряє rate limit для AI запитів"""
        ai_settings = AISettings.objects.first()
        if not ai_settings:
            return True
        
        cache_key = "ai_requests_count"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= ai_settings.requests_per_minute:
            logger.warning(f"[AI-SERVICE] Rate limit exceeded: {current_count}/{ai_settings.requests_per_minute}")
            return False
        
        # Збільшуємо лічильник на 1 хвилину
        cache.set(cache_key, current_count + 1, 60)
        return True
    
    def generate_greeting_message(
        self, 
        lead_detail: LeadDetail, 
        business: Optional[YelpBusiness] = None,
        is_off_hours: bool = False,
        response_style: str = 'auto',
        include_location: bool = False,
        mention_response_time: bool = False,
        custom_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Генерує AI-powered greeting повідомлення на основі контексту ліда"""
        
        if not self.is_available():
            logger.error("[AI-SERVICE] OpenAI client not available")
            return None
        
        if not self.check_rate_limit():
            logger.warning("[AI-SERVICE] Rate limit exceeded, skipping AI generation")
            return None
        
        try:
            # Підготовка контексту для AI
            context = self._prepare_lead_context(
                lead_detail, business, is_off_hours, 
                include_location, mention_response_time
            )
            
            # Створення промпта
            prompt = self._create_greeting_prompt(
                context, response_style, custom_prompt
            )
            
            # Отримання налаштувань AI
            ai_settings = AISettings.objects.first()
            model = ai_settings.openai_model if ai_settings else "gpt-4o"
            temperature = ai_settings.default_temperature if ai_settings else 0.7
            max_length = ai_settings.max_message_length if ai_settings else 160
            
            # Виклик OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt(custom_prompt)
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=temperature
            )
            
            ai_message = response.choices[0].message.content.strip()
            
            # Обрізаємо повідомлення якщо воно завелике
            if len(ai_message) > max_length:
                ai_message = ai_message[:max_length-3] + "..."
            
            logger.info(f"[AI-SERVICE] Generated greeting for lead {lead_detail.lead_id}: {ai_message[:50]}...")
            return ai_message
            
        except Exception as e:
            logger.error(f"[AI-SERVICE] Error generating AI greeting: {e}")
            return None
    
    def generate_preview_message(
        self,
        business_name: str,
        customer_name: str = "John",
        services: str = "plumbing services",
        response_style: str = 'auto',
        include_location: bool = False,
        mention_response_time: bool = False,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Генерує превʼю повідомлення для тестування налаштувань"""
        
        if not self.is_available():
            return "AI service not available. Please check your settings."
        
        try:
            # Створюємо тестовий контекст
            context = {
                "customer_name": customer_name,
                "services": services,
                "business_name": business_name,
                "business_location": "Sample City" if include_location else "",
                "is_off_hours": False,
                "mention_response_time": mention_response_time
            }
            
            prompt = self._create_greeting_prompt(context, response_style, custom_prompt)
            
            ai_settings = AISettings.objects.first()
            model = ai_settings.openai_model if ai_settings else "gpt-4o"
            temperature = ai_settings.default_temperature if ai_settings else 0.7
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(custom_prompt)
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=160,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"[AI-SERVICE] Error generating preview: {e}")
            return f"Error generating preview: {str(e)}"
    
    def _prepare_lead_context(
        self, 
        lead_detail: LeadDetail, 
        business: Optional[YelpBusiness],
        is_off_hours: bool,
        include_location: bool,
        mention_response_time: bool
    ) -> Dict[str, Any]:
        """Підготовка контексту ліда для AI"""
        
        return {
            "customer_name": lead_detail.user_display_name or "there",
            "services": ", ".join(lead_detail.project.get("job_names", [])) if lead_detail.project else "",
            "business_name": business.name if business else "our business",
            "business_location": business.location if (business and include_location) else "",
            "is_off_hours": is_off_hours,
            "mention_response_time": mention_response_time,
            "phone_number": getattr(lead_detail, 'phone_number', None),
            "additional_info": getattr(lead_detail, 'additional_notes', '') or '',
            "created_at": lead_detail.created_at if hasattr(lead_detail, 'created_at') else timezone.now()
        }
    
    def _get_system_prompt(self, custom_prompt: Optional[str] = None) -> str:
        """Отримує системний промпт (кастомний або глобальний)"""
        if custom_prompt:
            return custom_prompt
        
        ai_settings = AISettings.objects.first()
        if ai_settings and ai_settings.base_system_prompt:
            return ai_settings.base_system_prompt
        
        return "You are a professional business communication assistant. Generate personalized, friendly, and professional greeting messages for potential customers who have inquired about services."
    
    def _create_greeting_prompt(
        self, 
        context: Dict[str, Any], 
        response_style: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Створює промпт для генерації вітального повідомлення"""
        
        style_instruction = {
            'formal': "Use a formal, professional tone.",
            'casual': "Use a casual, friendly tone.",
            'auto': "Use an appropriate tone based on the context."
        }.get(response_style, "Use an appropriate tone based on the context.")
        
        time_context = ""
        if context.get('is_off_hours'):
            time_context = "Note: This message is being sent outside business hours, acknowledge this appropriately."
        
        location_context = ""
        if context.get('business_location'):
            location_context = f"Business is located in {context['business_location']}."
        
        response_time_context = ""
        if context.get('mention_response_time'):
            response_time_context = "Mention that they can expect a response within 24 hours."
        
        return f"""
Create a personalized greeting message for a potential customer with these details:
- Customer name: {context.get('customer_name', 'there')}
- Services they're interested in: {context.get('services', 'our services')}
- Business name: {context.get('business_name', 'our business')}
{location_context}
{time_context}
{response_time_context}

Style requirements:
- {style_instruction}
- Keep it under 160 characters (SMS friendly)
- Be professional but warm
- Mention their specific service interest if provided
- Use their name if provided
- Include a clear next step or call to action

Generate only the message text, no additional formatting:
        """.strip()
    
    def _fallback_message(self, context: Dict[str, Any]) -> str:
        """Fallback повідомлення якщо AI не працює"""
        name = context.get('customer_name', '')
        services = context.get('services', 'our services')
        business = context.get('business_name', 'our business')
        
        if name and name != 'there':
            return f"Hello {name}! Thank you for your inquiry about {services}. We'll get back to you soon!"
        else:
            return f"Hello! Thank you for your inquiry about {services}. We'll get back to you soon!" 