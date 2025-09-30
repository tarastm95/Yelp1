#!/usr/bin/env python3
"""
🔧 Final cleanup - remove all duplicates and fix broken lines
"""

import re

def final_cleanup():
    """Остаточне очищення файлу"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Видаляємо рядок з подвійним def
    content = content.replace(
        'def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:',
        'def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:'
    )
    
    # 2. Виправляємо неправильну індентацію def (8 пробілів → 4)
    content = content.replace(
        '        def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:',
        '    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:'
    )
    
    # 3. Видаляємо всі дублікати _create_standard_chunks методів окрім першого
    lines = content.split('\\n')
    cleaned_lines = []
    in_duplicate_method = False
    duplicate_count = 0
    
    for line in lines:
        if '    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:' in line:
            duplicate_count += 1
            if duplicate_count == 1:
                # Залишаємо перший метод
                cleaned_lines.append(line)
                in_duplicate_method = False
            else:
                # Починаємо пропускати дублікат
                in_duplicate_method = True
                continue
        elif in_duplicate_method and line.startswith('    def '):
            # Новий метод почався - припиняємо пропускати
            in_duplicate_method = False
            cleaned_lines.append(line)
        elif not in_duplicate_method:
            cleaned_lines.append(line)
    
    content = '\\n'.join(cleaned_lines)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Final cleanup completed!")
    print(f"📊 Removed {duplicate_count - 1} duplicate methods")
    
    # Финальна перевірка
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        final_content = f.read()
    
    final_count = final_content.count('def _create_standard_chunks')
    print(f"📊 Final _create_standard_chunks count: {final_count} (should be 1)")

if __name__ == '__main__':
    final_cleanup()
