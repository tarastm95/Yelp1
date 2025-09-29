#!/usr/bin/env python3
"""
🔧 Fix method nesting issue - _create_standard_chunks inside other method
"""

def fix_method_nesting():
    """Виправляє вкладеність методів - переносить _create_standard_chunks на правильний рівень"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо проблемне місце
    broken_line = "        def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:"
    fixed_line = "    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:"
    
    # Виправляємо індентацію для _create_standard_chunks
    content = content.replace(broken_line, fixed_line)
    
    # Також виправляємо всі рядки всередині цього методу (зсуваємо ліворуч на 4 пробіли)
    lines = content.split('\\n')
    fixed_lines = []
    in_method = False
    
    for line in lines:
        if line.strip() == 'def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:':
            in_method = True
            fixed_lines.append(line)
        elif in_method and line.startswith('    def ') and not line.startswith('        '):
            # Наступний метод почався - закінчуємо виправлення
            in_method = False
            fixed_lines.append(line)
        elif in_method and line.startswith('        '):
            # Видаляємо 4 пробіли з початку (зсуваємо ліворуч)
            fixed_lines.append(line[4:])
        else:
            fixed_lines.append(line)
    
    content = '\\n'.join(fixed_lines)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed method nesting - moved _create_standard_chunks to correct level!")

if __name__ == '__main__':
    fix_method_nesting()
