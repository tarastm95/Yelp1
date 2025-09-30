#!/usr/bin/env python3
"""
🔧 Fix Vector Search SQL Parameter Handling
"""

import re

def fix_vector_sql():
    """Виправляє SQL запит для правильної роботи з pgvector параметрами"""
    
    with open('backend/webhooks/vector_search_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо і замінюємо проблемний SQL блок
    old_sql_block = '''            # Побудова SQL запиту з векторною схожістю
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
                    (1 - (vc.embedding <=> %s::vector)) as similarity_score
                FROM webhooks_vectorchunk vc
                JOIN webhooks_vectordocument vd ON vc.document_id = vd.id
                WHERE vd.business_id = %s
                  AND vd.processing_status = 'completed'
            """
            
            params = [query_embedding_str, business_id]'''
    
    new_sql_block = '''            # Побудова SQL запиту з векторною схожістю (FIXED)
            # Використовуємо pgvector cosine similarity operator (<=>)
            
            logger.info(f"[VECTOR-SEARCH] 🔧 Building SQL query with embedding string length: {len(query_embedding_str)}")
            
            # ВИПРАВЛЕННЯ: Вставляємо embedding напряму в query для pgvector
            base_query = f"""
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
                    (1 - (vc.embedding <=> '{query_embedding_str}'::vector)) as similarity_score
                FROM webhooks_vectorchunk vc
                JOIN webhooks_vectordocument vd ON vc.document_id = vd.id
                WHERE vd.business_id = %s
                  AND vd.processing_status = 'completed'
            """
            
            params = [business_id]  # Тільки business_id як параметр'''
    
    content = content.replace(old_sql_block, new_sql_block)
    
    # Також виправляємо similarity threshold частину
    old_threshold_block = '''            # Додаємо similarity threshold та ordering
            base_query += """
                AND (1 - (vc.embedding <=> %s::vector)) >= %s
                ORDER BY vc.embedding <=> %s::vector
                LIMIT %s
            """
            
            params.extend([query_embedding_str, similarity_threshold, query_embedding_str, limit])'''
    
    new_threshold_block = '''            # Додаємо similarity threshold та ordering (FIXED)
            base_query += f"""
                AND (1 - (vc.embedding <=> '{query_embedding_str}'::vector)) >= %s
                ORDER BY vc.embedding <=> '{query_embedding_str}'::vector
                LIMIT %s
            """
            
            params.extend([similarity_threshold, limit])  # Тільки threshold та limit як параметри'''
    
    content = content.replace(old_threshold_block, new_threshold_block)
    
    with open('backend/webhooks/vector_search_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed Vector Search SQL parameter handling!")
    print("  🔧 Embedding now inserted directly into SQL string")
    print("  🔧 Only business_id, similarity_threshold, limit as parameters")
    print("  🔧 Should resolve pgvector parameter issues")

if __name__ == '__main__':
    fix_vector_sql()
