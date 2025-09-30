#!/usr/bin/env python3
"""
🔧 Add detailed SQL debug logging to vector search
"""

import re

def add_sql_debug():
    """Додає детальне SQL debug логування"""
    
    with open('backend/webhooks/vector_search_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Додаємо debug логування перед SQL execution
    old_execution = '''            logger.info(f"[VECTOR-SEARCH] Executing vector similarity search...")
            
            with connection.cursor() as cursor:
                cursor.execute(base_query, params)
                rows = cursor.fetchall()'''
    
    new_execution = '''            logger.info(f"[VECTOR-SEARCH] 🔍 EXECUTING SQL DEBUG:")
            logger.info(f"[VECTOR-SEARCH] Query length: {len(base_query)} chars")
            logger.info(f"[VECTOR-SEARCH] Params count: {len(params)}")
            logger.info(f"[VECTOR-SEARCH] Params: {[type(p).__name__ for p in params]}")
            logger.info(f"[VECTOR-SEARCH] SQL preview: {base_query[:500]}...")
            
            with connection.cursor() as cursor:
                try:
                    cursor.execute(base_query, params)
                    rows = cursor.fetchall()
                    
                    logger.info(f"[VECTOR-SEARCH] ✅ SQL executed successfully, fetched {len(rows)} rows")
                    
                    # Debug: показати raw results
                    if len(rows) > 0:
                        logger.info(f"[VECTOR-SEARCH] 📊 Raw SQL results:")
                        for i, row in enumerate(rows[:2]):
                            logger.info(f"[VECTOR-SEARCH]   Row {i+1}: ID={row[0]}, Type={row[5]}, Similarity={row[10]:.4f}")
                    else:
                        logger.warning(f"[VECTOR-SEARCH] ⚠️ SQL returned 0 rows")
                        
                        # Debug query без similarity filter
                        debug_query = base_query.split('AND (1 - (vc.embedding')[0] + " LIMIT 3"
                        debug_params = params[:-2]  # Видаляємо similarity та limit
                        
                        logger.info(f"[VECTOR-SEARCH] 🔍 DEBUG: Testing query without similarity filter...")
                        cursor.execute(debug_query, debug_params)
                        debug_rows = cursor.fetchall()
                        logger.info(f"[VECTOR-SEARCH] 🔍 DEBUG: Query without similarity found {len(debug_rows)} rows")
                        
                except Exception as sql_error:
                    logger.error(f"[VECTOR-SEARCH] ❌ SQL execution error: {sql_error}")
                    raise'''
    
    content = content.replace(old_execution, new_execution)
    
    with open('backend/webhooks/vector_search_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Added detailed SQL debug logging!")

if __name__ == '__main__':
    add_sql_debug()
