#!/usr/bin/env python3
"""
🔧 Fix duplicate methods and broken references
"""

import re

def fix_duplicates():
    """Виправляє дублікати методів та broken references"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Спрощуємо broken _create_sample_replies_chunks метод  
    # Замінюємо весь блок на простий working метод
    old_broken_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🎯 Simple AI Extractor-based Sample Replies parsing with Pydantic contracts"""
        
        if not SIMPLE_AI_EXTRACTOR_AVAILABLE:'''
    
    new_simple_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Simplified: Uses standard chunking with enhanced classification"""
        
        logger.info("[VECTOR-PDF] 🔄 Using simplified Sample Replies processing")
        return self._create_standard_chunks(text, max_tokens)
    
    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:'''
    
    # Знаходимо початок broken методу
    broken_start = content.find(old_broken_method)
    if broken_start != -1:
        # Знаходимо кінець broken методу (до наступного def _create_standard_chunks)
        next_method = content.find('def _create_standard_chunks(self, text: str, max_tokens: int)', broken_start + 100)
        
        if next_method != -1:
            # Вирізаємо broken код
            before_broken = content[:broken_start]
            after_broken = content[next_method:]
            
            # Вставляємо чистий метод
            content = before_broken + new_simple_method + after_broken
    
    # 2. Видаляємо другий дублікат _identify_chunk_type (простий метод)
    simple_identify_pattern = r'    def _identify_chunk_type\(self, text: str\) -> str:\s*"""Визначає тип контенту секції""".*?return \'general\''
    content = re.sub(simple_identify_pattern, '', content, flags=re.DOTALL)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed all duplicates and broken references!")
    
    # Перевірка
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        check_content = f.read()
    
    identify_count = check_content.count('def _identify_chunk_type')
    create_standard_count = check_content.count('def _create_standard_chunks')
    
    print(f"📊 Methods count after cleanup:")
    print(f"  _identify_chunk_type: {identify_count} (should be 1)")
    print(f"  _create_standard_chunks: {create_standard_count} (should be 1)")

if __name__ == '__main__':
    fix_duplicates()
