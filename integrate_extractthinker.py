#!/usr/bin/env python3
"""
🔧 Integrates ExtractThinker into VectorPDFService
"""

import re

def integrate_extractthinker():
    """Інтегрує ExtractThinker parser в VectorPDFService"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Додаємо import ExtractThinker
    old_imports = '''from .extraction_contracts import CustomerInquiry, BusinessResponse, SampleReplyExample, SampleRepliesDocument'''
    
    new_imports = '''# ExtractThinker integration
try:
    from .extractthinker_parser import extractthinker_parser
    from .extraction_contracts import CustomerInquiry, BusinessResponse, SampleReplyExample, SampleRepliesDocument
    EXTRACTTHINKER_INTEGRATION = True
    logger.info("[VECTOR-PDF] ✅ ExtractThinker integration available")
except ImportError as e:
    EXTRACTTHINKER_INTEGRATION = False
    logger.warning(f"[VECTOR-PDF] ⚠️ ExtractThinker integration not available: {e}")'''
    
    # Додаємо після основних imports
    content = content.replace(
        'logger = logging.getLogger(__name__)',
        f'''logger = logging.getLogger(__name__)

{new_imports}'''
    )
    
    # 2. Змінюємо _create_sample_replies_chunks для використання ExtractThinker
    old_sample_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Fallback: використовує стандартний chunking для Sample Replies"""
        
        logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker not available - using enhanced standard method")
        return self._create_standard_chunks(text, max_tokens)'''
    
    new_sample_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🎯 ExtractThinker-based Sample Replies parsing with Pydantic contracts"""
        
        if not EXTRACTTHINKER_INTEGRATION:
            logger.warning("[VECTOR-PDF] ⚠️ ExtractThinker not available - using standard chunking")
            return self._create_standard_chunks(text, max_tokens)
        
        try:
            logger.info("[VECTOR-PDF] 🧠 Using ExtractThinker for structured parsing...")
            
            # Використовуємо ExtractThinker для structured extraction
            document = extractthinker_parser.parse_sample_replies_document(text)
            
            if not document or not document.examples:
                logger.warning("[VECTOR-PDF] ⚠️ ExtractThinker found no examples, falling back")
                return self._create_standard_chunks(text, max_tokens)
            
            # Конвертуємо structured data в DocumentChunk об'єкти
            chunks = []
            chunk_index = 0
            
            logger.info(f"[VECTOR-PDF] 🎯 Converting {len(document.examples)} structured examples to chunks")
            
            for example in document.examples:
                # Inquiry chunk з enhanced metadata
                inquiry_chunk = DocumentChunk(
                    content=example.inquiry.raw_text,
                    page_number=1,
                    chunk_index=chunk_index,
                    token_count=self._count_tokens(example.inquiry.raw_text),
                    chunk_type='inquiry',
                    metadata={
                        'extractthinker_structured': True,
                        'example_number': example.example_number,
                        'customer_name': example.inquiry.customer_name,
                        'service_type': example.inquiry.service_type,
                        'location': example.inquiry.location,
                        'urgency': example.inquiry.service_urgency,
                        'building_stories': example.inquiry.building_stories,
                        'roof_covering': example.inquiry.roof_covering_type,
                        'chunk_purpose': 'customer_inquiry_structured'
                    }
                )
                chunks.append(inquiry_chunk)
                chunk_index += 1
                
                # Response chunk з enhanced metadata
                response_chunk = DocumentChunk(
                    content=example.response.raw_text,
                    page_number=1,
                    chunk_index=chunk_index,
                    token_count=self._count_tokens(example.response.raw_text),
                    chunk_type='response',
                    metadata={
                        'extractthinker_structured': True,
                        'example_number': example.example_number,
                        'customer_name': example.inquiry.customer_name,
                        'service_type': example.inquiry.service_type,
                        'greeting_type': example.response.greeting_type,
                        'tone': example.response.tone,
                        'has_questions': len(example.response.questions_asked or []) > 0,
                        'has_availability': bool(example.response.availability_mention),
                        'signature': example.response.signature,
                        'context_match_score': example.context_match_score,
                        'chunk_purpose': 'business_response_structured'
                    }
                )
                chunks.append(response_chunk)
                chunk_index += 1
                
                # Optional: Combined example chunk для context learning
                if len(example.inquiry.raw_text) + len(example.response.raw_text) < max_tokens * 3:
                    combined_content = f"CUSTOMER INQUIRY:\\n{example.inquiry.raw_text}\\n\\nBUSINESS RESPONSE:\\n{example.response.raw_text}"
                    
                    combined_chunk = DocumentChunk(
                        content=combined_content,
                        page_number=1,
                        chunk_index=chunk_index,
                        token_count=self._count_tokens(combined_content),
                        chunk_type='example',
                        metadata={
                            'extractthinker_structured': True,
                            'example_number': example.example_number,
                            'customer_name': example.inquiry.customer_name,
                            'service_type': example.inquiry.service_type,
                            'context_match_score': example.context_match_score,
                            'chunk_purpose': 'complete_conversation_example'
                        }
                    )
                    chunks.append(combined_chunk)
                    chunk_index += 1
            
            # Статистика
            chunk_stats = {}
            for chunk in chunks:
                chunk_stats[chunk.chunk_type] = chunk_stats.get(chunk.chunk_type, 0) + 1
            
            logger.info(f"[VECTOR-PDF] 🎉 EXTRACTTHINKER CHUNKING SUCCESS:")
            logger.info(f"[VECTOR-PDF]   Created {len(chunks)} structured chunks")
            logger.info(f"[VECTOR-PDF]   Examples processed: {len(document.examples)}")
            logger.info(f"[VECTOR-PDF]   Extraction quality: {document.extraction_quality}")
            logger.info(f"[VECTOR-PDF]   Chunk distribution: {chunk_stats}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] ❌ ExtractThinker chunking failed: {e}")
            logger.warning("[VECTOR-PDF] 🔄 Falling back to standard chunking")
            return self._create_standard_chunks(text, max_tokens)'''
    
    content = content.replace(old_sample_method, new_sample_method)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ ExtractThinker integrated into VectorPDFService!")

if __name__ == '__main__':
    integrate_extractthinker()
