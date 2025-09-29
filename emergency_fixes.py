#!/usr/bin/env python3
"""
🚨 Emergency fixes for VectorPDFService crashes
"""

import re

def emergency_fixes():
    """Виправляє критичні помилки в VectorPDFService"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Виправляємо TypeError в _detect_sample_replies_document
    old_indicators = '''        # Ключові індикатори Sample Replies
        indicators = [
            'inquiry information:' in text_lower,
            'response:' in text_lower,
            'example #' in text_lower or 'example#' in text_lower,
            re.search(r'name:\\s*[a-z]+ [a-z]\\.?', text_lower),  # Name: John D.
            'talk soon' in text_lower
        ]
        
        detected_count = sum(indicators)'''
    
    new_indicators = '''        # Ключові індикатори Sample Replies
        indicators = [
            'inquiry information:' in text_lower,
            'response:' in text_lower,
            'example #' in text_lower or 'example#' in text_lower,
            bool(re.search(r'name:\\s*[a-z]+ [a-z]\\.?', text_lower)),  # Name: John D. - перетворюємо в boolean
            'talk soon' in text_lower
        ]
        
        detected_count = sum(indicators)'''
    
    content = content.replace(old_indicators, new_indicators)
    
    # 2. Виправляємо broken _create_sample_replies_chunks method
    old_broken_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """Створює chunks використовуючи спеціалізований Sample Replies chunker"""
        
        try:
            # Використовуємо спеціалізований chunker
            # sample_replies_chunker removed - using standard method
            
            if not sections:
                logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker failed, falling back to standard")
                return self._create_standard_chunks(text, max_tokens)'''
    
    new_working_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Fallback: використовує стандартний chunking для Sample Replies"""
        
        logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker not available - using enhanced standard method")
        return self._create_standard_chunks(text, max_tokens)'''
    
    content = content.replace(old_broken_method, new_working_method)
    
    # 3. Видаляємо весь broken код після коментаря
    # Знайдемо початок broken блоку і видалимо все до кінця методу
    broken_start = content.find('            # Конвертуємо в DocumentChunk об\'єкти')
    if broken_start != -1:
        # Знайдемо кінець методу _create_sample_replies_chunks
        method_end = content.find('    def _create_standard_chunks(', broken_start)
        if method_end != -1:
            # Вирізаємо broken код
            before = content[:broken_start]
            after = content[method_end:]
            content = before + after
    
    # 4. Видаляємо дублований _identify_chunk_type (старий простий метод)
    old_simple_identify = '''    def _identify_chunk_type(self, text: str) -> str:
        """Визначає тип контенту секції"""
        text_lower = text.lower()
        
        if 'inquiry information:' in text_lower:
            return 'inquiry'
        elif 'response:' in text_lower:
            return 'response'  
        elif ('inquiry information:' in text_lower and 'response:' in text_lower):
            return 'example'
        else:
            return 'general' '''
    
    # Просто видаляємо цей простий метод - у нас вже є розширений
    content = content.replace(old_simple_identify, '')
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Emergency fixes applied!")

if __name__ == '__main__':
    emergency_fixes()
