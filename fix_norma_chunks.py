#!/usr/bin/env python3
"""
🚀 Швидке виправлення chunks Норми
"""

import os
import sys
import django

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yelp_project.settings')
django.setup()

from webhooks.vector_models import VectorChunk

# Знайти та виправити Norma's response chunks
business_id = 'S4VbIKUr_s7FecEH72n_cA'
chunks = VectorChunk.objects.filter(document__business_id=business_id)

print(f"📊 До виправлення:")
for t in ['inquiry', 'response', 'general']:
    print(f"  {t}: {chunks.filter(chunk_type=t).count()}")

fixed = 0
for chunk in chunks:
    content = chunk.content.lower()
    old_type = chunk.chunk_type
    
    # Norma's response patterns
    if any(pattern in content for pattern in [
        'good afternoon beau', 'good morning', 'thanks for reaching out',
        'talk soon, norma', 'thanks so much for sharing'
    ]):
        chunk.chunk_type = 'response'
        chunk.save()
        fixed += 1
        print(f"✅ Fixed chunk: {old_type} → response (Norma's response)")
    
    # Client inquiry patterns  
    elif 'name: beau s' in content or 'name: jenny z' in content:
        chunk.chunk_type = 'inquiry'
        chunk.save()
        fixed += 1
        print(f"✅ Fixed chunk: {old_type} → inquiry (Client data)")

print(f"\n🎯 Виправлено chunks: {fixed}")
print(f"📊 Після виправлення:")
for t in ['inquiry', 'response', 'general']:
    print(f"  {t}: {chunks.filter(chunk_type=t).count()}")

print(f"\n✅ Тепер AI зможе знайти приклади стилю Норми!")
