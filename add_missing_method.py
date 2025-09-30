#!/usr/bin/env python3
"""
🔧 Add missing extract_text_from_uploaded_file method
"""

def add_missing_method():
    """Додає відсутній метод extract_text_from_uploaded_file"""
    
    with open('backend/webhooks/vector_pdf_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Додаємо метод після extract_text_from_pdf_bytes
    insertion_point = content.find('    def create_semantic_chunks(self, text: str, max_tokens: int = 800) -> List[DocumentChunk]:')
    
    if insertion_point == -1:
        print("❌ Insertion point not found")
        return
    
    missing_method = '''    def extract_text_from_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """Legacy method for fallback compatibility"""
        
        logger.info(f"[VECTOR-PDF] 📄 Processing {filename} ({len(file_content)} bytes)")
        
        try:
            if b'%PDF' in file_content[:100] or filename.lower().endswith('.pdf'):
                pdf_result = self.extract_text_from_pdf_bytes(file_content, filename)
                
                if pdf_result['success']:
                    return pdf_result['text']
                else:
                    return "PDF_PROCESSING_ERROR"
            else:
                # Plain text file
                text_content = file_content.decode('utf-8', errors='ignore')
                return text_content if text_content.strip() else "EMPTY_FILE"
                
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error processing {filename}: {e}")
            return "PROCESSING_ERROR"

    '''
    
    # Вставляємо метод
    before = content[:insertion_point]
    after = content[insertion_point:]
    content = before + missing_method + after
    
    with open('backend/webhooks/vector_pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Added missing extract_text_from_uploaded_file method!")

if __name__ == '__main__':
    add_missing_method()
