#!/usr/bin/env python3
"""
🔧 Fix IndentationError by removing unreachable code
"""

import re

def fix_indentation():
    """Видаляє unreachable код після return в _create_sample_replies_chunks"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо метод _create_sample_replies_chunks і видаляємо все після return
    method_start = content.find('def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:')
    if method_start == -1:
        print("❌ Method _create_sample_replies_chunks not found")
        return
    
    # Знаходимо return statement в цьому методі
    method_part = content[method_start:]
    return_pos = method_part.find('return self._create_standard_chunks(text, max_tokens)')
    
    if return_pos == -1:
        print("❌ Return statement not found")
        return
    
    return_end = method_start + return_pos + len('return self._create_standard_chunks(text, max_tokens)')
    
    # Знаходимо наступний метод щоб знати де закінчити видалення
    next_method_pos = content.find('def _create_standard_chunks(', return_end)
    
    if next_method_pos == -1:
        print("❌ Next method not found")
        return
    
    # Видаляємо unreachable код між return та наступним методом
    before_return = content[:return_end]
    after_unreachable = content[next_method_pos:]
    
    # Додаємо правильний відступ та перенос рядка
    fixed_content = before_return + "\\n\\n    " + after_unreachable
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("✅ Removed unreachable code and fixed indentation!")

if __name__ == '__main__':
    fix_indentation()
