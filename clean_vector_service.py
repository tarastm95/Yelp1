#!/usr/bin/env python3
"""
🧹 Clean VectorPDFService from all broken code
"""

import re

def clean_vector_service():
    """Повністю очищає VectorPDFService від broken коду"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Замінюємо broken _create_sample_replies_chunks на простий working метод
    broken_method_start = content.find('def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:')
    if broken_method_start == -1:
        print("❌ Method not found")
        return
    
    # Знаходимо початок методу (з правильними відступами)
    method_start = content.rfind('    def _create_sample_replies_chunks', 0, broken_method_start + 100)
    
    # Знаходимо перший наступний метод після broken коду
    next_method = content.find('    def _create_standard_chunks', method_start + 10)  # Пропускаємо перший дублікат
    if next_method == -1:
        print("❌ Next method not found")
        return
    
    # Замінюємо весь broken блок на простий working метод
    before_method = content[:method_start]
    after_method = content[next_method:]
    
    clean_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Simplified: Uses standard chunking with enhanced classification"""
        
        logger.info("[VECTOR-PDF] 🔄 Using simplified Sample Replies processing")
        return self._create_standard_chunks(text, max_tokens)

    '''
    
    content = before_method + clean_method + after_method
    
    # 2. Видаляємо broken legacy extract_text_from_uploaded_file метод що використовує undefined pages_data
    legacy_method_pattern = r'    def extract_text_from_uploaded_file\(self, file_content: bytes, filename: str\) -> str:.*?return "PROCESSING_ERROR"'
    content = re.sub(legacy_method_pattern, '', content, flags=re.DOTALL)
    
    # 3. Замінюємо простий _identify_chunk_type на enhanced версію
    simple_identify = '''    def _identify_chunk_type(self, text: str) -> str:
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
    
    enhanced_identify = '''    def _identify_chunk_type(self, text: str) -> str:
        """🎯 Enhanced chunk classification with business response detection"""
        
        logger.info(f"[VECTOR-PDF] 🎯 CLASSIFYING CHUNK:")
        logger.info(f"[VECTOR-PDF]   Text length: {len(text)} chars")
        logger.info(f"[VECTOR-PDF]   Text preview: {text[:100]}...")
        
        text_lower = text.lower().strip()
        
        # Quick markers check
        quick_markers = {
            'inquiry_marker': 'inquiry information:' in text_lower,
            'response_marker': 'response:' in text_lower,
            'name_marker': 'name:' in text_lower,
            'good_afternoon': 'good afternoon' in text_lower,
            'good_morning': 'good morning' in text_lower,
            'thanks_reaching': 'thanks for reaching' in text_lower,
            'talk_soon': 'talk soon' in text_lower,
            'norma': 'norma' in text_lower
        }
        logger.info(f"[VECTOR-PDF]   Quick markers: {quick_markers}")
        
        # Enhanced classification logic
        if 'inquiry information:' in text_lower:
            logger.info(f"[VECTOR-PDF] ✅ EXPLICIT INQUIRY MARKER")
            return 'inquiry'
        elif 'response:' in text_lower:
            logger.info(f"[VECTOR-PDF] ✅ EXPLICIT RESPONSE MARKER")
            return 'response'
        elif ('inquiry information:' in text_lower and 'response:' in text_lower):
            logger.info(f"[VECTOR-PDF] ✅ MIXED EXAMPLE MARKER")
            return 'example'
        
        # Business response patterns (Norma's style)
        business_phrases = ['good afternoon', 'good morning', 'thanks for reaching', 'thanks so much', 
                           "we'd be glad", 'talk soon', 'our team', 'please let', 'norma']
        business_matches = sum(1 for phrase in business_phrases if phrase in text_lower)
        
        # Customer inquiry patterns
        inquiry_phrases = ['name:', 'lead created:', 'what kind of', 'how many stories', 
                          'when do you require', 'in what location', 'ca \\\\d{5}']
        inquiry_matches = sum(1 for phrase in inquiry_phrases if phrase in text_lower)
        
        if business_matches >= 2:
            logger.info(f"[VECTOR-PDF] ✅ BUSINESS RESPONSE DETECTED ({business_matches} matches)")
            return 'response'
        elif inquiry_matches >= 2:
            logger.info(f"[VECTOR-PDF] ✅ CUSTOMER INQUIRY DETECTED ({inquiry_matches} matches)")
            return 'inquiry'
        elif business_matches > 0:
            logger.info(f"[VECTOR-PDF] ⚡ LIKELY BUSINESS RESPONSE ({business_matches} matches)")
            return 'response'
        elif inquiry_matches > 0:
            logger.info(f"[VECTOR-PDF] ⚡ LIKELY CUSTOMER INQUIRY ({inquiry_matches} matches)")
            return 'inquiry'
        else:
            logger.warning(f"[VECTOR-PDF] ⚠️ NO CLEAR PATTERNS - defaulting to general")
            return 'general' '''
    
    content = content.replace(simple_identify, enhanced_identify)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Cleaned VectorPDFService:")
    print("  ❌ Removed: Broken AI extractor code")
    print("  ❌ Removed: Duplicate methods")
    print("  ❌ Removed: Undefined variables")
    print("  ✅ Enhanced: _identify_chunk_type with business patterns")
    print("  ✅ Clean: Simple working methods only")

if __name__ == '__main__':
    clean_vector_service()
