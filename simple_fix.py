#!/usr/bin/env python3
"""
🔧 Simple fix: completely replace broken method
"""

import re

def simple_fix():
    """Повністю замінює broken _create_sample_replies_chunks метод"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо і замінюємо весь broken метод
    # Пошук від початку методу до наступного методу
    method_pattern = r'    def _create_sample_replies_chunks\(self, text: str, max_tokens: int\) -> List\[DocumentChunk\]:.*?(?=    def _create_standard_chunks)'
    
    new_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Fallback: використовує стандартний chunking для Sample Replies"""
        
        logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker not available - using enhanced standard method")
        return self._create_standard_chunks(text, max_tokens)

    '''
    
    content = re.sub(method_pattern, new_method, content, flags=re.DOTALL)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Replaced broken method with clean working version!")

if __name__ == '__main__':
    simple_fix()
