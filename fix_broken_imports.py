#!/usr/bin/env python3
"""
🔧 Fix broken imports and method calls in VectorPDFService
"""

import re

def fix_broken_imports():
    """Виправляє всі broken посилання в VectorPDFService"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Видаляємо broken import та змінну ADVANCED_PDF_PARSER_AVAILABLE
    old_import = '''# Import the advanced PDF parser
try:
    from .advanced_pdf_parser import advanced_pdf_parser
    ADVANCED_PDF_PARSER_AVAILABLE = True
    logger.info("[VECTOR-PDF] ✅ Advanced PDF Parser loaded")
except ImportError as e:
    ADVANCED_PDF_PARSER_AVAILABLE = False
    logger.warning(f"[VECTOR-PDF] ⚠️ Advanced PDF Parser not available: {e}")'''
    
    # Просто видаляємо цей блок
    content = content.replace(old_import, '')
    
    # 2. Замінюємо метод extract_text_from_pdf_bytes на простий
    old_method = '''    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict:
        """🚀 Professional PDF extraction using advanced parser"""
        
        if ADVANCED_PDF_PARSER_AVAILABLE:
            logger.info(f"[VECTOR-PDF] 🚀 Using Advanced PDF Parser for: {filename}")
            
            try:
                result = advanced_pdf_parser.extract_text_from_pdf_bytes(pdf_bytes, filename)
                
                if result['success']:
                    logger.info(f"[VECTOR-PDF] ✅ Advanced parser success!")
                    logger.info(f"[VECTOR-PDF] Parser used: {result['parser_used']}")
                    logger.info(f"[VECTOR-PDF] Structure preserved: {result['structure_preserved']}")
                    logger.info(f"[VECTOR-PDF] Sections detected: {len(result['sections_detected'])}")
                    
                    for section in result['sections_detected']:
                        logger.info(f"[VECTOR-PDF]   📋 {section}")
                    
                    return result
                else:
                    logger.warning(f"[VECTOR-PDF] ⚠️ Advanced parser failed, falling back to basic method")
                    for error in result['errors']:
                        logger.warning(f"[VECTOR-PDF]   - {error}")
                        
            except Exception as e:
                logger.error(f"[VECTOR-PDF] ❌ Advanced parser exception: {e}")
        
        # Fallback to old method
        logger.info(f"[VECTOR-PDF] 🔄 Using fallback PDF extraction")
        return self._extract_text_fallback(pdf_bytes, filename)'''
    
    new_method = '''    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict:
        """📄 Simple PDF extraction using PyMuPDF"""
        
        logger.info(f"[VECTOR-PDF] 📄 Extracting text from PDF: {filename}")
        
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing libraries not available.")
        
        try:
            doc = fitz.open("pdf", pdf_bytes)
            pages_data = []
            all_text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                if text.strip():
                    pages_data.append({
                        'page_number': page_num + 1,
                        'text': text,
                        'char_count': len(text)
                    })
                    all_text_parts.append(text)
                    
                    logger.info(f"[VECTOR-PDF] Page {page_num + 1}: {len(text)} chars")
            
            doc.close()
            
            all_text = "\\n\\n".join(all_text_parts)
            
            # Аналіз структури PDF
            text_lower = all_text.lower()
            structure_indicators = {
                'inquiry_information': 'inquiry information:' in text_lower,
                'response_marker': 'response:' in text_lower,
                'example_marker': 'example #' in text_lower,
                'customer_names': len(re.findall(r'name:\\s*[a-z]+ [a-z]\\.?', text_lower)),
                'norma_signatures': len(re.findall(r'talk soon,?\\s*norma', text_lower, re.IGNORECASE))
            }
            
            logger.info(f"[VECTOR-PDF] 📊 PDF Structure Analysis:")
            logger.info(f"[VECTOR-PDF]   Text length: {len(all_text)} chars")
            logger.info(f"[VECTOR-PDF]   Pages extracted: {len(pages_data)}")
            for key, value in structure_indicators.items():
                logger.info(f"[VECTOR-PDF]   {key}: {value}")
            
            return {
                'success': True,
                'text': all_text,
                'pages': pages_data,
                'parser_used': 'pymupdf',
                'structure_preserved': True,
                'sections_detected': [f"{k}: {v}" for k, v in structure_indicators.items() if v],
                'structure_quality_score': sum(1 for v in structure_indicators.values() if v)
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] PDF extraction error: {e}")
            return {
                'success': False,
                'text': '',
                'pages': [],
                'parser_used': None,
                'structure_preserved': False,
                'sections_detected': [],
                'errors': [str(e)]
            }'''
    
    content = content.replace(old_method, new_method)
    
    # 3. Видаляємо метод _extract_text_fallback (він дублює функціональність)
    fallback_method_pattern = r'    def _extract_text_fallback\(self, pdf_bytes: bytes, filename: str\) -> Dict:.*?return \{[^}]+\}'
    content = re.sub(fallback_method_pattern, '', content, flags=re.DOTALL)
    
    # 4. Виправляємо виклик старого методу extract_text_from_pdf
    content = content.replace(
        'pages_data = self.extract_text_from_pdf(full_path)',
        '# Using new extract_text_from_pdf_bytes method instead'
    )
    
    # 5. Видаляємо broken посилання на sample_replies_chunker
    content = content.replace(
        'sections = sample_replies_chunker.parse_sample_replies_document(text)',
        '# sample_replies_chunker removed - using standard method'
    )
    
    # 6. Виправляємо broken _create_sample_replies_chunks method
    old_sample_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """Створює chunks використовуючи спеціалізований Sample Replies chunker"""
        
        try:
            # Використовуємо спеціалізований chunker
            sections = sample_replies_chunker.parse_sample_replies_document(text)
            
            if not sections:
                logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker failed, falling back to standard")
                return self._create_standard_chunks(text, max_tokens)
            
            # Конвертуємо в DocumentChunk об'єкти
            chunks = []
            chunk_index = 0
            
            for section in sections:
                # Inquiry chunk
                inquiry_chunk = DocumentChunk(
                    content=section.inquiry_text,
                    page_number=1,
                    chunk_index=chunk_index,
                    token_count=self._count_tokens(section.inquiry_text),
                    chunk_type='inquiry',
                    metadata={
                        'example_number': section.example_number,
                        'customer_name': section.customer_name,
                        'service_type': section.service_type,
                        'location': section.location,
                        'chunk_purpose': 'customer_data',
                        'has_inquiry': True,
                        'has_response': False,
                        'specialized_chunking': True
                    }
                )
                chunks.append(inquiry_chunk)
                chunk_index += 1
                
                # Response chunk  
                response_chunk = DocumentChunk(
                    content=section.response_text,
                    page_number=1,
                    chunk_index=chunk_index,
                    token_count=self._count_tokens(section.response_text),
                    chunk_type='response',
                    metadata={
                        'example_number': section.example_number,
                        'customer_name': section.customer_name,
                        'service_type': section.service_type,
                        'location': section.location,
                        'chunk_purpose': 'business_response',
                        'has_inquiry': False,
                        'has_response': True,
                        'specialized_chunking': True,
                        'response_style': section.raw_response[:50] + '...' if len(section.raw_response) > 50 else section.raw_response
                    }
                )
                chunks.append(response_chunk)
                chunk_index += 1
            
            logger.info(f"[VECTOR-PDF] 🎉 SPECIALIZED CHUNKING SUCCESS:")
            logger.info(f"[VECTOR-PDF] Created {len(chunks)} specialized chunks from {len(sections)} examples")
            
            # Статистика
            chunk_stats = {}
            for chunk in chunks:
                chunk_stats[chunk.chunk_type] = chunk_stats.get(chunk.chunk_type, 0) + 1
            logger.info(f"[VECTOR-PDF] Chunk distribution: {chunk_stats}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] ❌ Specialized chunking failed: {e}")
            logger.warning("[VECTOR-PDF] 🔄 Falling back to standard chunking")
            return self._create_standard_chunks(text, max_tokens)'''
    
    new_sample_method = '''    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Fallback: використовує стандартний chunking для Sample Replies"""
        
        logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker not available - using enhanced standard method")
        return self._create_standard_chunks(text, max_tokens)'''
    
    content = content.replace(old_sample_method, new_sample_method)
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed all broken imports and method calls!")

if __name__ == '__main__':
    fix_broken_imports()
