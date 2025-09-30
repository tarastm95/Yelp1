#!/usr/bin/env python3
"""
🔧 Add missing pythonjsonlogger dependency
"""

# Читаємо requirements.txt
with open('backend/requirements.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Додаємо pythonjsonlogger після python-decouple
content = content.replace(
    'python-decouple>=3.8     # Configuration management',
    'python-decouple>=3.8     # Configuration management\npython-json-logger>=2.0.0  # JSON logging support'
)

# Записуємо назад
with open('backend/requirements.txt', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added python-json-logger dependency")

# Перевіряємо що все додано
lines = content.split('\n')
for i, line in enumerate(lines[1:10], 1):
    if 'decouple' in line or 'json-logger' in line:
        print(f"  ✅ {line}")

if __name__ == '__main__':
    pass
