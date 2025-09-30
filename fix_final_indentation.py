#!/usr/bin/env python3
"""
🔧 Final indentation fix for _create_standard_chunks method
"""

def fix_final_indentation():
    """Виправляє індентацію методу _create_standard_chunks"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Виправляємо індентацію методу - з 8 пробілів на 4
    content = content.replace(
        "        def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:",
        "    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:"
    )
    
    # Виправляємо індентацію всього тіла методу
    lines = content.split('\\n')
    fixed_lines = []
    fix_indentation = False
    
    for line in lines:
        if 'def _create_standard_chunks(self, text: str, max_tokens: int)' in line:
            fix_indentation = True
            fixed_lines.append(line)
        elif fix_indentation and line.startswith('    def ') and '_create_standard_chunks' not in line:
            # Наступний метод почався - припиняємо виправлення
            fix_indentation = False
            fixed_lines.append(line)
        elif fix_indentation and line.startswith('        '):
            # Виправляємо відступ: 8 пробілів → 4 пробіли
            fixed_lines.append(line[4:])
        else:
            fixed_lines.append(line)
    
    content = '\\n'.join(fixed_lines)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed _create_standard_chunks method indentation!")
    
    # Перевіряємо результат
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        check_content = f.read()
    
    if '        def _create_standard_chunks' in check_content:
        print("❌ Still has wrong indentation!")
    elif '    def _create_standard_chunks' in check_content:
        print("✅ Indentation corrected successfully!")
    else:
        print("⚠️ Method not found - check manually")

if __name__ == '__main__':
    fix_final_indentation()
