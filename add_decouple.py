#!/usr/bin/env python3
"""
🔧 Add missing python-decouple dependency
"""

# Читаємо requirements.txt
with open('backend/requirements.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Додаємо python-decouple після python-dotenv
content = content.replace(
    'python-dotenv>=0.19.0',
    'python-dotenv>=0.19.0\npython-decouple>=3.8     # Configuration management'
)

# Записуємо назад
with open('backend/requirements.txt', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added python-decouple dependency")

# Показуємо що додано
print("\nUpdated requirements.txt:")
lines = content.split('\n')
for i, line in enumerate(lines[1:8], 1):
    print(f"  {i}. {line}")

if __name__ == '__main__':
    pass
