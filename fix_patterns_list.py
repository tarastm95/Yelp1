#!/usr/bin/env python3
"""
🔧 Fix patterns list - add proper closing bracket
"""

def fix_patterns_list():
    """Виправляє patterns list з правильною закриваючою дужкою"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Виправляємо patterns блок
    old_patterns = """        # Паттерни для розділення Sample Replies
        patterns = [
            r'Example\\s*#\\d+',
            r'Inquiry information:',
            r'Response:',
            r'\\n\\n\\n+',  # Множинні переноси рядків\\n        ]"""
    
    new_patterns = """        # Паттерни для розділення Sample Replies
        patterns = [
            r'Example\\s*#\\d+',
            r'Inquiry information:',
            r'Response:',
            r'\\n\\n\\n+',  # Множинні переноси рядків
        ]"""
    
    content = content.replace(old_patterns, new_patterns)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed patterns list with proper closing bracket!")
    
    # Перевіряємо Python syntax
    try:
        compile(content, 'vector_pdf_service.py', 'exec')
        print("✅ Python syntax is now valid!")
    except SyntaxError as e:
        print(f"❌ Still has syntax error: {e}")
        print(f"Line {e.lineno}: {e.text}")

if __name__ == '__main__':
    fix_patterns_list()
