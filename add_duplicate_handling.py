#!/usr/bin/env python3
"""
🔧 Add duplicate handling to process_pdf_file method
"""

import re

def add_duplicate_handling():
    """Додає обробку дублікатів file_hash в process_pdf_file"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо створення документа в process_pdf_file
    old_create = '''                document = VectorDocument.objects.create(
                    business_id=business_id,
                    location_id=location_id,
                    filename=filename,
                    file_hash=file_hash,
                    file_size=len(file_content),
                    page_count=page_count,
                    chunk_count=len(chunks),
                    total_tokens=sum(chunk.token_count for chunk in chunks),
                    processing_status='completed',
                    embedding_model='text-embedding-3-small',
                    embedding_dimensions=1536,
                    metadata={
                        'chunks_by_type': {
                            chunk_type: len([c for c in chunks if c.chunk_type == chunk_type])
                            for chunk_type in set(chunk.chunk_type for chunk in chunks)
                        }
                    }
                )'''
    
    new_create = '''                # Перевіряємо чи документ вже існує
                try:
                    existing_doc = VectorDocument.objects.get(file_hash=file_hash)
                    logger.warning(f"[VECTOR-PDF] ⚠️ Document with same hash exists, deleting old version")
                    existing_doc.delete()
                except VectorDocument.DoesNotExist:
                    pass  # Все ок, документа не існує
                
                document = VectorDocument.objects.create(
                    business_id=business_id,
                    location_id=location_id,
                    filename=filename,
                    file_hash=file_hash,
                    file_size=len(file_content),
                    page_count=page_count,
                    chunk_count=len(chunks),
                    total_tokens=sum(chunk.token_count for chunk in chunks),
                    processing_status='completed',
                    embedding_model='text-embedding-3-small',
                    embedding_dimensions=1536,
                    metadata={
                        'chunks_by_type': {
                            chunk_type: len([c for c in chunks if c.chunk_type == chunk_type])
                            for chunk_type in set(chunk.chunk_type for chunk in chunks)
                        }
                    }
                )'''
    
    content = content.replace(old_create, new_create)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Added duplicate handling for file_hash conflicts!")

if __name__ == '__main__':
    add_duplicate_handling()
