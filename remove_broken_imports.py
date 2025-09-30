#!/usr/bin/env python3
"""
🔧 Remove broken imports and simplify _create_sample_replies_chunks
"""

import re

def remove_broken_imports():
    """Видаляє broken imports та спрощує методи"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Видаляємо broken import block
    broken_import_block = '''# Simple AI Extractor integration
try:
    from .simple_ai_extractor import simple_ai_extractor
    from .extraction_contracts import CustomerInquiry, BusinessResponse, SampleReplyExample, SampleRepliesDocument
    SIMPLE_AI_EXTRACTOR_AVAILABLE = True
    logger.info("[VECTOR-PDF] ✅ Simple AI Extractor available")
except ImportError as e:
    SIMPLE_AI_EXTRACTOR_AVAILABLE = False
    logger.warning(f"[VECTOR-PDF] ⚠️ Simple AI Extractor not available: {e}")'''
    
    content = content.replace(broken_import_block, '')
    
    # 2. Замінюємо весь broken _create_sample_replies_chunks метод на простий fallback
    # Знайдемо початок і кінець методу
    method_start = content.find('def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:')
    if method_start == -1:
        print("❌ Method not found")
        return
    
    method_start = content.rfind('    def _create_sample_replies_chunks', 0, method_start + 100)
    
    # Знайдемо наступний метод
    next_method = content.find('    def _create_standard_chunks', method_start)
    if next_method == -1:
        print("❌ Next method not found")
        return
    
    # Замінюємо весь метод на простий
    before_method = content[:method_start]
    after_method = content[next_method:]
    
    simple_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Simplified: Direct fallback to standard chunking with enhanced classification"""
        
        logger.info("[VECTOR-PDF] 🔄 Using simplified Sample Replies processing")
        logger.info("[VECTOR-PDF] Will use standard chunking + enhanced classification")
        
        return self._create_standard_chunks(text, max_tokens)

    '''
    
    content = before_method + simple_method + after_method
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Removed all broken imports and simplified methods!")

if __name__ == '__main__':
    remove_broken_imports()
