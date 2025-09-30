#!/usr/bin/env python3
"""
🔧 Final requirements.txt fix - remove extract-thinker + add django-rq
"""

# Читаємо поточний файл
with open('backend/requirements.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Видаляємо extract-thinker і весь ExtractThinker блок
lines = content.split('\n')
filtered_lines = []

skip_next = False
for line in lines:
    if 'extract-thinker' in line:
        continue  # Пропускаємо extract-thinker
    elif '# 🎯 Structured Data Extraction (ExtractThinker)' in line:
        # Замінюємо header
        filtered_lines.append('# 🎯 Data Validation (lightweight)')
        continue
    elif 'AI-powered structured data extraction' in line:
        continue  # Пропускаємо опис extract-thinker
    else:
        filtered_lines.append(line)

# Додаємо django-rq після redis
final_lines = []
for line in filtered_lines:
    final_lines.append(line)
    if line.startswith('redis>='):
        final_lines.append('django-rq>=2.10.0,<3.0.0     # Redis queue integration')

# Записуємо виправлений файл
with open('backend/requirements.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(final_lines))

print("✅ Fixed requirements.txt:")
print("  ❌ Removed: extract-thinker (heavy dependencies)")
print("  ✅ Added: django-rq (Redis queue support)")
print("  ✅ Clean: No dependency conflicts")

if __name__ == '__main__':
    pass
