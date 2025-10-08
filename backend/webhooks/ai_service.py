import openai
import logging
import time
import json
import re
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from .models import LeadDetail, YelpBusiness, AISettings, AutoResponseSettings
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
    
    def _get_ai_settings(self, business_ai_settings: Optional['AutoResponseSettings'] = None) -> Dict[str, Any]:
        """Отримує AI налаштування з business-specific fallback на global"""
        # Отримуємо глобальні налаштування як fallback
        global_ai_settings = AISettings.objects.first()
        
        # Модель
        if business_ai_settings and business_ai_settings.ai_model:
            model = business_ai_settings.ai_model
            logger.info(f"[AI-SERVICE] Using business-specific model: {model}")
        else:
            model = global_ai_settings.openai_model if global_ai_settings else "gpt-4o"
            logger.info(f"[AI-SERVICE] Using fallback model: {model}")
        
        # Temperature
        if business_ai_settings and business_ai_settings.ai_temperature is not None:
            temperature = business_ai_settings.ai_temperature
            logger.info(f"[AI-SERVICE] Using business-specific temperature: {temperature}")
        else:
            temperature = global_ai_settings.default_temperature if global_ai_settings else 0.7
            logger.info(f"[AI-SERVICE] Using fallback temperature: {temperature}")
        
        # ✅ Max message length - DEPRECATED field, always use auto-detect from Sample Replies
        # ai_max_message_length field is ignored - система автоматично визначає довжину
        max_length = 500  # Generous default for auto-detect mode
        logger.info(f"[AI-SERVICE] 🎯 Using AUTO-DETECT mode for message length (generous default: {max_length} tokens)")
        logger.info(f"[AI-SERVICE] ai_max_message_length field is DEPRECATED and ignored")
        
        return {
            'model': model,
            'temperature': temperature,
            'max_length': max_length,
            'global_settings': global_ai_settings
        }
    
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
        # All AI behavior controlled via Custom Instructions (location, response time, business data, style)
        custom_prompt: Optional[str] = None,
        business_data_settings: Optional[Dict[str, bool]] = None,
        max_length: Optional[int] = None,
        business_ai_settings: Optional['AutoResponseSettings'] = None
    ) -> Optional[str]:
        """Генерує AI-powered greeting повідомлення на основі контексту ліда"""
        
        logger.info(f"[AI-SERVICE] ============= AI GREETING GENERATION (FALLBACK) =============")
        logger.info(f"[AI-SERVICE] 📋 Using Custom Instructions for response generation")
        logger.info(f"[AI-SERVICE] This path is used when:")
        logger.info(f"[AI-SERVICE]   - No Sample Replies configured")
        logger.info(f"[AI-SERVICE]   - Vector search found no similar examples")
        logger.info(f"[AI-SERVICE]   - Similarity score below threshold")
        logger.info(f"[AI-SERVICE] Input parameters:")
        logger.info(f"[AI-SERVICE] - Lead ID: {lead_detail.lead_id}")
        logger.info(f"[AI-SERVICE] - Customer name: {lead_detail.user_display_name}")
        logger.info(f"[AI-SERVICE] - Business: {business.name if business else 'None'}")
        logger.info(f"[AI-SERVICE] - is_off_hours: {is_off_hours}")
        # All AI behavior controlled via Custom Instructions
        logger.info(f"[AI-SERVICE] - custom_prompt provided: {custom_prompt is not None}")
        logger.info(f"[AI-SERVICE] - business_data_settings: {business_data_settings}")
        
        if not self.is_available():
            logger.error("[AI-SERVICE] ❌ OpenAI client not available")
            return None
        
        logger.info(f"[AI-SERVICE] ✅ OpenAI client is available")
        
        if not self.check_rate_limit():
            logger.warning("[AI-SERVICE] ⚠️ Rate limit exceeded, skipping AI generation")
            return None
        
        logger.info(f"[AI-SERVICE] ✅ Rate limit check passed")
        
        try:
            logger.info(f"[AI-SERVICE] 🔄 Preparing lead context...")
            
            # Підготовка контексту для AI
            context = self._prepare_lead_context(
                lead_detail, business, is_off_hours, 
                business_data_settings, custom_prompt
            )
            
            logger.info(f"[AI-SERVICE] ✅ Lead context prepared:")
            logger.info(f"[AI-SERVICE] - Customer name: {context.get('customer_name')}")
            logger.info(f"[AI-SERVICE] - Services: {context.get('services')}")
            logger.info(f"[AI-SERVICE] - Business name: {context.get('business_name')}")
            logger.info(f"[AI-SERVICE] - Phone number: {context.get('phone_number', 'Not provided')}")
            logger.info(f"[AI-SERVICE] - Additional info: {context.get('additional_info', 'None')[:50]}...")
            
            logger.info(f"[AI-SERVICE] 🔄 Creating prompt...")
            
            # Створення промпта
            prompt = self._create_greeting_prompt(
                context, custom_prompt, max_length
            )
            
            logger.info(f"[AI-SERVICE] ✅ Prompt created (length: {len(prompt)} characters)")
            logger.info(f"[AI-SERVICE] Prompt preview: {prompt[:200]}...")
            
            # Отримання AI налаштувань з business-specific fallback
            ai_config = self._get_ai_settings(business_ai_settings)
            model = ai_config['model']
            temperature = ai_config['temperature']
            
            # Використовуємо параметр max_length якщо наданий, інакше business/global
            if max_length is not None and max_length > 0:
                message_length = max_length
                logger.info(f"[AI-SERVICE] Using parameter max length: {message_length}")
            else:
                message_length = ai_config['max_length']
                logger.info(f"[AI-SERVICE] Using configured max length: {message_length}")
            
            logger.info(f"[AI-SERVICE] 🤖 Final AI configuration:")
            logger.info(f"[AI-SERVICE] - Model: {model}")
            logger.info(f"[AI-SERVICE] - Temperature: {temperature}")
            logger.info(f"[AI-SERVICE] - Max tokens: {message_length}")
            
            logger.info(f"[AI-SERVICE] 🤖 Calling OpenAI API...")
            logger.info(f"[AI-SERVICE] ========== OPENAI API CALL ==========")
            logger.info(f"[AI-SERVICE] About to call OpenAI chat completion...")
            logger.info(f"[AI-SERVICE] API parameters:")
            logger.info(f"[AI-SERVICE] - Model: {model}")
            logger.info(f"[AI-SERVICE] - Temperature: {temperature}")
            logger.info(f"[AI-SERVICE] - Max tokens: {message_length}")
            
            # 🎯 Для contextual AI analysis використовуємо custom prompt як system prompt
            system_prompt = self._get_system_prompt(custom_prompt)
            logger.info(f"[AI-SERVICE] - System prompt length: {len(system_prompt)} characters")
            logger.info(f"[AI-SERVICE] - User prompt length: {len(prompt)} characters")
            
            # 📋 FULL PROMPT LOGGING для діагностики
            logger.info(f"[AI-SERVICE] ==================== FULL PROMPT DETAILS ====================")
            logger.info(f"[AI-SERVICE] 📝 SYSTEM PROMPT (Custom Instructions):")
            logger.info(f"[AI-SERVICE] {system_prompt}")
            logger.info(f"[AI-SERVICE] " + "="*60)
            logger.info(f"[AI-SERVICE] 💬 USER PROMPT (Customer + Business Data):")
            logger.info(f"[AI-SERVICE] {prompt}")
            logger.info(f"[AI-SERVICE] " + "="*60)
            logger.info(f"[AI-SERVICE] 🚀 Making OpenAI API request...")
            
            # Підготовка повідомлень з урахуванням особливостей моделі
            messages = self._prepare_messages_for_model(model, system_prompt, prompt)
            
            # Підготовка параметрів API з урахуванням обмежень моделі
            api_params = self._get_api_params_for_model(model, messages, message_length, temperature)
            
            # Виклик OpenAI API
            response = self.client.chat.completions.create(**api_params)
            logger.info(f"[AI-SERVICE] ✅ OpenAI API call completed successfully")
            logger.info(f"[AI-SERVICE] ✅ OpenAI API responded successfully")
            
            ai_message = response.choices[0].message.content.strip()
            original_length = len(ai_message)
            
            logger.info(f"[AI-SERVICE] ==================== AI RESPONSE ====================")
            logger.info(f"[AI-SERVICE] 📤 RAW AI RESPONSE:")
            logger.info(f"[AI-SERVICE] {ai_message}")
            logger.info(f"[AI-SERVICE] " + "="*60)
            logger.info(f"[AI-SERVICE] 📊 Response length: {original_length} characters")
            
            # 🔍 АНАЛІЗ ДОТРИМАННЯ ПРАВИЛ З ПРОМПТУ
            logger.info(f"[AI-SERVICE] ==================== PROMPT COMPLIANCE ANALYSIS ====================")
            
            # Get expected time greeting from context
            from .utils import get_time_based_greeting
            business_id = context.get('business_id')
            expected_greeting = get_time_based_greeting(business_id)
            
            # Check 1: Time-based greeting
            has_correct_greeting = ai_message.lower().startswith(expected_greeting.lower())
            logger.info(f"[AI-SERVICE] ✅ Rule 1 - Time-based Greeting:")
            logger.info(f"[AI-SERVICE]    Expected: '{expected_greeting}'")
            logger.info(f"[AI-SERVICE]    Response starts with it: {has_correct_greeting}")
            if not has_correct_greeting:
                logger.warning(f"[AI-SERVICE]    ⚠️ AI IGNORED time-based greeting rule!")
                logger.warning(f"[AI-SERVICE]    Response starts with: '{ai_message[:50]}'")
            
            # Check 2: Customer name usage
            customer_name = context.get('customer_name', '')
            has_customer_name = customer_name.lower() in ai_message.lower() if customer_name != 'there' else True
            logger.info(f"[AI-SERVICE] ✅ Rule 2 - Customer Name Usage:")
            logger.info(f"[AI-SERVICE]    Customer name: '{customer_name}'")
            logger.info(f"[AI-SERVICE]    Name used in response: {has_customer_name}")
            if not has_customer_name and customer_name != 'there':
                logger.warning(f"[AI-SERVICE]    ⚠️ AI FORGOT to use customer name!")
            
            # Check 3: Signature presence (-Ben)
            has_signature = '-Ben' in ai_message or '- Ben' in ai_message or ai_message.strip().endswith('Ben')
            logger.info(f"[AI-SERVICE] ✅ Rule 3 - Signature (-Ben):")
            logger.info(f"[AI-SERVICE]    Signature present: {has_signature}")
            if not has_signature:
                logger.warning(f"[AI-SERVICE]    ⚠️ AI FORGOT signature!")
            
            # Check 4: Length appropriateness
            is_too_short = original_length < 200
            logger.info(f"[AI-SERVICE] ✅ Rule 4 - Response Length:")
            logger.info(f"[AI-SERVICE]    Length: {original_length} characters")
            logger.info(f"[AI-SERVICE]    Too short (< 200): {is_too_short}")
            if is_too_short:
                logger.warning(f"[AI-SERVICE]    ⚠️ Response seems TOO SHORT for natural conversation!")
            
            # Check 5: Forbidden phrases
            forbidden_phrases = ['call me', 'please call', 'give us a call', 'tailored design options', 
                               'structural considerations', 'just to confirm', 'scope and options']
            found_forbidden = [phrase for phrase in forbidden_phrases if phrase in ai_message.lower()]
            logger.info(f"[AI-SERVICE] ✅ Rule 5 - Forbidden Phrases:")
            logger.info(f"[AI-SERVICE]    Found forbidden phrases: {found_forbidden if found_forbidden else 'None'}")
            if found_forbidden:
                logger.warning(f"[AI-SERVICE]    ⚠️ AI USED FORBIDDEN PHRASES: {found_forbidden}")
            
            # Summary
            compliance_score = sum([has_correct_greeting, has_customer_name, has_signature, not is_too_short, len(found_forbidden) == 0])
            logger.info(f"[AI-SERVICE] 📊 COMPLIANCE SCORE: {compliance_score}/5")
            if compliance_score < 4:
                logger.warning(f"[AI-SERVICE] ⚠️ LOW COMPLIANCE - AI may be ignoring parts of Custom Instructions!")
            else:
                logger.info(f"[AI-SERVICE] ✅ GOOD COMPLIANCE - AI following instructions well")
            
            logger.info(f"[AI-SERVICE] ============================================================")
            logger.info(f"[AI-SERVICE] 🎉 FINAL AI GREETING:")
            logger.info(f"[AI-SERVICE] - Final message: '{ai_message}'")
            logger.info(f"[AI-SERVICE] - Final length: {len(ai_message)} characters")
            logger.info(f"[AI-SERVICE] Generated greeting for lead {lead_detail.lead_id}: {ai_message[:50]}...")
            logger.info(f"[AI-SERVICE] ==============================================" )
            
            return ai_message
            
        except Exception as e:
            logger.error(f"[AI-SERVICE] ❌ Error generating AI greeting: {e}")
            logger.exception(f"[AI-SERVICE] AI generation exception details")
            logger.info(f"[AI-SERVICE] ==============================================")
            return None
    
    def generate_preview_message(
        self,
        business,  # YelpBusiness object
        # All AI behavior controlled via Custom Instructions (location, response time, business data, style)
        custom_prompt: Optional[str] = None,
        max_length: Optional[int] = None,
        custom_preview_text: Optional[str] = None,  # 🎯 Додаємо новий параметр
        business_ai_settings: Optional['AutoResponseSettings'] = None
    ) -> str:
        """Генерує превʼю повідомлення для тестування налаштувань"""
        
        if not self.is_available():
            return "AI service not available. Please check your settings."
        
        # 🎯 НОВА СПРОЩЕНА АРХІТЕКТУРА AI СИСТЕМИ
        logger.info(f"[AI-SERVICE] 🎯 SIMPLIFIED AI: Vector Search → Custom Instructions")
        logger.info(f"[AI-SERVICE] Business: {business.name}")
        logger.info(f"[AI-SERVICE] Has custom_prompt: {bool(custom_prompt)}")
        logger.info(f"[AI-SERVICE] Has custom_preview_text: {bool(custom_preview_text)}")
        
        try:
            # 🎯 STEP 1: СПРОБУЄМО VECTOR SEARCH (якщо є Sample Replies + custom preview text)
            if custom_preview_text and business_ai_settings and business_ai_settings.use_sample_replies:
                logger.info(f"[AI-SERVICE] 🔍 STEP 1: Trying Vector Search (Sample Replies)")
                logger.info(f"[AI-SERVICE] Custom preview text: {custom_preview_text[:100]}...")
                
                try:
                    # Використовуємо Vector Search approach
                    from .models import LeadDetail
                    mock_lead = LeadDetail(
                        lead_id="preview_test",
                        user_display_name="Test Customer",
                        business_id=business.business_id
                    )
                    mock_lead.project = {"additional_info": custom_preview_text}
                    
                    vector_response = self.generate_sample_replies_response(
                        lead_detail=mock_lead,
                        business=business,
                        max_length=None,  # ✅ Auto-detect from Sample Replies examples
                        business_ai_settings=business_ai_settings,
                        use_vector_search=True
                    )
                    
                    if vector_response:
                        logger.info(f"[AI-SERVICE] 🎉 STEP 1 SUCCESS: Vector Search generated response")
                        return vector_response
                    else:
                        logger.info(f"[AI-SERVICE] 📋 STEP 1 FAILED: Vector Search found no results, trying Custom Instructions")
                        
                except Exception as vector_error:
                    logger.warning(f"[AI-SERVICE] ❌ STEP 1 ERROR: Vector Search failed: {vector_error}")
                    logger.info(f"[AI-SERVICE] 🔄 STEP 1 FALLBACK: Using Custom Instructions")
            
            # 🎯 STEP 2: CUSTOM INSTRUCTIONS (Primary prompt approach)
            if not custom_prompt:
                logger.warning(f"[AI-SERVICE] ⚠️ STEP 2: No Custom Instructions provided - using minimal prompt")
                return "Custom Instructions required for AI response generation."
            
            logger.info(f"[AI-SERVICE] 📝 STEP 2: Using Custom Instructions as primary prompt")
            logger.info(f"[AI-SERVICE] Custom prompt length: {len(custom_prompt)} characters")
            
            # 🏢 ПІДГОТОВКА BUSINESS CONTEXT (всі доступні дані для Custom Instructions)
            business_context = {
                "name": business.name,
                "location": business.location or "",
                "time_zone": business.time_zone or "",
                "open_days": business.open_days or "",
                "open_hours": business.open_hours or ""
            }
            
            # Додаємо всі доступні business.details (Custom Instructions сам вибере що використовувати)
            if business.details and isinstance(business.details, dict):
                logger.info(f"[AI-SERVICE] 📋 Business details available for Custom Instructions")
                business_context.update({
                    "rating": business.details.get("rating"),
                    "review_count": business.details.get("review_count"),
                    "categories": business.details.get("categories", []),
                    "phone": business.details.get("display_phone") or business.details.get("phone"),
                    "website": business.details.get("url"),
                    "price": business.details.get("price"),
                    "address": business.details.get("location", {}).get("display_address", []),
                    "city": business.details.get("location", {}).get("city"),
                    "state": business.details.get("location", {}).get("state"),
                    "zip_code": business.details.get("location", {}).get("zip_code"),
                    "transactions": business.details.get("transactions", [])
                })
                
                # Логування доступних даних для Custom Instructions
                available_data = []
                for key, value in business_context.items():
                    if value and key != "name":
                        available_data.append(key)
                logger.info(f"[AI-SERVICE] 📊 Available business data for Custom Instructions: {', '.join(available_data)}")
            else:
                logger.warning(f"[AI-SERVICE] ⚠️ No business details available")
            
            # 🎯 СПРОЩЕНИЙ CONTEXT ДЛЯ CUSTOM INSTRUCTIONS
            customer_text = custom_preview_text or "I need help with your services"
            customer_name = "[Client Name]" 
            business_name = business.name
            
            # Форматуємо всі доступні business data для Custom Instructions
            business_info_parts = []
            
            if business_context.get("location"):
                business_info_parts.append(f"Location: {business_context['location']}")
            
            if business_context.get("rating"):
                rating_str = f"Rating: {business_context['rating']}/5 stars"
                if business_context.get("review_count"):
                    rating_str += f" ({business_context['review_count']} reviews)"
                business_info_parts.append(rating_str)
            
            if business_context.get("categories"):
                categories = business_context["categories"]
                if categories:
                    category_titles = [cat.get('title', str(cat)) if isinstance(cat, dict) else str(cat) for cat in categories[:3]]
                    business_info_parts.append(f"Specializes in: {', '.join(category_titles)}")
            
            if business_context.get("phone"):
                business_info_parts.append(f"Phone: {business_context['phone']}")
            
            if business_context.get("price"):
                business_info_parts.append(f"Price range: {business_context['price']}")
            
            if business_context.get("website"):
                business_info_parts.append(f"Website: {business_context['website']}")
            
            business_info = "\n".join(business_info_parts) if business_info_parts else "Basic business information available."
            
            logger.info(f"[AI-SERVICE] 📋 Formatted business info: {len(business_info_parts)} items")
            logger.info(f"[AI-SERVICE] 💬 Customer text: {customer_text[:50]}...")
            
            # 🎯 СТВОРЮЄМО СПРОЩЕНИЙ PROMPT З CUSTOM INSTRUCTIONS + BUSINESS DATA
            # ✅ Length instruction removed - AI auto-detects natural length from Sample Replies examples
            # No artificial length restrictions for preview
            length_instruction = ""
            
            # 🎯 СПРОЩЕНИЙ PROMPT ГЕНЕРАЦІЯ З CUSTOM INSTRUCTIONS
            simplified_prompt = f"""Customer message:
"{customer_text}"

Customer name: {customer_name}
Business name: {business_name}

Available Business Information:
{business_info}{length_instruction}

{custom_prompt}

Respond to the customer."""
            
            logger.info(f"[AI-SERVICE] 📝 Generated simplified prompt (length: {len(simplified_prompt)} chars)")
            
            # Використовуємо simplified prompt замість складного _create_greeting_prompt
            prompt = simplified_prompt
            
            # Отримання AI налаштувань з business-specific fallback для preview
            ai_config = self._get_ai_settings(business_ai_settings)
            model = ai_config['model']
            temperature = ai_config['temperature']
            
            # Додаткове логування для debug
            logger.info(f"[AI-SERVICE] Selected model: {model}")
            logger.info(f"[AI-SERVICE] Temperature: {temperature}")
            
            # GPT-5 detection (not recommended for customer support)
            if model.startswith('gpt-5'):
                logger.warning(f"[AI-SERVICE] ⚠️ GPT-5 model detected: {model}")
                logger.info(f"[AI-SERVICE] Note: GPT-5 may return empty responses, will auto-fallback to gpt-4o if needed")
            
            # 🎯 AUTO-DETECT LENGTH for preview (no manual restrictions)
            # Give generous token limit to allow natural response length
            # AI will determine natural length based on Sample Replies examples in the prompt
            if max_length is not None and max_length > 0:
                # User explicitly provided max_length - respect it
                estimated_tokens = max(100, max_length // 3)
                message_length = estimated_tokens
                logger.info(f"[AI-SERVICE] Using explicit max_length: {max_length} chars → {estimated_tokens} tokens")
            else:
                # No explicit limit - allow natural length (generous token limit)
                message_length = 500  # ~1500 characters, allows natural response length
                logger.info(f"[AI-SERVICE] 🎯 AUTO-DETECT MODE: Using generous token limit ({message_length}) for natural length")
            
            # 🎯 Для contextual AI analysis використовуємо custom prompt як system prompt
            system_prompt = self._get_system_prompt(custom_prompt)
            
            # Log prompt info
            logger.info(f"[AI-SERVICE] System prompt length: {len(system_prompt)} characters")
            
            # Підготовка повідомлень з урахуванням особливостей моделі
            messages = self._prepare_messages_for_model(model, system_prompt, prompt)
            
            # Підготовка параметрів API з урахуванням обмежень моделі
            api_params = self._get_api_params_for_model(model, messages, message_length, temperature)
            
            logger.info(f"[AI-SERVICE] Making API call with params: {api_params}")
            
            try:
                response = self.client.chat.completions.create(**api_params)
                
                logger.info(f"[AI-SERVICE] Response received successfully")
                logger.info(f"[AI-SERVICE] Response choices count: {len(response.choices)}")
                
                if response.choices and len(response.choices) > 0:
                    choice = response.choices[0]
                    # Детальне логування для діагностики
                    logger.info(f"[AI-SERVICE] Finish reason: {choice.finish_reason}")
                    logger.info(f"[AI-SERVICE] Message role: {choice.message.role}")
                    logger.info(f"[AI-SERVICE] Tool calls: {choice.message.tool_calls}")
                    logger.info(f"[AI-SERVICE] Usage: {response.usage}")
                    
                    content = choice.message.content
                    logger.info(f"[AI-SERVICE] Response content length: {len(content) if content else 0}")
                    logger.info(f"[AI-SERVICE] Response content: '{content}'")
                    
                    if not content:
                        logger.warning(f"[AI-SERVICE] Empty content received from {model}")
                        
                        # 🔄 Спеціальна обробка для GPT-5: reasoning tokens без text output
                        if model.startswith('gpt-5'):
                            logger.warning(f"[AI-SERVICE] ⚠️ GPT-5 ISSUE: Used reasoning tokens but returned no text")
                            logger.info(f"[AI-SERVICE] GPT-5 моделі призначені для reasoning, не для text generation")
                            logger.info(f"[AI-SERVICE] 🔄 Auto-fallback to gpt-4o for better results...")
                            
                            # Retry з gpt-4o
                            try:
                                fallback_params = self._get_api_params_for_model('gpt-4o', messages, message_length, 0.7)
                                logger.info(f"[AI-SERVICE] Retrying with gpt-4o...")
                                fallback_response = self.client.chat.completions.create(**fallback_params)
                                fallback_content = fallback_response.choices[0].message.content
                                
                                if fallback_content:
                                    logger.info(f"[AI-SERVICE] ✅ Fallback successful with gpt-4o")
                                    logger.info(f"[AI-SERVICE] Fallback response length: {len(fallback_content)}")
                                    return fallback_content.strip()
                                    
                            except Exception as fallback_error:
                                logger.error(f"[AI-SERVICE] Fallback to gpt-4o also failed: {fallback_error}")
                        
                        return "Empty response received from AI model."
                    
                    return content.strip()
                else:
                    logger.error(f"[AI-SERVICE] No choices in response from {model}")
                    return "No response choices received from AI model."
                    
            except Exception as api_error:
                logger.error(f"[AI-SERVICE] API call failed for {model}: {api_error}")
                
                # Fallback для GPT-5 моделей до gpt-4o
                if model.startswith('gpt-5'):
                    logger.warning(f"[AI-SERVICE] 🔄 GPT-5 failed, trying fallback to gpt-4o")
                    try:
                        fallback_params = self._get_api_params_for_model('gpt-4o', messages, message_length, temperature)
                        logger.info(f"[AI-SERVICE] Making fallback API call with gpt-4o")
                        
                        fallback_response = self.client.chat.completions.create(**fallback_params)
                        content = fallback_response.choices[0].message.content
                        
                        if content:
                            logger.info(f"[AI-SERVICE] ✅ Fallback successful with gpt-4o")
                            return content.strip()
                        else:
                            logger.error(f"[AI-SERVICE] Fallback also returned empty content")
                            return "Fallback model also returned empty response."
                            
                    except Exception as fallback_error:
                        logger.error(f"[AI-SERVICE] Fallback to gpt-4o also failed: {fallback_error}")
                        return f"Both {model} and fallback failed: {str(api_error)}"
                else:
                    # Для інших моделей просто повертаємо помилку
                    return f"API call failed: {str(api_error)}"
            
        except Exception as e:
            logger.error(f"[AI-SERVICE] Error generating preview: {e}")
            return f"Error generating preview: {str(e)}"

    def _prepare_messages_for_model(self, model: str, system_prompt: str, user_prompt: str) -> list:
        """Підготовка повідомлень з урахуванням особливостей різних моделей"""
        
        if model.startswith("o1"):
            # o1 моделі не підтримують system role
            # Комбінуємо system prompt з user prompt
            combined_prompt = f"{system_prompt}\n\nUser request: {user_prompt}"
            logger.info(f"[AI-SERVICE] o1 model detected: combining system and user prompts")
            return [{"role": "user", "content": combined_prompt}]
        else:
            # Стандартні моделі підтримують system role
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

    def _get_api_params_for_model(self, model: str, messages: list, max_tokens: int, temperature: float) -> dict:
        """Отримання параметрів API з урахуванням обмежень моделі"""
        
        params = {
            "model": model,
            "messages": messages
        }
        
        if model.startswith("o1"):
            # o1 моделі не підтримують temperature та max_tokens
            logger.info(f"[AI-SERVICE] o1 model: skipping temperature and max_tokens parameters")
        elif model.startswith("gpt-5"):
            # ✅ GPT-5 використовує max_completion_tokens замість max_tokens
            params["max_completion_tokens"] = max_tokens
            # GPT-5 має fixed temperature = 1.0 (не підтримує налаштування)
            logger.info(f"[AI-SERVICE] GPT-5 model: using max_completion_tokens={max_tokens} (fixed temperature=1.0)")
        else:
            # Стандартні моделі підтримують max_tokens
            params["max_tokens"] = max_tokens
            params["temperature"] = temperature
            logger.info(f"[AI-SERVICE] Standard model: using max_tokens and temperature")
        
        return params
    
    def _prepare_lead_context(
        self, 
        lead_detail: LeadDetail, 
        business: Optional[YelpBusiness],
        is_off_hours: bool,
        # All AI behavior controlled via Custom Instructions (location, response time, business data, style)
        business_data_settings: Optional[Dict[str, bool]] = None,
        custom_prompt: Optional[str] = None
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
        
        # Отримуємо оригінальний текст клієнта для contextual analysis
        original_customer_text = self._get_lead_text(lead_detail)
        
        # Базова інформація про клієнта
        context = {
            "customer_name": lead_detail.user_display_name or "there",
            "services": ", ".join(lead_detail.project.get("job_names", [])) if lead_detail.project else "",
            "phone_number": getattr(lead_detail, 'phone_number', None),
            "additional_info": getattr(lead_detail, 'additional_notes', '') or '',
            "created_at": lead_detail.created_at if hasattr(lead_detail, 'created_at') else timezone.now(),
            "is_off_hours": is_off_hours,
            # mention_response_time removed - controlled via Custom Instructions
            "original_customer_text": original_customer_text,  # 🎯 Для contextual AI analysis
            "business_id": business.business_id if business else None  # 🕐 Для time-based greeting
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
            "business_location": business.location if business.location else "",
            "business_data": business_data,
            "business_data_settings": business_data_settings
        })
        
        # 🎯 CONTEXTUAL AI: Більше не потрібен парсинг плейсхолдерів 
        # AI сам аналізує original_customer_text згідно з custom prompt
        
        return context
    
    def _get_system_prompt(self, custom_prompt: Optional[str] = None) -> str:
        """Отримує системний промпт (тільки кастомний)"""
        if custom_prompt:
            return custom_prompt
        
        ai_settings = AISettings.objects.first()
        if ai_settings and ai_settings.base_system_prompt:
            return ai_settings.base_system_prompt
        
        # Повертаємо порожній рядок замість захардкодженого промпта
        return ""
    
    def _create_greeting_prompt(
        self, 
        context: Dict[str, Any], 
        # response_style removed - AI learns style from PDF examples
        custom_prompt: Optional[str] = None,
        max_length: Optional[int] = None  # 🔧 Додаємо max_length для інструкцій про довжину
    ) -> str:
        """Створює промпт для генерації вітального повідомлення з повними бізнес-даними"""
        
        # 🎯 CONTEXTUAL AI ANALYSIS: Якщо є custom prompt - використовуємо його як system prompt
        if custom_prompt:
            # Отримуємо оригінальний текст клієнта
            customer_text = context.get('original_customer_text', '')
            customer_name = context.get('customer_name', 'there')
            business_name = context.get('business_name', 'our business')
            
            # 🕐 TIME-BASED GREETING: Додаємо правильний greeting за часом доби
            from .utils import get_time_based_greeting
            business_id = context.get('business_id', None)
            time_greeting = get_time_based_greeting(business_id)
            logger.info(f"[AI-SERVICE] 🕐 Time-based greeting: '{time_greeting}' for business {business_id}")
            
            # Створюємо контекстуальний user prompt для AI аналізу з business data
            business_data = context.get('business_data', {})
            business_data_settings = context.get('business_data_settings', {})
            
            # Формуємо business information для contextual prompt
            business_info_parts = []
            
            # Address information
            if business_data_settings.get('include_address'):
                address_parts = []
                city = business_data.get('city', '')
                state = business_data.get('state', '')
                zip_code = business_data.get('zip_code', '')
                
                # Якщо є окремі компоненти адреси
                if city and state and zip_code:
                    address_parts.append(f"{city}, {state} {zip_code}")
                elif city and state:
                    address_parts.append(f"{city}, {state}")
                elif city:
                    address_parts.append(city)
                
                # Якщо є додаткова адреса з Yelp API (наприклад, вулиця)
                if business_data.get('address'):
                    yelp_address = ", ".join(str(addr) for addr in business_data['address']) if isinstance(business_data['address'], list) else str(business_data['address'])
                    # Додаємо тільки якщо це не дублює city
                    if yelp_address and yelp_address.lower() != city.lower():
                        address_parts.insert(0, yelp_address)  # Вулиця спереду
                
                if address_parts:
                    full_address = ", ".join(address_parts)
                    business_info_parts.append(f"Address: {full_address}")
            
            # Phone
            if business_data_settings.get('include_phone') and business_data.get('phone'):
                business_info_parts.append(f"Phone: {business_data['phone']}")
            
            # Rating and reviews
            if business_data_settings.get('include_rating') and business_data.get('rating'):
                rating = business_data['rating']
                review_count = business_data.get('review_count', 0)
                if business_data_settings.get('include_reviews_count') and review_count > 0:
                    business_info_parts.append(f"Rating: {rating}/5 stars ({review_count} reviews)")
                else:
                    business_info_parts.append(f"Rating: {rating}/5 stars")
            
            # Categories
            if business_data_settings.get('include_categories') and business_data.get('categories'):
                category_titles = []
                for cat in business_data['categories'][:3]:
                    if isinstance(cat, dict):
                        category_titles.append(cat.get('title', cat.get('alias', str(cat))))
                    else:
                        category_titles.append(str(cat))
                if category_titles:
                    business_info_parts.append(f"Specializes in: {', '.join(category_titles)}")
            
            # Website
            if business_data_settings.get('include_website') and business_data.get('website'):
                business_info_parts.append("Website available")
            
            # Price range
            if business_data_settings.get('include_price_range') and business_data.get('price'):
                business_info_parts.append(f"Price range: {business_data['price']}")
            
            # Business hours and status
            if business_data_settings.get('include_hours'):
                if context.get('is_off_hours'):
                    business_info_parts.append("Currently closed - outside business hours")
                elif business_data.get('is_open_now'):
                    business_info_parts.append("Currently open")
            
            # Transactions/services
            if business_data_settings.get('include_transactions') and business_data.get('transactions'):
                transaction_items = [str(item) for item in business_data['transactions'][:3]]
                if transaction_items:
                    business_info_parts.append(f"Available services: {', '.join(transaction_items)}")
            
            business_info = "\n".join(business_info_parts) if business_info_parts else "No additional business information configured."
            
            # 🔍 VECTOR SEARCH CONTEXT for Custom Preview Text
            vector_context = ""
            if context.get('sample_replies_context'):
                logger.info(f"[AI-SERVICE] 🔍 Adding vector search context to preview prompt")
                similar_chunks = context['sample_replies_context']
                
                vector_parts = []
                for i, chunk in enumerate(similar_chunks[:3]):  # Top 3 most similar
                    similarity_score = chunk['similarity_score']
                    chunk_type = chunk['chunk_type']
                    content = chunk['content']
                    
                    vector_parts.append(
                        f"Similar Example {i+1} (similarity: {similarity_score:.2f}, type: {chunk_type}):\n{content}\n"
                    )
                
                vector_context = f"""
RELEVANT SAMPLE REPLIES (found via vector search):
{chr(10).join(vector_parts)}

STYLE GUIDANCE: Use the tone, approach, and communication style from the similar examples above. The higher the similarity score, the more closely you should match that style.
"""
                logger.info(f"[AI-SERVICE] 📝 Added {len(similar_chunks)} vector chunks to preview context")
            
            # ✅ Length instruction - NO HARD LIMITS, let AI determine natural length
            # System uses generous token limit to allow natural conversation length
            length_instruction = ""
            
            contextual_prompt = f"""Customer message:
"{customer_text}"

Customer name: {customer_name}
Business name: {business_name}
Time-appropriate greeting: {time_greeting}

Business Information:
{business_info}{vector_context}{length_instruction}

IMPORTANT: Start your response with the time-appropriate greeting ({time_greeting}) followed by the customer's name.

Customer inquiry requires response based on the information above."""
            
            logger.info(f"[AI-SERVICE] 🎯 Using contextual AI analysis with custom prompt")
            logger.info(f"[AI-SERVICE] Customer text length: {len(customer_text)} characters")
            logger.info(f"[AI-SERVICE] Business info parts: {len(business_info_parts)}")
            logger.info(f"[AI-SERVICE] Time greeting included: {time_greeting}")
            
            return contextual_prompt
        
        # 🔍 БЕЗ CUSTOM INSTRUCTIONS - але перевіряємо чи є Vector Search context
        customer_text = context.get('original_customer_text', '')
        customer_name = context.get('customer_name', 'there')
        business_name = context.get('business_name', 'our business')
        
        # Якщо є Vector Search context - використовуємо його навіть без custom prompt
        if context.get('sample_replies_context'):
            logger.info(f"[AI-SERVICE] 🔍 No custom instructions, but using Vector Search context for prompt")
            
            vector_context = ""
            similar_chunks = context['sample_replies_context']
            
            vector_parts = []
            for i, chunk in enumerate(similar_chunks[:3]):  # Top 3 most similar
                similarity_score = chunk['similarity_score']
                chunk_type = chunk['chunk_type']
                content = chunk['content']
                
                vector_parts.append(
                    f"Example {i+1} (similarity: {similarity_score:.2f}):\n{content}\n"
                )
            
            vector_context = f"""
RELEVANT SAMPLE REPLIES:
{chr(10).join(vector_parts)}
"""
            
            # ✅ No hard length limits - AI determines natural length
            length_instruction = ""
            
            basic_prompt = f"""Customer message:
"{customer_text}"

Customer name: {customer_name}
Business name: {business_name}
{vector_context}{length_instruction}

Respond to the customer using the examples above as style reference."""
            
            logger.info(f"[AI-SERVICE] ✅ Using Vector Search context without custom prompt")
            return basic_prompt
        
        # 🔧 Якщо немає ні custom prompt, ні vector context - використовуємо базовий prompt з business data
        logger.info(f"[AI-SERVICE] 💼 No custom instructions/vector context - using basic prompt with business data")
        
        # Формуємо базовий prompt з business data
        customer_text = context.get('original_customer_text', '')
        customer_name = context.get('customer_name', 'there')
        business_name = context.get('business_name', 'our business')
        business_data = context.get('business_data', {})
        business_data_settings = context.get('business_data_settings', {})
        
        # Формуємо business information для базового prompt
        business_info_parts = []
        
        # Rating and reviews
        if business_data_settings.get('include_rating') and business_data.get('rating'):
            rating = business_data['rating']
            review_count = business_data.get('review_count', 0)
            if business_data_settings.get('include_reviews_count') and review_count > 0:
                business_info_parts.append(f"Rating: {rating}/5 stars ({review_count} reviews)")
            else:
                business_info_parts.append(f"Rating: {rating}/5 stars")
        
        # Categories
        if business_data_settings.get('include_categories') and business_data.get('categories'):
            category_titles = []
            for cat in business_data['categories'][:3]:
                if isinstance(cat, dict):
                    category_titles.append(cat.get('title', cat.get('alias', str(cat))))
                else:
                    category_titles.append(str(cat))
            if category_titles:
                business_info_parts.append(f"Specializes in: {', '.join(category_titles)}")
        
        # Phone
        if business_data_settings.get('include_phone') and business_data.get('phone'):
            business_info_parts.append(f"Phone: {business_data['phone']}")
        
        # Price range
        if business_data_settings.get('include_price_range') and business_data.get('price'):
            business_info_parts.append(f"Price range: {business_data['price']}")
        
        business_info = "\n".join(business_info_parts) if business_info_parts else "No additional business information configured."
        
        # ✅ No hard length limits - AI determines natural length
        length_instruction = ""
        
        basic_prompt = f"""Customer message:
"{customer_text}"

Customer name: {customer_name}
Business name: {business_name}

Business Information:
{business_info}{length_instruction}

Respond to the customer using the business information above."""
        
        logger.info(f"[AI-SERVICE] ✅ Generated basic prompt with business data (length instructions: {bool(max_length)})")
        return basic_prompt
    
    def _fallback_message(self, context: Dict[str, Any]) -> str:
        """Fallback повідомлення якщо AI не працює - мінімальне без захардкоджених даних"""
        # Повертаємо мінімальне повідомлення без захардкоджених шаблонів
        name = context.get('customer_name', '')
        business_name = context.get('business_name', '')
        
        # Мінімальне повідомлення що не заважає custom prompt логіці
        if name and name != 'there' and business_name:
            return f"Hi {name}! Thank you for contacting {business_name}."
        elif business_name:
            return f"Thank you for contacting {business_name}."
        else:
            return "Thank you for your message."
    
    def _parse_lead_data(self, lead_detail: LeadDetail, custom_prompt: Optional[str] = None) -> Dict[str, str]:
        """🤖 AI-powered парсинг що автоматично витягує будь-які плейсхолдери з custom prompt"""
        
        # Отримуємо текст з additional_info або з job_names
        text = self._get_lead_text(lead_detail)
        
        if not text:
            logger.info(f"[AI-SERVICE] No text found in lead data")
            return {}
        
        logger.info(f"[AI-SERVICE] AI-powered parsing from text: {text[:100]}...")
        
        # Якщо немає custom prompt - використовуємо fallback парсинг
        if not custom_prompt:
            return self._fallback_parsing(text)
        
        # Витягуємо плейсхолдери з custom prompt
        placeholders = re.findall(r'\{(\w+)\}', custom_prompt)
        
        if not placeholders:
            logger.info(f"[AI-SERVICE] No placeholders found in custom prompt")
            return self._fallback_parsing(text)
        
        logger.info(f"[AI-SERVICE] Found placeholders: {placeholders}")
        
        # Пробуємо AI extraction
        try:
            return self._ai_extract_fields(text, placeholders)
        except Exception as e:
            logger.error(f"[AI-SERVICE] AI extraction failed: {e}")
            return self._fallback_parsing(text)
    
    def _get_lead_text(self, lead_detail: LeadDetail) -> str:
        """
        📝 Отримує ПОВНИЙ текст від клієнта для AI аналізу
        
        Працює так само як Custom Preview Text - повний, детальний контекст
        """
        from .models import LeadEvent
        
        logger.info(f"[AI-SERVICE] 🔍 EXTRACTING CUSTOMER TEXT for lead {lead_detail.lead_id}")
        
        # 🎯 ПРІОРИТЕТ: Шукаємо TEXT івент від CONSUMER
        all_consumer_texts = LeadEvent.objects.filter(
            lead_id=lead_detail.lead_id,
            event_type="TEXT",
            user_type="CONSUMER",
            from_backend=False
        ).order_by('time_created')
        
        logger.info(f"[AI-SERVICE] Found {all_consumer_texts.count()} CONSUMER TEXT events")
        
        # Детальне логування для діагностики
        for i, event in enumerate(all_consumer_texts[:3]):
            logger.info(f"[AI-SERVICE] Event {i+1}: ID={event.event_id}")
            logger.info(f"[AI-SERVICE]   - Text length: {len(event.text)} chars")
            logger.info(f"[AI-SERVICE]   - Text preview: {event.text[:100]}...")
            logger.info(f"[AI-SERVICE]   - Time: {event.time_created}")
        
        first_consumer_text = all_consumer_texts.first()
        
        if first_consumer_text and first_consumer_text.text:
            customer_text = first_consumer_text.text
            logger.info(f"[AI-SERVICE] ✅ SUCCESS: Using TEXT event from CONSUMER")
            logger.info(f"[AI-SERVICE] - Full text length: {len(customer_text)} characters")
            logger.info(f"[AI-SERVICE] - Preview: {customer_text[:200]}...")
            return customer_text
        
        # 🔄 FALLBACK: Формуємо структурований контекст з project data
        # (як в Yelp TEXT event format)
        logger.warning(f"[AI-SERVICE] ⚠️ No TEXT event found, building structured context")
        
        project_data = lead_detail.project or {}
        context_parts = []
        
        # Базова структура як у Yelp
        context_parts.append("Hi there! Could you help me with my project? Here are my answers to Yelp's questions regarding my project:")
        
        # Job names
        job_names = project_data.get("job_names", [])
        if job_names:
            context_parts.append(f"\n\nWhat type of contracting service do you need?\n{', '.join(job_names)}")
        
        # Survey answers
        survey_answers = project_data.get("survey_answers", [])
        for answer in survey_answers:
            question = answer.get("question_text", "")
            answer_text = answer.get("answer_text", [])
            if question and answer_text:
                if isinstance(answer_text, list):
                    answer_str = ", ".join(str(a) for a in answer_text)
                else:
                    answer_str = str(answer_text)
                context_parts.append(f"\n\n{question}\n{answer_str}")
        
        # Availability
        availability = project_data.get("availability", {})
        if availability:
            status = availability.get("status", "")
            if status:
                context_parts.append(f"\n\nWhen do you require this service?\n{status}")
        
        # Location
        location = project_data.get("location", {})
        if location:
            postal_code = location.get("postal_code", "")
            if postal_code:
                context_parts.append(f"\n\nIn what location do you need the service?\n{postal_code}")
        
        # Additional info
        additional_info = project_data.get("additional_info", "")
        if additional_info:
            context_parts.append(f"\n\nAdditional details:\n{additional_info}")
        
        structured_text = "".join(context_parts)
        
        if structured_text and len(structured_text) > 50:
            logger.info(f"[AI-SERVICE] ✅ Built structured context from project data")
            logger.info(f"[AI-SERVICE] - Length: {len(structured_text)} characters")
            logger.info(f"[AI-SERVICE] - Preview: {structured_text[:200]}...")
            return structured_text
        
        # Останній fallback
        logger.error(f"[AI-SERVICE] ❌ Could not build any useful context for lead {lead_detail.lead_id}")
        logger.error(f"[AI-SERVICE] Project data: {project_data}")
        return " ".join(job_names) if job_names else "customer inquiry"
    
    def _ai_extract_fields(self, text: str, placeholders: list) -> Dict[str, str]:
        """Використовує AI для витягування конкретних полів з тексту"""
        
        # Не використовуємо захардкоджені промпти для extraction
        extraction_prompt = f"Customer message: {text}"
        
        logger.info(f"[AI-SERVICE] Sending extraction prompt to AI...")
        
        try:
            # Використовуємо standard модель для extraction
            extraction_model = "gpt-4o"
            system_prompt = ""  # Не використовуємо захардкоджені промпти
            
            # Підготовка повідомлень з урахуванням особливостей моделі
            messages = self._prepare_messages_for_model(extraction_model, system_prompt, extraction_prompt)
            
            # Підготовка параметрів API з урахуванням обмежень моделі
            api_params = self._get_api_params_for_model(extraction_model, messages, 200, 0.1)
            
            # Використовуємо той же OpenAI клієнт
            response = self.client.chat.completions.create(**api_params)
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"[AI-SERVICE] AI extraction response: {ai_response}")
            
            # Очищаємо відповідь від можливого markdown
            if ai_response.startswith('```'):
                ai_response = ai_response.split('\n', 1)[1].rsplit('\n', 1)[0]
            
            # Парсимо JSON
            result = json.loads(ai_response)
            
            # Валідуємо результат
            if isinstance(result, dict):
                # Фільтруємо тільки запитувані поля
                filtered_result = {key: str(value) for key, value in result.items() if key in placeholders}
                logger.info(f"[AI-SERVICE] ✅ AI extraction successful: {filtered_result}")
                return filtered_result
            else:
                logger.warning(f"[AI-SERVICE] AI returned non-dict result: {result}")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"[AI-SERVICE] Failed to parse AI JSON response: {e}")
            return {}
        except Exception as e:
            logger.error(f"[AI-SERVICE] AI extraction error: {e}")
            return {}
    
    def _fallback_parsing(self, text: str) -> Dict[str, str]:
        """Fallback парсинг для базових полів (contracting бізнес)"""
        
        result = {}
        text_lower = text.lower()
        
        # Базовий парсинг service_type
        if "structural repair" in text_lower or "structure repair" in text_lower:
            result["service_type"] = "Structural repair"
        elif "remodeling" in text_lower or "remodel" in text_lower:
            result["service_type"] = "Remodeling"
        elif "addition" in text_lower:
            result["service_type"] = "Additions to an existing structure"
        elif "new structure" in text_lower or "new construction" in text_lower:
            result["service_type"] = "New structure construction"
        elif "design" in text_lower:
            result["service_type"] = "Construction design services"
        
        # Базовий парсинг sub_option для structural repair
        if result.get("service_type") == "Structural repair":
            if "foundation" in text_lower:
                result["sub_option"] = "Foundation"
            elif "roof" in text_lower:
                result["sub_option"] = "Roof frame"
            elif "wall" in text_lower:
                result["sub_option"] = "Walls"
        
        # Базовий парсинг timeline
        if "as soon as possible" in text_lower or "asap" in text_lower:
            result["timeline"] = "As soon as possible"
        elif "flexible" in text_lower:
            result["timeline"] = "I'm flexible"
        
        # Базовий парсинг ZIP
        zip_match = re.search(r'\b\d{5}\b', text)
        if zip_match:
            result["zip"] = zip_match.group()
        
        logger.info(f"[AI-SERVICE] 🔄 Fallback parsing result: {result}")
        return result 

    def generate_sample_replies_response(
        self, 
        lead_detail: LeadDetail, 
        business: Optional[YelpBusiness] = None,
        max_length: Optional[int] = None,
        business_ai_settings: Optional['AutoResponseSettings'] = None,
        use_vector_search: bool = True
    ) -> Optional[str]:
        """🔍 Режим 2: Генерує відповідь на основі векторного пошуку Sample Replies (тільки для AI Generated)"""
        
        if not business:
            logger.warning("[AI-SERVICE] No business provided for Mode 2 vector search")
            return None
        
        logger.info(f"[AI-SERVICE] ========== MODE 2: VECTOR SAMPLE REPLIES AI GENERATION ==========")
        logger.info(f"[AI-SERVICE] Lead ID: {lead_detail.lead_id}")
        logger.info(f"[AI-SERVICE] Business: {business.name} ({business.business_id})")
        logger.info(f"[AI-SERVICE] Use vector search: {use_vector_search}")
        
        if not self.is_available():
            logger.error("[AI-SERVICE] ❌ OpenAI client not available")
            return None
        
        if not self.check_rate_limit():
            logger.warning("[AI-SERVICE] ⚠️ Rate limit exceeded, skipping Sample Replies AI generation")
            return None
        
        try:
            # Отримуємо текст ліда для пошуку
            lead_inquiry = self._get_lead_text(lead_detail)
            
            if not lead_inquiry:
                logger.warning("[AI-SERVICE] No lead inquiry text found")
                return None
            
            logger.info(f"[AI-SERVICE] Lead inquiry: {lead_inquiry[:200]}...")
            
            customer_name = lead_detail.user_display_name or "there"
            # ✅ Auto-detect response length from Sample Replies examples (no default 160)
            response_length = max_length  # None means auto-detect in vector_search_service
            logger.info(f"[AI-SERVICE] Response length setting: {response_length if response_length else 'AUTO-DETECT from examples'}")
            
            if use_vector_search:
                # 🔍 ВЕКТОРНИЙ ПОШУК: Знаходимо найбільш схожі чанки
                try:
                    from .vector_search_service import vector_search_service
                    
                    # 🎯 НОВИЙ ПІДХІД: Inquiry→Response pair matching
                    inquiry_response_pairs = vector_search_service.search_inquiry_response_pairs(
                        query_text=lead_inquiry,
                        business_id=business.business_id,
                        location_id=None,  # TODO: Add location support if needed
                        limit=business_ai_settings.vector_search_limit if business_ai_settings else 5,
                        similarity_threshold=business_ai_settings.vector_similarity_threshold if business_ai_settings else 0.6
                    )
                    
                    if not inquiry_response_pairs:
                        logger.warning("[AI-SERVICE] ⚠️ No similar inquiry→response pairs found via vector search")
                        logger.info("[AI-SERVICE] 🔄 Returning None to trigger fallback to Custom Instructions")
                        logger.info("[AI-SERVICE] System will use standard AI generation with Custom Instructions")
                        return None
                    
                    logger.info(f"[AI-SERVICE] Found {len(inquiry_response_pairs)} inquiry→response pairs via vector search")
                    for i, pair in enumerate(inquiry_response_pairs[:3]):
                        logger.info(f"[AI-SERVICE] Pair {i+1}: similarity={pair['pair_similarity']:.3f}, quality={pair['pair_quality']}")
                        logger.info(f"[AI-SERVICE]   Inquiry: {pair['inquiry']['content'][:80]}...")
                        logger.info(f"[AI-SERVICE]   Response: {pair['response']['content'][:80]}...")
                    
                    # Отримуємо Custom Instructions з business settings
                    custom_instructions = None
                    if business_ai_settings and business_ai_settings.ai_custom_prompt:
                        custom_instructions = business_ai_settings.ai_custom_prompt
                        logger.info(f"[AI-SERVICE] ✅ Custom Instructions available ({len(custom_instructions)} chars)")
                    else:
                        logger.warning(f"[AI-SERVICE] ⚠️ No Custom Instructions - using default prompt")
                    
                    # 🤖 ГЕНЕРАЦІЯ КОНТЕКСТУАЛЬНОЇ ВІДПОВІДІ З ПАР
                    contextual_response = vector_search_service.generate_contextual_response_from_pairs(
                        lead_inquiry=lead_inquiry,
                        customer_name=customer_name,
                        inquiry_response_pairs=inquiry_response_pairs,
                        business_name=business.name,
                        max_response_length=response_length,
                        custom_instructions=custom_instructions  # ✅ ПЕРЕДАЄМО Custom Instructions
                    )
                    
                    if contextual_response:
                        logger.info(f"[AI-SERVICE] 🎉 MODE 2 VECTOR: Generated contextual response:")
                        logger.info(f"[AI-SERVICE] - Length: {len(contextual_response)} chars")
                        logger.info(f"[AI-SERVICE] - Response: '{contextual_response}'")
                        logger.info(f"[AI-SERVICE] - Based on {len(inquiry_response_pairs)} inquiry→response pairs")
                        logger.info(f"[AI-SERVICE] ==============================================")
                        
                        return contextual_response
                    else:
                        logger.warning("[AI-SERVICE] Contextual response generation failed")
                        return None
                        
                except Exception as vector_error:
                    logger.error(f"[AI-SERVICE] Vector search failed: {vector_error}")
                    logger.warning("[AI-SERVICE] Falling back to legacy Sample Replies method...")
                    # Fallback to legacy method if vector search fails
                    use_vector_search = False
            
            # 📄 LEGACY FALLBACK: Використовуємо старий метод з повним текстом
            if not use_vector_search and business_ai_settings and business_ai_settings.sample_replies_content:
                logger.info("[AI-SERVICE] Using legacy Sample Replies method as fallback...")
                return self._generate_legacy_sample_replies_response(
                    lead_detail, business, business_ai_settings.sample_replies_content, 
                    response_length, business_ai_settings
                )
            
            logger.warning("[AI-SERVICE] No Sample Replies available for Mode 2")
            return None
            
        except Exception as e:
            logger.error(f"[AI-SERVICE] ❌ Error in Sample Replies generation (Mode 2): {e}")
            logger.exception("Sample replies generation error details")
            return None
    
    def _generate_legacy_sample_replies_response(
        self,
        lead_detail: LeadDetail,
        business: YelpBusiness,
        sample_replies_content: str,
        max_length: int,
        business_ai_settings: 'AutoResponseSettings'
    ) -> Optional[str]:
        """Legacy метод генерації з повним Sample Replies текстом (fallback)"""
        
        try:
            lead_inquiry = self._get_lead_text(lead_detail)
            customer_name = lead_detail.user_display_name or "there"
            
            # Отримуємо AI налаштування
            ai_config = self._get_ai_settings(business_ai_settings)
            model = ai_config['model']
            temperature = ai_config['temperature']
            
            # Використовуємо business custom prompt замість захардкодженого
            system_prompt = custom_prompt if custom_prompt else ""
            
            # Додаємо sample replies як контекст без захардкоджених інструкцій
            if system_prompt:
                system_prompt += f"""

SAMPLE REPLIES FOR REFERENCE:
{sample_replies_content}"""
            else:
                system_prompt = f"""SAMPLE REPLIES FOR REFERENCE:
{sample_replies_content}"""
            
            user_prompt = f"""Customer: {customer_name}
Inquiry: "{lead_inquiry}"

Respond based on the sample replies context provided."""
            
            # Підготовка та виклик API
            messages = self._prepare_messages_for_model(model, system_prompt, user_prompt)
            api_params = self._get_api_params_for_model(model, messages, max_length, temperature)
            
            response = self.client.chat.completions.create(**api_params)
            ai_message = response.choices[0].message.content.strip()
            
            logger.info(f"[AI-SERVICE] 📄 Legacy Sample Replies response: {ai_message}")
            return ai_message
            
        except Exception as e:
            logger.error(f"[AI-SERVICE] Legacy Sample Replies generation failed: {e}")
            return None