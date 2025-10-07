"""
🔍 Vector Search Service for Sample Replies
Семантичний пошук по PDF чанках з pgvector та генерація контекстуальних відповідей
"""

import logging
from typing import List, Dict, Optional, Tuple
from django.db import connection
from django.db.models import Q
import openai
import os

logger = logging.getLogger(__name__)

class VectorSearchService:
    """Сервіс для семантичного пошуку через sample reply chunks"""
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """Ініціалізація OpenAI клієнта для query ембедінгів"""
        try:
            from .models import AISettings
            
            # Try environment variable first
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                # Try database settings
                ai_settings = AISettings.objects.first()
                if ai_settings and ai_settings.openai_api_key:
                    openai_api_key = ai_settings.openai_api_key
            
            if openai_api_key:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("[VECTOR-SEARCH] OpenAI client initialized successfully")
            else:
                logger.error("[VECTOR-SEARCH] No OpenAI API key found")
                
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")
    
    def generate_query_embedding(self, query_text: str) -> List[float]:
        """Генерує ембедінг для пошукового запиту"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        try:
            logger.info(f"[VECTOR-SEARCH] Generating embedding for query: {query_text[:100]}...")
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=[query_text],
                dimensions=1536
            )
            
            embedding = response.data[0].embedding
            logger.info(f"[VECTOR-SEARCH] Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")
            raise
    
    def _get_vector_search_settings(self, business_id: str, phone_available: bool = False) -> Dict:
        """Отримує налаштування vector search з AutoResponseSettings"""
        try:
            from .models import AutoResponseSettings, YelpBusiness
            
            business = YelpBusiness.objects.get(business_id=business_id)
            settings = AutoResponseSettings.objects.filter(
                business=business,
                phone_available=phone_available
            ).first()
            
            if settings:
                return {
                    'similarity_threshold': settings.vector_similarity_threshold,
                    'search_limit': settings.vector_search_limit,
                    'chunk_types': settings.vector_chunk_types if settings.vector_chunk_types else None
                }
            else:
                # Fallback значення
                return {
                    'similarity_threshold': 0.6,
                    'search_limit': 5,
                    'chunk_types': None
                }
                
        except Exception as e:
            logger.warning(f"[VECTOR-SEARCH] Could not load settings for {business_id}: {e}")
            # Fallback значення
            return {
                'similarity_threshold': 0.6,
                'search_limit': 5,
                'chunk_types': None
            }
    
    def search_similar_chunks(
        self,
        query_text: str,
        business_id: str,
        location_id: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.6,
        chunk_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Шукає схожі чанки за допомогою векторної схожості
        
        Args:
            query_text: Текст запиту ліда для пошуку
            business_id: Фільтр по business ID
            location_id: Опціональний фільтр локації
            limit: Максимальна кількість результатів
            similarity_threshold: Мінімальний рівень косинусної схожості
            chunk_types: Фільтр по типах чанків (inquiry, response, example, general)
            
        Returns:
            Список схожих чанків з оцінками схожості та метаданими
        """
        
        logger.info(f"[VECTOR-SEARCH] ========== VECTOR SEARCH ==========")
        logger.info(f"[VECTOR-SEARCH] Query: {query_text[:200]}...")
        logger.info(f"[VECTOR-SEARCH] Business ID: {business_id}")
        logger.info(f"[VECTOR-SEARCH] Location ID: {location_id}")
        logger.info(f"[VECTOR-SEARCH] Limit: {limit}")
        logger.info(f"[VECTOR-SEARCH] Similarity threshold: {similarity_threshold}")
        logger.info(f"[VECTOR-SEARCH] Chunk types filter: {chunk_types}")
        
        try:
            # Генерація ембедінгу для запиту
            query_embedding = self.generate_query_embedding(query_text)
            
            logger.info(f"[VECTOR-SEARCH] 🧠 Using Python-based similarity calculation (no giant SQL!)")
            
            # PYTHON-BASED approach: отримуємо chunks і рахуємо similarity
            from .vector_models import VectorChunk
            import numpy as np
            
            # Отримуємо кандидатів для similarity calculation
            chunks_queryset = VectorChunk.objects.select_related('document').filter(
                document__business_id=business_id,
                document__processing_status='completed'
            ).exclude(embedding__isnull=True)
            
            if location_id:
                chunks_queryset = chunks_queryset.filter(document__location_id=location_id)
            
            if chunk_types:
                chunks_queryset = chunks_queryset.filter(chunk_type__in=chunk_types)
                logger.info(f"[VECTOR-SEARCH] Filtering by chunk types: {chunk_types}")
            
            logger.info(f"[VECTOR-SEARCH] 📊 Candidate chunks: {chunks_queryset.count()}")
            
            # Обчислюємо similarity для кожного chunk в Python
            results = []
            query_embedding_np = np.array(query_embedding)
            processed_count = 0
            
            for chunk in chunks_queryset:
                try:
                    if chunk.embedding is not None and len(chunk.embedding) == 1536:
                        # Cosine similarity в Python (надійний метод)
                        chunk_embedding_np = np.array(chunk.embedding)
                        
                        # Обчислення cosine similarity
                        dot_product = np.dot(chunk_embedding_np, query_embedding_np)
                        norm_chunk = np.linalg.norm(chunk_embedding_np)
                        norm_query = np.linalg.norm(query_embedding_np)
                        
                        if float(norm_chunk) > 0.0 and float(norm_query) > 0.0:
                            similarity = float(dot_product / (norm_chunk * norm_query))
                            processed_count += 1
                            
                            if similarity >= similarity_threshold:
                                results.append({
                                    'chunk_id': chunk.id,
                                    'content': chunk.content,
                                    'page_number': chunk.page_number,
                                    'chunk_index': chunk.chunk_index,
                                    'token_count': chunk.token_count,
                                    'chunk_type': chunk.chunk_type,
                                    'metadata': chunk.metadata,
                                    'filename': chunk.document.filename,
                                    'business_id': chunk.document.business_id,
                                    'location_id': chunk.document.location_id,
                                    'similarity_score': similarity
                                })
                                
                                logger.info(f"[VECTOR-SEARCH] ✅ Chunk {chunk.id}: similarity={similarity:.4f} >= {similarity_threshold}")
                        else:
                            logger.warning(f"[VECTOR-SEARCH] ⚠️ Chunk {chunk.id}: zero norm vectors")
                            
                except Exception as chunk_error:
                    logger.warning(f"[VECTOR-SEARCH] ⚠️ Error processing chunk {chunk.id}: {chunk_error}")
                    continue
            
            logger.info(f"[VECTOR-SEARCH] 📊 Processed {processed_count} chunks with embeddings")
            logger.info(f"[VECTOR-SEARCH] 🎯 Found {len(results)} chunks above threshold {similarity_threshold}")
            
            # Сортуємо за similarity score (найкращі спочатку)
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:limit]
            
            logger.info(f"[VECTOR-SEARCH] 🏆 Returning top {len(results)} results")
            
            # Логування топ результатів
            for i, result in enumerate(results[:3]):
                logger.info(f"[VECTOR-SEARCH] Result {i+1}:")
                logger.info(f"[VECTOR-SEARCH] - Similarity: {result['similarity_score']:.3f}")
                logger.info(f"[VECTOR-SEARCH] - Type: {result['chunk_type']}")
                logger.info(f"[VECTOR-SEARCH] - Content: {result['content'][:100]}...")
                logger.info(f"[VECTOR-SEARCH] - Page: {result['page_number']}")
            
            logger.info(f"[VECTOR-SEARCH] =================================")
            
            return results
                
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")
            logger.exception("Vector search error details")
            return []
    
    def search_inquiry_response_pairs(
        self,
        query_text: str,
        business_id: str,
        location_id: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.6
    ) -> List[Dict]:
        """
        🎯 ПРАВИЛЬНИЙ ПІДХІД: Знаходить схожі inquiry chunks, потім їх парні response chunks
        
        Args:
            query_text: Новий inquiry від клієнта
            business_id: ID бізнесу
            location_id: Опціональний фільтр локації
            limit: Максимальна кількість inquiry→response пар
            similarity_threshold: Мінімальний рівень схожості
            
        Returns:
            Список inquiry→response пар з оцінками схожості
        """
        
        logger.info(f"[VECTOR-SEARCH] ========== INQUIRY→RESPONSE PAIR MATCHING ==========")
        logger.info(f"[VECTOR-SEARCH] Query: {query_text[:200]}...")
        logger.info(f"[VECTOR-SEARCH] Business ID: {business_id}")
        logger.info(f"[VECTOR-SEARCH] Limit: {limit}")
        logger.info(f"[VECTOR-SEARCH] Similarity threshold: {similarity_threshold}")
        
        try:
            # ЕТАП 1: Знайти схожі inquiry chunks
            logger.info(f"[VECTOR-SEARCH] 🔍 ЕТАП 1: Пошук схожих inquiry chunks...")
            
            similar_inquiries = self.search_similar_chunks(
                query_text=query_text,
                business_id=business_id,
                location_id=location_id,
                limit=limit * 2,  # Шукаємо більше inquiry для кращого вибору
                similarity_threshold=similarity_threshold,
                chunk_types=['inquiry']  # ✅ ТІЛЬКИ INQUIRY CHUNKS
            )
            
            if not similar_inquiries:
                logger.warning("[VECTOR-SEARCH] ⚠️ No similar inquiry chunks found above threshold")
                logger.info(f"[VECTOR-SEARCH] 📊 Search parameters:")
                logger.info(f"[VECTOR-SEARCH]   - Query: {query_text[:100]}...")
                logger.info(f"[VECTOR-SEARCH]   - Threshold: {similarity_threshold}")
                logger.info(f"[VECTOR-SEARCH]   - Limit: {limit}")
                logger.info(f"[VECTOR-SEARCH] 💡 Suggestions:")
                logger.info(f"[VECTOR-SEARCH]   - Lower similarity_threshold (e.g., 0.4-0.5)")
                logger.info(f"[VECTOR-SEARCH]   - Add more relevant examples to Sample Replies")
                logger.info(f"[VECTOR-SEARCH]   - Check if Sample Replies cover this topic")
                logger.info(f"[VECTOR-SEARCH] 🔄 System will fallback to Custom Instructions")
                return []
            
            logger.info(f"[VECTOR-SEARCH] Found {len(similar_inquiries)} similar inquiry chunks")
            
            # ЕТАП 2: Знайти парні response chunks
            logger.info(f"[VECTOR-SEARCH] 🔗 ЕТАП 2: Пошук парних response chunks...")
            
            from .vector_models import VectorChunk
            inquiry_response_pairs = []
            
            for inquiry_chunk in similar_inquiries[:limit]:
                try:
                    # Знайти наступний response chunk після цього inquiry
                    inquiry_chunk_obj = VectorChunk.objects.get(id=inquiry_chunk['chunk_id'])
                    
                    # Пошук наступного response chunk в тому ж документі
                    next_response = VectorChunk.objects.filter(
                        document=inquiry_chunk_obj.document,
                        chunk_index__gt=inquiry_chunk_obj.chunk_index,  # Після inquiry
                        chunk_type='response'  # Тільки response
                    ).order_by('chunk_index').first()
                    
                    if next_response:
                        logger.info(f"[VECTOR-SEARCH] ✅ Found pair: inquiry#{inquiry_chunk_obj.chunk_index} → response#{next_response.chunk_index}")
                        
                        pair = {
                            'inquiry': {
                                'similarity_score': inquiry_chunk['similarity_score'],
                                'content': inquiry_chunk['content'],
                                'chunk_index': inquiry_chunk_obj.chunk_index,
                                'chunk_type': 'inquiry'
                            },
                            'response': {
                                'content': next_response.content,
                                'chunk_index': next_response.chunk_index,
                                'chunk_type': 'response',
                                'quality': next_response.metadata.get('chunk_quality', 'basic') if next_response.metadata else 'basic'
                            },
                            'pair_similarity': inquiry_chunk['similarity_score'],  # Базується на inquiry similarity
                            'pair_quality': self._assess_pair_quality(inquiry_chunk['content'], next_response.content)
                        }
                        
                        inquiry_response_pairs.append(pair)
                        
                    else:
                        logger.warning(f"[VECTOR-SEARCH] ⚠️ No response chunk found for inquiry#{inquiry_chunk_obj.chunk_index}")
                        
                except Exception as pair_error:
                    logger.error(f"[VECTOR-SEARCH] Error finding response pair: {pair_error}")
                    continue
            
            logger.info(f"[VECTOR-SEARCH] 🎯 Found {len(inquiry_response_pairs)} complete inquiry→response pairs")
            
            # Сортування за similarity і якістю
            inquiry_response_pairs.sort(key=lambda x: (x['pair_similarity'], x['pair_quality'] == 'excellent'), reverse=True)
            
            # ЕТАП 3: Логування результатів
            logger.info(f"[VECTOR-SEARCH] 📊 INQUIRY→RESPONSE PAIRS RESULTS:")
            for i, pair in enumerate(inquiry_response_pairs[:3]):
                logger.info(f"[VECTOR-SEARCH] Pair {i+1}: similarity={pair['pair_similarity']:.3f}, quality={pair['pair_quality']}")
                logger.info(f"[VECTOR-SEARCH]   Inquiry: {pair['inquiry']['content'][:100]}...")
                logger.info(f"[VECTOR-SEARCH]   Response: {pair['response']['content'][:100]}...")
            
            logger.info(f"[VECTOR-SEARCH] =================================")
            return inquiry_response_pairs
            
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in inquiry→response pair matching: {e}")
            logger.exception("Pair matching error details")
            return []
    
    def _assess_pair_quality(self, inquiry_content: str, response_content: str) -> str:
        """🎯 Оцінює якість inquiry→response пари"""
        
        # Перевіряємо чи response відповідає inquiry
        inquiry_lower = inquiry_content.lower()
        response_lower = response_content.lower()
        
        # Ключові слова з inquiry мають бути згадані в response
        service_keywords = ['roof', 'foundation', 'remodel', 'deck', 'bathroom', 'kitchen', 'addition']
        inquiry_services = [kw for kw in service_keywords if kw in inquiry_lower]
        response_mentions = [kw for kw in inquiry_services if kw in response_lower]
        
        service_match_ratio = len(response_mentions) / len(inquiry_services) if inquiry_services else 0
        
        # Оцінка якості response
        has_professional_greeting = any(x in response_lower for x in ['good afternoon', 'good morning', 'hello', 'hi'])
        has_business_info = any(x in response_lower for x in ['available', 'hours', 'monday', 'friday'])
        has_personal_touch = any(x in response_lower for x in ['talk soon', 'norma', 'best', 'glad'])
        
        quality_score = service_match_ratio + sum([has_professional_greeting, has_business_info, has_personal_touch])
        
        if quality_score >= 3:
            return 'excellent'
        elif quality_score >= 2:
            return 'good'
        else:
            return 'basic'
    
    def generate_contextual_response_from_pairs(
        self,
        lead_inquiry: str,
        customer_name: str,
        inquiry_response_pairs: List[Dict],
        business_name: str = "",
        max_response_length: int = None  # ✅ Зробимо опціональним для auto-detect
    ) -> str:
        """
        🎯 Генерує відповідь на основі inquiry→response пар (ПРАВИЛЬНИЙ ПІДХІД)
        
        Args:
            lead_inquiry: Оригінальний запит клієнта
            customer_name: Ім'я клієнта
            inquiry_response_pairs: Результати inquiry→response pair matching
            business_name: Назва бізнесу
            max_response_length: Максимальна довжина відповіді (None = auto-detect)
            
        Returns:
            Згенерована відповідь у стилі найкращих inquiry→response пар
        """
        
        if not self.openai_client or not inquiry_response_pairs:
            logger.warning("[VECTOR-SEARCH] No OpenAI client or inquiry→response pairs for generation")
            return ""
        
        logger.info(f"[VECTOR-SEARCH] ========== CONTEXTUAL RESPONSE FROM PAIRS ==========")
        logger.info(f"[VECTOR-SEARCH] Lead inquiry: {lead_inquiry[:100]}...")
        logger.info(f"[VECTOR-SEARCH] Customer: {customer_name}")
        logger.info(f"[VECTOR-SEARCH] Business: {business_name}")
        logger.info(f"[VECTOR-SEARCH] Inquiry→Response pairs: {len(inquiry_response_pairs)}")
        
        # 🎯 Автоматичне визначення довжини на основі прикладів
        # Використовуємо response chunks з inquiry_response_pairs
        response_chunks_for_length = []
        for pair in inquiry_response_pairs[:5]:
            if pair.get('response'):
                response_chunks_for_length.append({
                    'chunk_type': 'response',
                    'content': pair['response'].get('content', '')
                })
        
        avg_length, min_length, max_length = self.calculate_average_response_length(response_chunks_for_length)
        
        if max_response_length:
            target_length = min(avg_length, max_response_length)
            logger.info(f"[VECTOR-SEARCH] 📏 Using capped length: {target_length} (max: {max_response_length})")
        else:
            target_length = avg_length
            logger.info(f"[VECTOR-SEARCH] 🎯 Using AUTO-DETECTED length from pairs: {target_length} chars (range: {min_length}-{max_length})")
        
        try:
            # Збирання контексту зі inquiry→response пар
            context_parts = []
            for i, pair in enumerate(inquiry_response_pairs[:3]):  # Топ 3 пари
                similarity_score = pair['pair_similarity']
                pair_quality = pair['pair_quality']
                inquiry_content = pair['inquiry']['content']
                response_content = pair['response']['content']
                
                context_parts.append(
                    f"""EXAMPLE {i+1} (similarity: {similarity_score:.2f}, quality: {pair_quality}):
CUSTOMER INQUIRY: {inquiry_content}
BUSINESS RESPONSE: {response_content}
---"""
                )
            
            context = "\n".join(context_parts)
            
            # Системний промпт для генерації з пар
            system_prompt = f"""You are a professional business communication assistant for {business_name}.

TASK: Generate a personalized response using INQUIRY→RESPONSE pairs as training examples.

METHODOLOGY: You will receive examples showing how the business responds to specific customer inquiries. Study these inquiry→response patterns to understand:
1. How the business addresses different service types
2. The professional tone and communication style used
3. The structure and elements of good responses
4. How to personalize responses while maintaining consistency

TRAINING EXAMPLES (ranked by similarity to current inquiry):
{context}

INSTRUCTIONS:
1. Analyze the new customer inquiry and find the most similar training inquiry
2. Study how the business responded to that similar inquiry
3. Generate a NEW response following the same pattern, tone, LENGTH, and structure
4. Personalize with the customer's name and specific details
5. Match the NATURAL LENGTH shown in examples (approximately {avg_length} characters, ranging {min_length}-{max_length})
6. Maintain the professional, helpful tone shown in examples

CRITICAL: 
- Use the inquiry→response patterns as your guide
- Match the natural response length from the examples (don't artificially shorten or extend)
- The response should feel natural and personal while following the learned communication style"""
            
            # 🕐 Get time-based greeting
            from .utils import get_time_based_greeting
            from .models import YelpBusiness
            
            time_greeting = "Good morning"  # default
            try:
                business_obj = YelpBusiness.objects.filter(name=business_name).first()
                if business_obj:
                    time_greeting = get_time_based_greeting(business_obj.business_id)
            except Exception as e:
                logger.warning(f"[VECTOR-SEARCH] Could not get time greeting: {e}")
            
            logger.info(f"[VECTOR-SEARCH] 🕐 Time-based greeting: '{time_greeting}'")
            
            user_prompt = f"""NEW CUSTOMER INQUIRY:
Customer Name: {customer_name}
Inquiry Text: "{lead_inquiry}"
Business: {business_name}
Time-appropriate greeting: {time_greeting}

IMPORTANT: Start your response with "{time_greeting} {customer_name}" followed by a casual personal touch (e.g., "hope your day's going well").

Based on the training examples above, generate a professional response that:
1. Addresses this specific customer inquiry
2. Follows the communication patterns learned from similar inquiries
3. Matches the tone and style of the most similar business responses
4. Is personalized for {customer_name} and their specific needs"""
            
            logger.info(f"[VECTOR-SEARCH] Generating response from {len(inquiry_response_pairs)} inquiry→response pairs...")
            logger.info(f"[VECTOR-SEARCH] Top pair similarities: {[p['pair_similarity'] for p in inquiry_response_pairs[:3]]}")
            
            # Розрахунок max_tokens на основі target_length
            estimated_tokens = max(50, target_length // 3)
            logger.info(f"[VECTOR-SEARCH] Estimated tokens for {target_length} chars: {estimated_tokens}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Ефективна модель для цього завдання
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=estimated_tokens,  # ✅ Використовуємо автоматично розрахований ліміт
                temperature=0.7
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            logger.info(f"[VECTOR-SEARCH] ==================== GENERATED RESPONSE ====================")
            logger.info(f"[VECTOR-SEARCH] 📤 Response: {generated_response}")
            logger.info(f"[VECTOR-SEARCH] " + "="*60)
            logger.info(f"[VECTOR-SEARCH] 📊 Response length: {len(generated_response)} chars")
            logger.info(f"[VECTOR-SEARCH] 📊 Used {len(inquiry_response_pairs)} pairs")
            
            # 🔍 АНАЛІЗ ДОТРИМАННЯ ПРАВИЛ
            logger.info(f"[VECTOR-SEARCH] ==================== COMPLIANCE ANALYSIS ====================")
            
            # Check 1: Time-based greeting
            has_correct_greeting = generated_response.lower().startswith(time_greeting.lower())
            logger.info(f"[VECTOR-SEARCH] ✅ Rule 1 - Time-based Greeting:")
            logger.info(f"[VECTOR-SEARCH]    Expected: '{time_greeting}'")
            logger.info(f"[VECTOR-SEARCH]    Response starts with it: {has_correct_greeting}")
            if not has_correct_greeting:
                logger.warning(f"[VECTOR-SEARCH]    ⚠️ AI IGNORED time-based greeting!")
                logger.warning(f"[VECTOR-SEARCH]    Response starts with: '{generated_response[:50]}'")
            
            # Check 2: Customer name
            has_name = customer_name.lower() in generated_response.lower() if customer_name != 'there' else True
            logger.info(f"[VECTOR-SEARCH] ✅ Rule 2 - Customer Name:")
            logger.info(f"[VECTOR-SEARCH]    Name used: {has_name}")
            if not has_name and customer_name != 'there':
                logger.warning(f"[VECTOR-SEARCH]    ⚠️ AI FORGOT customer name!")
            
            # Check 3: Length comparison
            logger.info(f"[VECTOR-SEARCH] ✅ Rule 3 - Length Matching:")
            logger.info(f"[VECTOR-SEARCH]    Target length: {target_length} chars")
            logger.info(f"[VECTOR-SEARCH]    Generated length: {len(generated_response)} chars")
            logger.info(f"[VECTOR-SEARCH]    Difference: {abs(len(generated_response) - target_length)} chars")
            
            # Check 4: Signature
            has_signature = '-Ben' in generated_response or '- Ben' in generated_response or generated_response.strip().endswith('Ben')
            logger.info(f"[VECTOR-SEARCH] ✅ Rule 4 - Signature:")
            logger.info(f"[VECTOR-SEARCH]    Signature present: {has_signature}")
            if not has_signature:
                logger.warning(f"[VECTOR-SEARCH]    ⚠️ AI FORGOT signature!")
            
            # Compliance score
            compliance_score = sum([has_correct_greeting, has_name, has_signature])
            logger.info(f"[VECTOR-SEARCH] 📊 COMPLIANCE SCORE: {compliance_score}/3")
            if compliance_score < 3:
                logger.warning(f"[VECTOR-SEARCH] ⚠️ LOW COMPLIANCE - AI not fully following examples!")
            else:
                logger.info(f"[VECTOR-SEARCH] ✅ GOOD COMPLIANCE")
            
            logger.info(f"[VECTOR-SEARCH] ========================================================")
            
            return generated_response
            
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error generating response from pairs: {e}")
            logger.exception("Pair-based response generation error")
            return ""
    
    def calculate_average_response_length(self, similar_chunks: List[Dict]) -> Tuple[int, int, int]:
        """
        🎯 Автоматично визначає оптимальну довжину відповіді на основі прикладів
        
        Returns:
            (avg_length, min_length, max_length) - середня, мінімальна та максимальна довжина
        """
        response_lengths = []
        
        for chunk in similar_chunks:
            # Беремо тільки response chunks
            if chunk.get('chunk_type') == 'response':
                content = chunk.get('content', '')
                # Шукаємо секцію Reply:
                if 'reply:' in content.lower():
                    reply_start = content.lower().find('reply:')
                    reply_text = content[reply_start:].replace('Reply:', '').replace('reply:', '').strip()
                    response_lengths.append(len(reply_text))
                else:
                    # Якщо це чистий response chunk (без маркера)
                    response_lengths.append(len(content))
        
        if not response_lengths:
            logger.warning("[VECTOR-SEARCH] No response chunks found, using default length")
            return (200, 150, 300)  # Розумні дефолти
        
        avg_length = sum(response_lengths) // len(response_lengths)
        min_length = min(response_lengths)
        max_length = max(response_lengths)
        
        logger.info(f"[VECTOR-SEARCH] 📏 Calculated response lengths from {len(response_lengths)} examples:")
        logger.info(f"[VECTOR-SEARCH]   Average: {avg_length} chars")
        logger.info(f"[VECTOR-SEARCH]   Range: {min_length} - {max_length} chars")
        
        return (avg_length, min_length, max_length)
    
    def generate_contextual_response(
        self,
        lead_inquiry: str,
        customer_name: str,
        similar_chunks: List[Dict],
        business_name: str = "",
        max_response_length: int = None  # ✅ Зробимо опціональним
    ) -> str:
        """
        Генерує контекстуальну відповідь на основі схожих sample replies
        
        Args:
            lead_inquiry: Оригінальний запит клієнта
            customer_name: Ім'я клієнта
            similar_chunks: Результати векторного пошуку
            business_name: Назва бізнесу
            max_response_length: Максимальна довжина відповіді
            
        Returns:
            Згенерована відповідь у стилі sample replies
        """
        
        if not self.openai_client or not similar_chunks:
            logger.warning("[VECTOR-SEARCH] No OpenAI client or similar chunks for response generation")
            return ""
        
        logger.info(f"[VECTOR-SEARCH] ========== CONTEXTUAL RESPONSE GENERATION ==========")
        logger.info(f"[VECTOR-SEARCH] Lead inquiry: {lead_inquiry[:100]}...")
        logger.info(f"[VECTOR-SEARCH] Customer: {customer_name}")
        logger.info(f"[VECTOR-SEARCH] Business: {business_name}")
        logger.info(f"[VECTOR-SEARCH] Similar chunks: {len(similar_chunks)}")
        
        try:
            # 🎯 Автоматичне визначення оптимальної довжини на основі прикладів
            avg_length, min_length, max_length = self.calculate_average_response_length(similar_chunks)
            
            # Якщо max_response_length явно вказаний, використовуємо його як обмеження
            if max_response_length:
                # Обмежуємо середнє значення максимумом
                target_length = min(avg_length, max_response_length)
                logger.info(f"[VECTOR-SEARCH] 📏 Using capped length: {target_length} (max: {max_response_length})")
            else:
                # Інакше використовуємо автоматично розраховану довжину
                target_length = avg_length
                logger.info(f"[VECTOR-SEARCH] 🎯 Using AUTO-DETECTED length: {target_length} chars (from examples)")
            
            # Збирання контексту зі схожих чанків
            context_parts = []
            for i, chunk in enumerate(similar_chunks[:5]):  # Використовуємо топ 5 чанків
                similarity_score = chunk['similarity_score']
                chunk_type = chunk['chunk_type']
                content = chunk['content']
                
                context_parts.append(
                    f"Example {i+1} (similarity: {similarity_score:.2f}, type: {chunk_type}):\n{content}\n"
                )
            
            context = "\n".join(context_parts)
            
            # Створення системного промпту для генерації відповіді
            system_prompt = f"""You are a professional business communication assistant for {business_name}.

TASK: Generate a personalized response to a customer inquiry using the most similar sample replies as your style guide.

MOST SIMILAR SAMPLE REPLIES (ranked by semantic similarity):
{context}

INSTRUCTIONS:
1. Analyze the customer inquiry and the similar examples above
2. Generate a NEW response that matches the TONE, STYLE, LENGTH, and APPROACH of the most similar examples
3. Personalize it with the customer's name and specific inquiry details
4. Match the NATURAL LENGTH of responses in the examples (approximately {avg_length} characters, ranging {min_length}-{max_length})
5. Be professional, helpful, and follow the communication patterns learned from the examples
6. Focus especially on the highest similarity examples for style guidance

IMPORTANT: 
- Use the examples as style guides, not templates to copy
- Generate original content that sounds natural and personal
- Match the professionalism, helpfulness, AND TYPICAL LENGTH shown in the examples
- Don't artificially shorten or extend - match the natural conversation length from examples"""
            
            # 🕐 Get time-based greeting
            from .utils import get_time_based_greeting
            from .models import YelpBusiness
            
            time_greeting = "Good morning"  # default
            try:
                business_obj = YelpBusiness.objects.filter(name=business_name).first()
                if business_obj:
                    time_greeting = get_time_based_greeting(business_obj.business_id)
            except Exception as e:
                logger.warning(f"[VECTOR-SEARCH] Could not get time greeting: {e}")
            
            logger.info(f"[VECTOR-SEARCH] 🕐 Time-based greeting: '{time_greeting}'")
            
            user_prompt = f"""Customer Information:
- Name: {customer_name}
- Inquiry: "{lead_inquiry}"
- Business: {business_name}
- Time-appropriate greeting: {time_greeting}

IMPORTANT: Start your response with "{time_greeting} {customer_name}" followed by a casual personal touch.

Based on the similar sample replies ranked above (especially the highest similarity ones), generate a personalized response that addresses this specific customer's inquiry while matching the learned communication style."""
            
            logger.info(f"[VECTOR-SEARCH] Generating contextual response with {len(similar_chunks)} similar examples...")
            logger.info(f"[VECTOR-SEARCH] Top similarity scores: {[c['similarity_score'] for c in similar_chunks[:3]]}")
            
            # Розрахунок max_tokens на основі target_length
            # Використовуємо консервативну конвертацію: 1 token ≈ 3-4 characters
            estimated_tokens = max(50, target_length // 3)
            logger.info(f"[VECTOR-SEARCH] Estimated tokens for {target_length} chars: {estimated_tokens}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Ефективна модель для цього завдання
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=estimated_tokens,  # ✅ Використовуємо автоматично розрахований ліміт
                temperature=0.7
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            logger.info(f"[VECTOR-SEARCH] ✅ Generated contextual response:")
            logger.info(f"[VECTOR-SEARCH] - Length: {len(generated_response)} chars")
            logger.info(f"[VECTOR-SEARCH] - Response: {generated_response}")
            logger.info(f"[VECTOR-SEARCH] - Used {len(similar_chunks)} similar examples")
            logger.info(f"[VECTOR-SEARCH] ========================================")
            
            return generated_response
            
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")
            logger.exception("Response generation error details")
            return ""
    
    def get_chunk_statistics(self, business_id: str, location_id: Optional[str] = None) -> Dict:
        """Отримує статистику про чанки для бізнесу"""
        
        try:
            from .vector_models import VectorDocument, VectorChunk
            
            # Фільтри
            doc_filter = Q(business_id=business_id, processing_status='completed')
            if location_id:
                doc_filter &= Q(location_id=location_id)
            
            documents = VectorDocument.objects.filter(doc_filter)
            
            if not documents.exists():
                return {
                    'total_documents': 0,
                    'total_chunks': 0,
                    'total_tokens': 0,
                    'chunk_types': {},
                    'avg_similarity_ready': False
                }
            
            total_chunks = sum(doc.chunk_count for doc in documents)
            total_tokens = sum(doc.total_tokens for doc in documents)
            
            # Статистика по типах чанків
            chunk_type_stats = {}
            for doc in documents:
                doc_chunk_types = doc.metadata.get('processing_info', {}).get('chunks_by_type', {})
                for chunk_type, count in doc_chunk_types.items():
                    chunk_type_stats[chunk_type] = chunk_type_stats.get(chunk_type, 0) + count
            
            return {
                'total_documents': len(documents),
                'total_chunks': total_chunks,
                'total_tokens': total_tokens,
                'chunk_types': chunk_type_stats,
                'avg_similarity_ready': total_chunks > 0,
                'documents': [
                    {
                        'filename': doc.filename,
                        'chunks': doc.chunk_count,
                        'tokens': doc.total_tokens,
                        'created': doc.created_at.isoformat()
                    }
                    for doc in documents
                ]
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'total_tokens': 0,
                'chunk_types': {},
                'avg_similarity_ready': False,
                'error': str(e)
            }
    
    def test_vector_search(
        self,
        business_id: str, 
        test_query: str = "roof repair",
        location_id: Optional[str] = None
    ) -> Dict:
        """Тестовий векторний пошук для діагностики"""
        
        logger.info(f"[VECTOR-SEARCH] ========== TEST VECTOR SEARCH ==========")
        logger.info(f"[VECTOR-SEARCH] Test query: {test_query}")
        logger.info(f"[VECTOR-SEARCH] Business: {business_id}")
        
        try:
            # Отримання налаштувань пошуку
            search_settings = self._get_vector_search_settings(business_id)
            logger.info(f"[VECTOR-SEARCH] Using settings: threshold={search_settings['similarity_threshold']}, limit={search_settings['search_limit']}")
            
            # Отримання статистики
            stats = self.get_chunk_statistics(business_id, location_id)
            
            if stats['total_chunks'] == 0:
                return {
                    'success': False,
                    'message': 'No vector chunks available for this business',
                    'stats': stats
                }
            
            # Тестовий пошук з налаштуваннями
            results = self.search_similar_chunks(
                query_text=test_query,
                business_id=business_id,
                location_id=location_id,
                limit=search_settings['search_limit'],
                similarity_threshold=search_settings['similarity_threshold'],
                chunk_types=search_settings['chunk_types']
            )
            
            if not results:
                return {
                    'success': False,
                    'message': 'No similar chunks found (try lowering similarity threshold)',
                    'stats': stats,
                    'query': test_query
                }
            
            # Генерація тестової відповіді
            test_response = self.generate_contextual_response(
                lead_inquiry=test_query,
                customer_name="Test Customer",
                similar_chunks=results,
                business_name=business_id,
                max_response_length=160
            )
            
            logger.info(f"[VECTOR-SEARCH] ✅ Test completed successfully")
            logger.info(f"[VECTOR-SEARCH] =================================")
            
            return {
                'success': True,
                'message': 'Vector search test completed successfully',
                'stats': stats,
                'query': test_query,
                'results_count': len(results),
                'top_similarity': results[0]['similarity_score'] if results else 0,
                'generated_response': test_response,
                'sample_results': results[:2]  # Топ 2 для preview
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-SEARCH] Error in vector search: {e}")
            return {
                'success': False,
                'message': f'Test failed: {str(e)}',
                'error': str(e)
            }

# Глобальний інстанс
vector_search_service = VectorSearchService()
