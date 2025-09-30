#!/usr/bin/env python3
"""
🔧 Fix SyntaxError: unterminated string literal
"""

def fix_syntax_error():
    """Виправляє незакриту строку в patterns"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо проблемне місце та виправляємо
    content = content.replace(
        "            r'\\n\\n",
        "            r'\\n\\n\\n+',  # Множинні переноси рядків"
    )
    
    # Перевіряємо що patterns секція завершена правильно
    if "patterns = [" in content and "r'\\n\\n\\n+'" in content:
        # Переконуємося що після patterns є закриваюча дужка
        patterns_start = content.find("patterns = [")
        patterns_section = content[patterns_start:patterns_start+200]
        
        if "]" not in patterns_section:
            # Додаємо закриваючу дужку якщо відсутня
            content = content.replace(
                "            r'\\n\\n\\n+',  # Множинні переноси рядків",
                "            r'\\n\\n\\n+',  # Множинні переноси рядків\\n        ]"
            )
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed unterminated string literal!")
    
    # Перевіряємо результат
    try:
        compile(content, 'vector_pdf_service.py', 'exec')
        print("✅ Python syntax is now valid!")
    except SyntaxError as e:
        print(f"❌ Still has syntax error: {e}")
        print(f"Line {e.lineno}: {e.text}")

if __name__ == '__main__':
    fix_syntax_error()
