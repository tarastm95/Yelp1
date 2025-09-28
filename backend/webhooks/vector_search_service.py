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
    
    def search_similar_chunks(
        self,
        query_text: str,
        business_id: str,
        location_id: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
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
            
            # Побудова SQL запиту з векторною схожістю
            # Використовуємо pgvector cosine similarity operator (<=>)
            base_query = """
                SELECT 
                    vc.id,
                    vc.content,
                    vc.page_number,
                    vc.chunk_index,
                    vc.token_count,
                    vc.chunk_type,
                    vc.metadata,
                    vd.filename,
                    vd.business_id,
                    vd.location_id,
                    (1 - (vc.embedding <=> %s)) as similarity_score
                FROM webhooks_vectorchunk vc
                JOIN webhooks_vectordocument vd ON vc.document_id = vd.id
                WHERE vd.business_id = %s
                  AND vd.processing_status = 'completed'
            """
            
            params = [query_embedding, business_id]
            
            # Додаємо фільтр локації якщо вказано
            if location_id:
                base_query += " AND vd.location_id = %s"
                params.append(location_id)
            
            # Додаємо фільтр типів чанків якщо вказано
            if chunk_types:
                placeholders = ','.join(['%s'] * len(chunk_types))
                base_query += f" AND vc.chunk_type IN ({placeholders})"
                params.extend(chunk_types)
            
            # Додаємо similarity threshold та ordering
            base_query += """
                AND (1 - (vc.embedding <=> %s)) >= %s
                ORDER BY vc.embedding <=> %s
                LIMIT %s
            """
            
            params.extend([query_embedding, similarity_threshold, query_embedding, limit])
            
            logger.info(f"[VECTOR-SEARCH] Executing vector similarity search...")
            
            with connection.cursor() as cursor:
                cursor.execute(base_query, params)
                rows = cursor.fetchall()
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    results.append({
                        'chunk_id': row_dict['id'],
                        'content': row_dict['content'],
                        'page_number': row_dict['page_number'],
                        'chunk_index': row_dict['chunk_index'],
                        'token_count': row_dict['token_count'],
                        'chunk_type': row_dict['chunk_type'],
                        'metadata': row_dict['metadata'],
                        'filename': row_dict['filename'],
                        'business_id': row_dict['business_id'],
                        'location_id': row_dict['location_id'],
                        'similarity_score': float(row_dict['similarity_score'])
                    })
                
                logger.info(f"[VECTOR-SEARCH] Found {len(results)} similar chunks")
                
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
            # Отримання статистики
            stats = self.get_chunk_statistics(business_id, location_id)
            
            if stats['total_chunks'] == 0:
                return {
                    'success': False,
                    'message': 'No vector chunks available for this business',
                    'stats': stats
                }
            
            # Тестовий пошук
            results = self.search_similar_chunks(
                query_text=test_query,
                business_id=business_id,
                location_id=location_id,
                limit=3,
                similarity_threshold=0.5  # Нижчий поріг для тестування
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
