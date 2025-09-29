#!/usr/bin/env python3
"""
Виправляє import в debug_views.py та додає URL patterns
"""

# 1. Виправляємо import в debug_views.py
with open('backend/webhooks/debug_views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Додаємо відсутній import
content = content.replace(
    'import logging',
    '''import logging
from django.utils import timezone'''
)

with open('backend/webhooks/debug_views.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Додаємо URLs до urls.py
with open('backend/webhooks/urls.py', 'r', encoding='utf-8') as f:
    urls_content = f.read()

# Додаємо import debug views
if 'debug_views' not in urls_content:
    # Знайти місце після останнього from .xxx_views import
    import_pattern = r'(from \.ml_classifier_views import[^)]+\))'
    
    urls_content = urls_content.replace(
        'from .ml_classifier_views import',
        '''from .debug_views import VectorDebugView, ChunkAnalysisView
from .ml_classifier_views import'''
    )

# Додаємо URL patterns перед закриттям urlpatterns
if 'vector-debug' not in urls_content:
    urls_content = urls_content.replace(
        '    path(\'chunks/reclassify/\', ReclassifyChunksView.as_view(), name=\'reclassify_chunks\'),\n]',
        '''    path('chunks/reclassify/', ReclassifyChunksView.as_view(), name='reclassify_chunks'),
    
    # 🔍 Debug Endpoints
    path('debug/vector/', VectorDebugView.as_view(), name='vector_debug'),
    path('debug/chunk-analysis/', ChunkAnalysisView.as_view(), name='chunk_analysis'),
]'''
    )

with open('backend/webhooks/urls.py', 'w', encoding='utf-8') as f:
    f.write(urls_content)

print("✅ Debug views fixed and URLs added!")
