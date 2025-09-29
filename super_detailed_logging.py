#!/usr/bin/env python3
"""
🔍 Super Detailed Logging Patch
Додає максимально детальне логування для діагностики
"""

import re

def add_super_detailed_logging():
    """Додає надзвичайно детальне логування"""
    
    print("🔧 Adding super detailed logging...")
    
    # 1. Патч для hybrid_chunk_classifier.py
    with open('backend/webhooks/hybrid_chunk_classifier.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Додаємо детальне логування в classify_chunk_hybrid
    old_classify = '''    def classify_chunk_hybrid(self, text: str) -> ClassificationResult:
        """🎯 Гібридна класифікація за вашим планом"""
        
        logger.info(f"[HYBRID-CLASSIFIER] 🧠 Classifying chunk: {text[:100]}...")
        
        # 🔍 ЕТАП 1: Explicit Markers (найвища впевненість)
        explicit_result = self._check_explicit_markers(text)
        if explicit_result:
            return explicit_result'''
    
    new_classify = '''    def classify_chunk_hybrid(self, text: str) -> ClassificationResult:
        """🎯 Гібридна класифікація за вашим планом"""
        
        logger.info(f"[HYBRID-CLASSIFIER] ====== CLASSIFYING NEW CHUNK ======")
        logger.info(f"[HYBRID-CLASSIFIER] 📝 Text length: {len(text)} chars")
        logger.info(f"[HYBRID-CLASSIFIER] 📝 Text preview: {text[:200]}...")
        logger.info(f"[HYBRID-CLASSIFIER] 📝 Confidence threshold: {self.confidence_threshold}")
        
        # Швидка діагностика маркерів перед етапами
        text_lower = text.lower()
        quick_check = {
            'inquiry_information': 'inquiry information:' in text_lower,
            'response_marker': 'response:' in text_lower,
            'name_colon': 'name:' in text_lower,
            'good_afternoon': 'good afternoon' in text_lower,
            'good_morning': 'good morning' in text_lower,
            'thanks_reaching': 'thanks for reaching' in text_lower,
            'talk_soon': 'talk soon' in text_lower,
            'norma': 'norma' in text_lower
        }
        logger.info(f"[HYBRID-CLASSIFIER] 🔍 QUICK MARKERS CHECK: {quick_check}")
        
        # 🔍 ЕТАП 1: Explicit Markers (найвища впевненість)
        logger.info(f"[HYBRID-CLASSIFIER] 🎯 STAGE 1: Checking explicit markers...")
        explicit_result = self._check_explicit_markers(text)
        if explicit_result:
            logger.info(f"[HYBRID-CLASSIFIER] ✅ STAGE 1 SUCCESS: {explicit_result.predicted_type} via {explicit_result.method_used}")
            return explicit_result
        else:
            logger.info(f"[HYBRID-CLASSIFIER] ⚪ STAGE 1: No explicit markers found")'''
    
    content = content.replace(old_classify, new_classify)
    
    # Додаємо логування в rule-based етап
    old_rule_stage = '''        # 🔍 ЕТАП 2: Rule-based + spaCy Patterns
        rule_result = self._rule_based_classification(text)
        if rule_result.confidence_score >= self.confidence_threshold:
            return rule_result'''
    
    new_rule_stage = '''        # 🔍 ЕТАП 2: Rule-based + spaCy Patterns
        logger.info(f"[HYBRID-CLASSIFIER] 🎯 STAGE 2: Running rule-based classification...")
        rule_result = self._rule_based_classification(text)
        logger.info(f"[HYBRID-CLASSIFIER] 📊 STAGE 2 RESULT: {rule_result.predicted_type}, confidence: {rule_result.confidence_score}, threshold: {self.confidence_threshold}")
        if rule_result.confidence_score >= self.confidence_threshold:
            logger.info(f"[HYBRID-CLASSIFIER] ✅ STAGE 2 SUCCESS: {rule_result.predicted_type} via {rule_result.method_used}")
            return rule_result
        else:
            logger.info(f"[HYBRID-CLASSIFIER] ⚪ STAGE 2: Confidence too low ({rule_result.confidence_score:.2f} < {self.confidence_threshold})")'''
    
    content = content.replace(old_rule_stage, new_rule_stage)
    
    # Додаємо логування в zero-shot етап
    old_zero_stage = '''        # 🔍 ЕТАП 3: Zero-shot Classification (для edge cases)
        zero_shot_result = self._zero_shot_classification(text)
        if zero_shot_result:
            return zero_shot_result'''
    
    new_zero_stage = '''        # 🔍 ЕТАП 3: Zero-shot Classification (для edge cases)
        logger.info(f"[HYBRID-CLASSIFIER] 🎯 STAGE 3: Trying zero-shot classification...")
        zero_shot_result = self._zero_shot_classification(text)
        if zero_shot_result:
            logger.info(f"[HYBRID-CLASSIFIER] ✅ STAGE 3 SUCCESS: {zero_shot_result.predicted_type} via {zero_shot_result.method_used}")
            return zero_shot_result
        else:
            logger.info(f"[HYBRID-CLASSIFIER] ⚪ STAGE 3: Zero-shot failed or unavailable")'''
    
    content = content.replace(old_zero_stage, new_zero_stage)
    
    # Додаємо логування в ML етап  
    old_ml_stage = '''        # 🔍 ЕТАП 4: ML Fallback
        ml_result = self._ml_fallback_classification(text)
        if ml_result:
            return ml_result'''
    
    new_ml_stage = '''        # 🔍 ЕТАП 4: ML Fallback
        logger.info(f"[HYBRID-CLASSIFIER] 🎯 STAGE 4: Trying heuristic fallback...")
        ml_result = self._ml_fallback_classification(text)
        if ml_result:
            logger.info(f"[HYBRID-CLASSIFIER] ✅ STAGE 4 SUCCESS: {ml_result.predicted_type} via {ml_result.method_used}")
            return ml_result
        else:
            logger.info(f"[HYBRID-CLASSIFIER] ⚪ STAGE 4: Heuristic fallback failed")'''
    
    content = content.replace(old_ml_stage, new_ml_stage)
    
    # Додаємо логування в default fallback
    old_default = '''        # 🔍 ЕТАП 5: Default fallback
        return ClassificationResult(
            predicted_type='general',
            confidence_score=0.0,
            method_used='default_fallback',
            rule_matches={},
            fallback_used=True
        )'''
    
    new_default = '''        # 🔍 ЕТАП 5: Default fallback
        logger.warning(f"[HYBRID-CLASSIFIER] ❌ ALL STAGES FAILED - Defaulting to 'general'")
        logger.warning(f"[HYBRID-CLASSIFIER] 📝 Failed text: {text[:300]}...")
        return ClassificationResult(
            predicted_type='general',
            confidence_score=0.0,
            method_used='default_fallback',
            rule_matches={},
            fallback_used=True
        )'''
    
    content = content.replace(old_default, new_default)
    
    with open('backend/webhooks/hybrid_chunk_classifier.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 2. Додаємо логування в створення chunks (vector_pdf_service.py)
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        pdf_content = f.read()
    
    # Додаємо логування після класифікації кожного chunk
    old_chunk_creation = '''                if token_count > 0:
                    chunks.append(DocumentChunk(
                        content=chunk_text.strip(),
                        page_number=1,  # Default for text input
                        chunk_index=chunk_index,
                        token_count=token_count,
                        chunk_type=self._identify_chunk_type(chunk_text),
                        metadata={
                            'has_inquiry': 'Inquiry information:' in chunk_text or 'Name:' in chunk_text,
                            'has_response': 'Response:' in chunk_text,
                            'has_customer_name': bool(re.search(r'Name:\\s*\\w+', chunk_text)),
                            'has_service_type': any(word in chunk_text.lower() for word in ['roof', 'repair', 'construction', 'service']),
                            'section_length': len(chunk_text),
                            'specialized_chunking': False
                        }
                    ))
                    chunk_index += 1'''
    
    new_chunk_creation = '''                if token_count > 0:
                    chunk_type = self._identify_chunk_type(chunk_text)
                    
                    logger.info(f"[VECTOR-PDF] 🧩 CREATING CHUNK #{chunk_index}:")
                    logger.info(f"[VECTOR-PDF]   Text length: {len(chunk_text)} chars")
                    logger.info(f"[VECTOR-PDF]   Token count: {token_count}")
                    logger.info(f"[VECTOR-PDF]   Classified as: {chunk_type}")
                    logger.info(f"[VECTOR-PDF]   Content preview: {chunk_text[:150]}...")
                    
                    # Детальна перевірка metadata
                    has_inquiry = 'Inquiry information:' in chunk_text or 'Name:' in chunk_text
                    has_response = 'Response:' in chunk_text
                    has_customer_name = bool(re.search(r'Name:\\s*\\w+', chunk_text))
                    has_service_type = any(word in chunk_text.lower() for word in ['roof', 'repair', 'construction', 'service'])
                    
                    logger.info(f"[VECTOR-PDF]   Metadata analysis:")
                    logger.info(f"[VECTOR-PDF]     - has_inquiry: {has_inquiry}")
                    logger.info(f"[VECTOR-PDF]     - has_response: {has_response}")
                    logger.info(f"[VECTOR-PDF]     - has_customer_name: {has_customer_name}")
                    logger.info(f"[VECTOR-PDF]     - has_service_type: {has_service_type}")
                    
                    chunks.append(DocumentChunk(
                        content=chunk_text.strip(),
                        page_number=1,  # Default for text input
                        chunk_index=chunk_index,
                        token_count=token_count,
                        chunk_type=chunk_type,
                        metadata={
                            'has_inquiry': has_inquiry,
                            'has_response': has_response,
                            'has_customer_name': has_customer_name,
                            'has_service_type': has_service_type,
                            'section_length': len(chunk_text),
                            'specialized_chunking': False
                        }
                    ))
                    chunk_index += 1'''
    
    pdf_content = pdf_content.replace(old_chunk_creation, new_chunk_creation)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(pdf_content)
    
    print("✅ Super detailed logging added!")

if __name__ == '__main__':
    add_super_detailed_logging()
