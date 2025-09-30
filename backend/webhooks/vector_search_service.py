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
            logger.error(f"[VECTOR-SEARCH] Failed to initialize OpenAI client: {e}")
    
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
            logger.error(f"[VECTOR-SEARCH] Error generating query embedding: {e}")
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
                    if chunk.embedding and len(chunk.embedding) == 1536:
                        # Cosine similarity в Python (надійний метод)
                        chunk_embedding_np = np.array(chunk.embedding)
                        
                        # Обчислення cosine similarity
                        dot_product = np.dot(chunk_embedding_np, query_embedding_np)
                        norm_chunk = np.linalg.norm(chunk_embedding_np)
                        norm_query = np.linalg.norm(query_embedding_np)
                        
                        if norm_chunk > 0 and norm_query > 0:
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
    
    def generate_contextual_response(
        self,
        lead_inquiry: str,
        customer_name: str,
        similar_chunks: List[Dict],
        business_name: str = "",
        max_response_length: int = 160
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
        logger.info(f"[VECTOR-SEARCH] Max length: {max_response_length}")
        
        try:
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
2. Generate a NEW response that matches the TONE, STYLE, and APPROACH of the most similar examples
3. Personalize it with the customer's name and specific inquiry details
4. Keep the response under {max_response_length} characters
5. Be professional, helpful, and follow the communication patterns learned from the examples
6. Focus especially on the highest similarity examples for style guidance

IMPORTANT: 
- Use the examples as style guides, not templates to copy
- Generate original content that sounds natural and personal
- Match the professionalism and helpfulness shown in the examples"""
            
            user_prompt = f"""Customer Information:
- Name: {customer_name}
- Inquiry: "{lead_inquiry}"
- Business: {business_name}

Based on the similar sample replies ranked above (especially the highest similarity ones), generate a personalized response that addresses this specific customer's inquiry while matching the learned communication style."""
            
            logger.info(f"[VECTOR-SEARCH] Generating contextual response with {len(similar_chunks)} similar examples...")
            logger.info(f"[VECTOR-SEARCH] Top similarity scores: {[c['similarity_score'] for c in similar_chunks[:3]]}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Ефективна модель для цього завдання
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_response_length // 3,  # Приблизна оцінка токенів
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
            logger.error(f"[VECTOR-SEARCH] Error generating contextual response: {e}")
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
            logger.error(f"[VECTOR-SEARCH] Error getting chunk statistics: {e}")
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
            logger.error(f"[VECTOR-SEARCH] Test vector search failed: {e}")
            return {
                'success': False,
                'message': f'Test failed: {str(e)}',
                'error': str(e)
            }

# Глобальний інстанс
vector_search_service = VectorSearchService()
