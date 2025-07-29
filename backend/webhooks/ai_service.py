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
        custom_prompt: Optional[str] = None,
        business_data_settings: Optional[Dict[str, bool]] = None
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
                include_location, mention_response_time, business_data_settings
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
        custom_prompt: Optional[str] = None,
        business_data_settings: Optional[Dict[str, bool]] = None
    ) -> str:
        """Генерує превʼю повідомлення для тестування налаштувань"""
        
        if not self.is_available():
            return "AI service not available. Please check your settings."
        
        # Налаштування за замовчуванням для превʼю
        if not business_data_settings:
            business_data_settings = {
                "include_rating": True,
                "include_categories": True,
                "include_phone": True,
                "include_website": False,
                "include_price_range": True,
                "include_hours": True,
                "include_reviews_count": True,
                "include_address": False,
                "include_transactions": False
            }
        
        try:
            # Створюємо тестовий контекст з повними бізнес-даними
            sample_business_data = {
                "name": business_name,
                "location": "Sample City, CA" if include_location else "",
                "time_zone": "America/Los_Angeles",
                "open_days": "Mon, Tue, Wed, Thu, Fri",
                "open_hours": "Mon: 08:00 - 18:00; Tue: 08:00 - 18:00; Wed: 08:00 - 18:00"
            }
            
            # Додаємо тестові дані на основі налаштувань
            if business_data_settings.get("include_rating"):
                sample_business_data["rating"] = 4.8
                if business_data_settings.get("include_reviews_count"):
                    sample_business_data["review_count"] = 156
            
            if business_data_settings.get("include_categories"):
                sample_business_data["categories"] = ["General Contractors", "Plumbing", "Electrical"]
            
            if business_data_settings.get("include_phone"):
                sample_business_data["phone"] = "(555) 123-4567"
            
            if business_data_settings.get("include_website"):
                sample_business_data["website"] = f"https://{business_name.lower().replace(' ', '')}.com"
            
            if business_data_settings.get("include_price_range"):
                sample_business_data["price"] = "$$"
            
            if business_data_settings.get("include_address"):
                sample_business_data["address"] = ["123 Main St", "Sample City, CA 90210"]
                sample_business_data["city"] = "Sample City"
                sample_business_data["state"] = "CA"
                sample_business_data["zip_code"] = "90210"
            
            if business_data_settings.get("include_hours"):
                sample_business_data["is_open_now"] = True
            
            if business_data_settings.get("include_transactions"):
                sample_business_data["transactions"] = ["consultation", "estimates", "emergency_services"]
            
            context = {
                "customer_name": customer_name,
                "services": services,
                "business_name": business_name,
                "business_location": "Sample City, CA" if include_location else "",
                "is_off_hours": False,
                "mention_response_time": mention_response_time,
                "business_data": sample_business_data,
                "business_data_settings": business_data_settings
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
        mention_response_time: bool,
        business_data_settings: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """Підготовка контексту ліда для AI з повною інформацією про бізнес"""
        
        # Налаштування за замовчуванням
        if not business_data_settings:
            business_data_settings = {
                "include_rating": True,
                "include_categories": True,
                "include_phone": True,
                "include_website": False,
                "include_price_range": True,
                "include_hours": True,
                "include_reviews_count": True,
                "include_address": False,
                "include_transactions": False
            }
        
        # Базова інформація про клієнта
        context = {
            "customer_name": lead_detail.user_display_name or "there",
            "services": ", ".join(lead_detail.project.get("job_names", [])) if lead_detail.project else "",
            "phone_number": getattr(lead_detail, 'phone_number', None),
            "additional_info": getattr(lead_detail, 'additional_notes', '') or '',
            "created_at": lead_detail.created_at if hasattr(lead_detail, 'created_at') else timezone.now(),
            "is_off_hours": is_off_hours,
            "mention_response_time": mention_response_time
        }
        
        if not business:
            context.update({
                "business_name": "our business",
                "business_location": "",
                "business_data": {}
            })
            return context
        
        # ПОВНА інформація про бізнес з YelpBusiness
        business_data = {
            "name": business.name,
            "location": business.location,
            "time_zone": business.time_zone,
            "open_days": business.open_days,
            "open_hours": business.open_hours,
            "business_id": business.business_id
        }
        
        # Додаємо дані з details JSON на основі налаштувань
        if business.details:
            details = business.details
            
            # Рейтинг та відгуки
            if business_data_settings.get("include_rating") and details.get("rating"):
                business_data["rating"] = details.get("rating", 0)
                if business_data_settings.get("include_reviews_count"):
                    business_data["review_count"] = details.get("review_count", 0)
            
            # Категорії бізнесу
            if business_data_settings.get("include_categories") and details.get("categories"):
                business_data["categories"] = [cat.get("title", "") for cat in details.get("categories", [])]
                business_data["category_aliases"] = [cat.get("alias", "") for cat in details.get("categories", [])]
            
            # Контактна інформація
            if business_data_settings.get("include_phone") and details.get("phone"):
                business_data["phone"] = details.get("phone", "")
            
            if business_data_settings.get("include_website") and details.get("url"):
                business_data["website"] = details.get("url", "")
            
            # Ціновий діапазон
            if business_data_settings.get("include_price_range") and details.get("price"):
                business_data["price"] = details.get("price", "")
            
            # Адреса
            if business_data_settings.get("include_address") and details.get("location"):
                location_data = details.get("location", {})
                business_data["address"] = location_data.get("display_address", [])
                business_data["city"] = location_data.get("city", "")
                business_data["state"] = location_data.get("state", "")
                business_data["zip_code"] = location_data.get("zip_code", "")
            
            # Робочі години
            if business_data_settings.get("include_hours") and details.get("hours"):
                business_data["hours_detailed"] = details.get("hours", [])
                business_data["is_open_now"] = details.get("hours", [{}])[0].get("is_open_now", False) if details.get("hours") else False
            
            # Транзакції та послуги
            if business_data_settings.get("include_transactions") and details.get("transactions"):
                business_data["transactions"] = details.get("transactions", [])
            
            # Додаткові дані (завжди включаємо для розширених можливостей)
            business_data.update({
                "coordinates": details.get("coordinates", {}),
                "image_url": details.get("image_url", ""),
                "is_claimed": details.get("is_claimed", False),
                "is_closed": details.get("is_closed", False),
                "yelp_url": details.get("url", "")
            })
        
        context.update({
            "business_name": business.name,
            "business_location": business.location if include_location else "",
            "business_data": business_data,
            "business_data_settings": business_data_settings
        })
        
        return context
    
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
        """Створює промпт для генерації вітального повідомлення з повними бізнес-даними"""
        
        style_instruction = {
            'formal': "Use a formal, professional tone.",
            'casual': "Use a casual, friendly tone.",
            'auto': "Use an appropriate tone based on the context."
        }.get(response_style, "Use an appropriate tone based on the context.")
        
        # Отримуємо бізнес-дані та налаштування
        business_data = context.get('business_data', {})
        business_data_settings = context.get('business_data_settings', {})
        
        # Формуємо розширену інформацію про бізнес для промпта
        business_context_parts = []
        
        # Основна інформація
        if business_data.get('name'):
            business_context_parts.append(f"Business name: {business_data['name']}")
        
        if context.get('business_location') and business_data.get('location'):
            business_context_parts.append(f"Location: {business_data['location']}")
        
        # Категорії бізнесу
        if business_data_settings.get('include_categories') and business_data.get('categories'):
            categories = ", ".join(business_data['categories'][:3])  # Перші 3 категорії
            business_context_parts.append(f"Business specializes in: {categories}")
        
        # Рейтинг та відгуки
        if business_data_settings.get('include_rating') and business_data.get('rating'):
            rating = business_data['rating']
            review_count = business_data.get('review_count', 0)
            if business_data_settings.get('include_reviews_count') and review_count > 0:
                business_context_parts.append(f"Rating: {rating}/5 stars ({review_count} reviews)")
            else:
                business_context_parts.append(f"Rating: {rating}/5 stars")
        
        # Ціновий діапазон
        if business_data_settings.get('include_price_range') and business_data.get('price'):
            business_context_parts.append(f"Price range: {business_data['price']}")
        
        # Телефон
        if business_data_settings.get('include_phone') and business_data.get('phone'):
            business_context_parts.append(f"Phone: {business_data['phone']}")
        
        # Веб-сайт
        if business_data_settings.get('include_website') and business_data.get('website'):
            business_context_parts.append(f"Website available")
        
        # Адреса
        if business_data_settings.get('include_address') and business_data.get('address'):
            address = ", ".join(business_data['address'][:2])  # Перші 2 частини адреси
            business_context_parts.append(f"Address: {address}")
        
        # Робочі години
        hours_context = ""
        if business_data_settings.get('include_hours'):
            if context.get('is_off_hours'):
                hours_context = "IMPORTANT: Currently outside business hours"
                business_context_parts.append("Currently closed - outside business hours")
            elif business_data.get('is_open_now'):
                business_context_parts.append("Currently open")
            
            if business_data.get('open_hours'):
                hours_summary = business_data['open_hours'][:50] + "..." if len(business_data.get('open_hours', '')) > 50 else business_data.get('open_hours', '')
                business_context_parts.append(f"Business hours: {hours_summary}")
        
        # Транзакції та послуги
        if business_data_settings.get('include_transactions') and business_data.get('transactions'):
            transactions = ", ".join(business_data['transactions'][:3])  # Перші 3 транзакції
            business_context_parts.append(f"Available services: {transactions}")
        
        business_context = "\n".join([f"- {part}" for part in business_context_parts])
        
        # Контекст часу
        time_context = ""
        if context.get('is_off_hours'):
            time_context = "IMPORTANT: This message is being sent outside business hours. Acknowledge this and mention when they can expect a response."
        
        response_time_context = ""
        if context.get('mention_response_time'):
            response_time_context = "Mention expected response time (within 24 hours or based on business hours)."
        
        return f"""
You are representing a business and responding to a potential customer inquiry. Use ALL the business information provided to create a personalized, professional response that showcases the business's strengths.

CUSTOMER INFORMATION:
- Customer name: {context.get('customer_name', 'there')}
- Services interested in: {context.get('services', 'our services')}
- Inquiry time: {context.get('created_at', 'recently')}

BUSINESS INFORMATION:
{business_context}

CONTEXT:
{time_context}
{response_time_context}

STYLE REQUIREMENTS:
- {style_instruction}
- Keep it under 160 characters (SMS friendly)
- Be professional but warm and welcoming
- Mention their specific service interest
- Use their name if provided
- Include a clear next step or call to action
- Leverage the business's strengths (rating, specialization, location, etc.)
- Make it feel personal and authentic to this specific business
- If rating/reviews are available, subtly highlight business credibility
- If specialization is available, mention relevant expertise

Generate only the message text, no additional formatting or explanation:
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