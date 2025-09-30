#!/usr/bin/env python3
"""
🔧 Add uvicorn for ASGI server support
"""

# Читаємо requirements.txt
with open('backend/requirements.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Додаємо uvicorn до production server секції
content = content.replace(
    'gunicorn>=21.0.0,<22.0.0   # WSGI HTTP server',
    '''gunicorn>=21.0.0,<22.0.0   # WSGI HTTP server
uvicorn>=0.30.0,<1.0.0     # ASGI HTTP server'''
)

# Записуємо назад
with open('backend/requirements.txt', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added uvicorn for ASGI server support")

if __name__ == '__main__':
    pass
