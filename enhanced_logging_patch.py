#!/usr/bin/env python3
"""
🔍 Enhanced Logging Patch для діагностики Vector Search проблем
"""

import re

def add_enhanced_logging():
    """Додає детальне логування в кілька файлів"""
    
    # 1. Vector PDF Service - додати детальне логування розділення
    print("🔧 Patching vector_pdf_service.py...")
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Додати логування в _split_by_sections
    old_split_method = '''    def _split_by_sections(self, text: str) -> List[str]:
        """Розділяє текст на логічні секції"""
        
        # Паттерни для розділення Sample Replies
        patterns = [
            r'Example\\s*#\\d+',
            r'Inquiry information:',
            r'Response:',
            r'\\n\\n\\n+',  # Множинні переноси рядків
        ]
        
        sections = [text]
        
        for pattern in patterns:
            new_sections = []
            for section in sections:
                parts = re.split(f'({pattern})', section, flags=re.IGNORECASE)
                for part in parts:
                    if part.strip():
                        new_sections.append(part.strip())
            sections = new_sections
        
        return [s for s in sections if len(s.strip()) > 20]  # Фільтруємо дуже короткі секції'''
    
    new_split_method = '''    def _split_by_sections(self, text: str) -> List[str]:
        """Розділяє текст на логічні секції"""
        
        logger.info(f"[VECTOR-PDF] 📄 SPLITTING TEXT INTO SECTIONS:")
        logger.info(f"[VECTOR-PDF] Original text length: {len(text)} chars")
        logger.info(f"[VECTOR-PDF] Text preview (first 300 chars): {text[:300]}...")
        
        # Паттерни для розділення Sample Replies
        patterns = [
            r'Example\\s*#\\d+',
            r'Inquiry information:',
            r'Response:',
            r'\\n\\n\\n+',  # Множинні переноси рядків
        ]
        
        sections = [text]
        
        for i, pattern in enumerate(patterns):
            logger.info(f"[VECTOR-PDF] 🔄 Applying pattern {i+1}: {pattern}")
            new_sections = []
            for section in sections:
                parts = re.split(f'({pattern})', section, flags=re.IGNORECASE)
                logger.info(f"[VECTOR-PDF]   Split into {len(parts)} parts")
                for j, part in enumerate(parts):
                    if part.strip():
                        logger.info(f"[VECTOR-PDF]     Part {j+1}: {len(part)} chars - '{part[:50]}...'")
                        new_sections.append(part.strip())
            sections = new_sections
            logger.info(f"[VECTOR-PDF] After pattern {i+1}: {len(sections)} sections")
        
        filtered_sections = [s for s in sections if len(s.strip()) > 20]
        logger.info(f"[VECTOR-PDF] 📋 FINAL SECTIONS: {len(filtered_sections)} (after filtering < 20 chars)")
        
        for i, section in enumerate(filtered_sections):
            logger.info(f"[VECTOR-PDF] Section {i+1}: {len(section)} chars")
            logger.info(f"[VECTOR-PDF]   Content: {section[:100]}...")
        
        return filtered_sections'''
    
    content = content.replace(old_split_method, new_split_method)
    
    # Додати логування в _identify_chunk_type перед класифікацією
    old_identify = '''    def _identify_chunk_type(self, text: str) -> str:
        """🚀 Enterprise Hybrid Classification: Rules → Scoring → Zero-shot → ML"""
        try:
            # 🎯 HYBRID APPROACH: Professional multi-stage classification
            from .hybrid_chunk_classifier import hybrid_classifier
            
            classification_result = hybrid_classifier.classify_chunk_hybrid(text)'''
    
    new_identify = '''    def _identify_chunk_type(self, text: str) -> str:
        """🚀 Enterprise Hybrid Classification: Rules → Scoring → Zero-shot → ML"""
        logger.info(f"[VECTOR-PDF] 🎯 CLASSIFYING CHUNK:")
        logger.info(f"[VECTOR-PDF] Text length: {len(text)} chars")
        logger.info(f"[VECTOR-PDF] Text preview: {text[:150]}...")
        
        # Швидка перевірка основних маркерів перед класифікацією
        text_lower = text.lower()
        quick_markers = {
            'inquiry_marker': 'inquiry information:' in text_lower,
            'response_marker': 'response:' in text_lower,
            'name_marker': 'name:' in text_lower,
            'good_afternoon': 'good afternoon' in text_lower,
            'good_morning': 'good morning' in text_lower,
            'thanks_reaching': 'thanks for reaching' in text_lower,
            'talk_soon': 'talk soon' in text_lower
        }
        logger.info(f"[VECTOR-PDF] Quick markers: {quick_markers}")
        
        try:
            # 🎯 HYBRID APPROACH: Professional multi-stage classification
            from .hybrid_chunk_classifier import hybrid_classifier
            
            classification_result = hybrid_classifier.classify_chunk_hybrid(text)'''
    
    content = content.replace(old_identify, new_identify)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 2. AI Service - додати детальне логування vector search
    print("🔧 Patching ai_service.py...")
    
    with open('backend/webhooks/ai_service.py', 'r', encoding='utf-8') as f:
        ai_content = f.read()
    
    # Знайти місце де викликається vector search в generate_preview_message
    old_vector_call = '''                    similar_chunks = vector_search_service.search_similar_chunks(
                        query_text=custom_preview_text,
                        business_id=business.business_id,
                        location_id=None,
                        limit=search_limit,
                        similarity_threshold=similarity_threshold,
                        chunk_types=['response', 'example'] if not chunk_types else chunk_types  # Приоритет response chunks
                    )'''
    
    new_vector_call = '''                    logger.info(f"[AI-SERVICE] 🔍 CALLING VECTOR SEARCH:")
                    logger.info(f"[AI-SERVICE] Query text: {custom_preview_text[:100]}...")
                    logger.info(f"[AI-SERVICE] Business: {business.business_id}")
                    logger.info(f"[AI-SERVICE] Similarity threshold: {similarity_threshold}")
                    logger.info(f"[AI-SERVICE] Search limit: {search_limit}")
                    logger.info(f"[AI-SERVICE] Chunk types filter: {['response', 'example'] if not chunk_types else chunk_types}")
                    
                    similar_chunks = vector_search_service.search_similar_chunks(
                        query_text=custom_preview_text,
                        business_id=business.business_id,
                        location_id=None,
                        limit=search_limit,
                        similarity_threshold=similarity_threshold,
                        chunk_types=['response', 'example'] if not chunk_types else chunk_types  # Приоритет response chunks
                    )
                    
                    logger.info(f"[AI-SERVICE] 📊 VECTOR SEARCH RESULTS:")
                    logger.info(f"[AI-SERVICE] Found chunks: {len(similar_chunks) if similar_chunks else 0}")'''
    
    ai_content = ai_content.replace(old_vector_call, new_vector_call)
    
    with open('backend/webhooks/ai_service.py', 'w', encoding='utf-8') as f:
        f.write(ai_content)
    
    print("✅ Enhanced logging patches applied!")

if __name__ == '__main__':
    add_enhanced_logging()
