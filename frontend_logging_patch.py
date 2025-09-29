#!/usr/bin/env python3
"""
🔍 Frontend Logging Patch для діагностики AI Preview проблем
"""

import re

def add_frontend_logging():
    """Додає детальне console.log логування в AutoResponseSettings.tsx"""
    
    print("🔧 Patching frontend AutoResponseSettings.tsx...")
    
    with open('frontend/src/AutoResponseSettings.tsx', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знайти handleGeneratePreview функцію та додати логування
    # Шукаємо місце де викликається AI Preview API
    
    # 1. Додати логування на початок handleGeneratePreview
    pattern_preview_start = r'(const handleGeneratePreview = async \(\) => {)'
    
    replacement = r'''\1
    console.log('🚀 [FRONTEND] AI PREVIEW GENERATION STARTED');
    console.log('📊 [FRONTEND] Settings:', {
      business: selectedBusiness,
      phoneAvailable,
      useAiGreeting,
      useSampleReplies,
      vectorSimilarityThreshold,
      vectorSearchLimit,
      vectorChunkTypes,
      customPreviewText: aiCustomPreviewText?.substring(0, 100) + '...'
    });'''
    
    content = re.sub(pattern_preview_start, replacement, content, flags=re.MULTILINE)
    
    # 2. Додати логування перед API викликом
    # Шукаємо axios.post для preview
    preview_api_pattern = r'(.*axios\.post.*ai-preview.*)'
    
    # Складно знайти точне місце, тому додамо загальне логування перед setAiPreviewLoading(true)
    loading_pattern = r'(setAiPreviewLoading\(true\);)'
    
    loading_replacement = r'''console.log('📡 [FRONTEND] Sending AI Preview request...', {
      apiEndpoint: '/ai-preview/',
      requestData: {
        business_id: selectedBusiness,
        phone_available: phoneAvailable,
        custom_preview_text: aiCustomPreviewText,
        vector_settings: {
          similarity_threshold: vectorSimilarityThreshold,
          search_limit: vectorSearchLimit,
          chunk_types: vectorChunkTypes
        }
      }
    });
    
    \1'''
    
    content = re.sub(loading_pattern, loading_replacement, content, flags=re.MULTILINE)
    
    # 3. Додати логування після отримання відповіді
    # Шукаємо .then(res => {
    then_pattern = r'(\.then\(res => {)'
    
    then_replacement = r'''\1
        console.log('✅ [FRONTEND] AI Preview response received:', res.data);
        console.log('📊 [FRONTEND] Response details:', {
          preview: res.data.preview?.substring(0, 100) + '...',
          vectorSearchEnabled: res.data.vector_search_enabled,
          vectorResultsCount: res.data.vector_results_count,
          status: res.status
        });'''
    
    content = re.sub(then_pattern, then_replacement, content, flags=re.MULTILINE)
    
    # 4. Додати логування помилок
    catch_pattern = r'(\.catch\(error => {)'
    
    catch_replacement = r'''\1
        console.error('❌ [FRONTEND] AI Preview error:', error);
        console.error('🔍 [FRONTEND] Error details:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          settings: {
            vectorSimilarityThreshold,
            vectorSearchLimit,
            useSampleReplies
          }
        });'''
    
    content = re.sub(catch_pattern, catch_replacement, content, flags=re.MULTILINE)
    
    with open('frontend/src/AutoResponseSettings.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Frontend logging patches applied!")

if __name__ == '__main__':
    add_frontend_logging()
