#!/usr/bin/env python3
"""
🔧 Fix _identify_chunk_type to use hybrid classifier instead of simple rules
"""

import re

def fix_identify_method():
    """Замінює простий _identify_chunk_type на hybrid classifier"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо і замінюємо простий _identify_chunk_type метод
    old_method = '''    def _identify_chunk_type(self, text: str) -> str:
        """Визначає тип контенту секції"""
        text_lower = text.lower()
        
        if 'inquiry information:' in text_lower:
            return 'inquiry'
        elif 'response:' in text_lower:
            return 'response'  
        elif ('inquiry information:' in text_lower and 'response:' in text_lower):
            return 'example'
        else:
            return 'general' '''
    
    new_method = '''    def _identify_chunk_type(self, text: str) -> str:
        """🎯 Розумна класифікація через гібридний класифікатор + простий fallback"""
        
        logger.info(f"[VECTOR-PDF] 🎯 CLASSIFYING CHUNK:")
        logger.info(f"[VECTOR-PDF]   Text length: {len(text)} chars")
        logger.info(f"[VECTOR-PDF]   Text preview: {text[:150]}...")
        
        # Швидка перевірка основних маркерів
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
        logger.info(f"[VECTOR-PDF]   Quick markers: {quick_markers}")
        
        # Спочатку простий explicit check для коротких маркерів
        if len(text.strip()) < 30:  # Короткі маркери типу "Response:" або "Inquiry information:"
            if 'inquiry information:' in text_lower:
                logger.info(f"[VECTOR-PDF] ✅ SHORT MARKER: inquiry")
                return 'inquiry'
            elif 'response:' in text_lower:
                logger.info(f"[VECTOR-PDF] ✅ SHORT MARKER: response")
                return 'response'
            elif 'example #' in text_lower:
                logger.info(f"[VECTOR-PDF] ✅ SHORT MARKER: example")
                return 'example'
        
        # Для довгих chunks використовуємо hybrid classifier
        try:
            from .hybrid_chunk_classifier import hybrid_classifier
            
            logger.info(f"[VECTOR-PDF] 🧠 Using hybrid classifier for long chunk...")
            classification_result = hybrid_classifier.classify_chunk_hybrid(text)
            
            logger.info(f"[VECTOR-PDF] 🏆 Hybrid Classification Result:")
            logger.info(f"[VECTOR-PDF]   - Type: {classification_result.predicted_type}")
            logger.info(f"[VECTOR-PDF]   - Confidence: {classification_result.confidence_score:.2f}")
            logger.info(f"[VECTOR-PDF]   - Method: {classification_result.method_used}")
            logger.info(f"[VECTOR-PDF]   - Rule matches: {classification_result.rule_matches}")
            
            return classification_result.predicted_type
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] ❌ Hybrid classification failed: {e}")
            logger.warning(f"[VECTOR-PDF] 🔄 Using simple fallback...")
            
            # Простий fallback якщо hybrid classifier не працює
            if 'inquiry information:' in text_lower:
                return 'inquiry'
            elif 'response:' in text_lower:
                return 'response'
            elif ('inquiry information:' in text_lower and 'response:' in text_lower):
                return 'example'
            elif any(phrase in text_lower for phrase in ['good afternoon', 'good morning', 'thanks for reaching', "we'd be glad", 'talk soon']):
                return 'response'
            elif any(phrase in text_lower for phrase in ['name:', 'lead created:', 'ca 9', 'what kind of']):
                return 'inquiry'
            else:
                logger.warning(f"[VECTOR-PDF] ⚠️ NO PATTERNS MATCHED - defaulting to general")
                return 'general' '''
    
    content = content.replace(old_method, new_method)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed _identify_chunk_type to use hybrid classifier!")

if __name__ == '__main__':
    fix_identify_method()
