#!/usr/bin/env python3
"""
🔧 Simple indentation fix
"""

def simple_indent_fix():
    """Просто виправляє індентацію методу _create_standard_chunks"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Просто замінюємо неправильну індентацію
    content = content.replace(
        "        def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:",
        "    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:"
    )
    
    # Виправляємо індентацію для всього методу - замінюємо 8 пробілів на 4 там де потрібно
    lines = content.split('\\n')
    fixed_lines = []
    fix_next_lines = False
    
    for line in lines:
        if 'def _create_standard_chunks(self, text: str, max_tokens: int)' in line:
            fix_next_lines = True
            fixed_lines.append(line)
        elif fix_next_lines and line.startswith('    def ') and 'def _create_standard_chunks' not in line:
            # Наступний метод - припиняємо фіксити
            fix_next_lines = False
            fixed_lines.append(line)
        elif fix_next_lines and line.startswith('        '):
            # Це рядок всередині _create_standard_chunks - зменшуємо індентацію
            fixed_lines.append(line[4:])  # Видаляємо 4 пробіли
        else:
            fixed_lines.append(line)
    
    content = '\\n'.join(fixed_lines)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed method indentation!")

if __name__ == '__main__':
    simple_indent_fix()
