#!/usr/bin/env python3
"""
🔧 Fix Vector Search - Replace SQL with Python-based similarity calculation
"""

import re

def fix_vector_search():
    """Замінює SQL-based vector search на Python-based similarity calculation"""
    
    with open('backend/webhooks/vector_search_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо і замінюємо весь блок від try до except
    # Шукаємо початок проблемного блоку
    start_pattern = r'        try:\s*\n\s*# Генерація ембедінгу для запиту'
    end_pattern = r'        except Exception as e:\s*\n\s*logger\.error\(f"\[VECTOR-SEARCH\] Error in vector search: \{e\}"\)'
    
    # Знаходимо позиції
    start_match = re.search(start_pattern, content)
    end_match = re.search(end_pattern, content)
    
    if not start_match or not end_match:
        print("❌ Could not find start/end patterns")
        return
    
    start_pos = start_match.start()
    end_pos = end_match.start()
    
    # Новий Python-based implementation
    new_implementation = '''        try:
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
                
        '''
    
    # Замінюємо блок
    before = content[:start_pos]
    after = content[end_pos:]
    
    new_content = before + new_implementation + after
    
    with open('backend/webhooks/vector_search_service.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Replaced SQL-based search with Python-based similarity calculation!")
    print("  🧠 Uses numpy for reliable cosine similarity")
    print("  🔧 No more 98KB SQL queries")
    print("  🎯 Direct control over similarity calculation")
    print("  📊 Enhanced logging for each step")

if __name__ == '__main__':
    fix_vector_search()
