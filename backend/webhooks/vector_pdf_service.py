"""
🔍 Clean Vector PDF Service 
Minimal working version without broken code
"""

import logging
import re
import hashlib
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import openai
import os

# PDF processing
try:
    import fitz
    import tiktoken
    import numpy as np
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    content: str
    page_number: int
    chunk_index: int
    token_count: int
    chunk_type: str
    metadata: Dict

class VectorPDFService:
    def __init__(self):
        self.openai_client = None
        self.encoding = None
        self._init_openai()
        self._init_tokenizer()
    
    def _init_openai(self):
        try:
            from .models import AISettings
            
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                ai_settings = AISettings.objects.first()
                if ai_settings and ai_settings.openai_api_key:
                    openai_api_key = ai_settings.openai_api_key
            
            if openai_api_key:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("[VECTOR-PDF] OpenAI client initialized successfully")
            else:
                logger.error("[VECTOR-PDF] No OpenAI API key found")
                
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Failed to initialize OpenAI client: {e}")
    
    def _init_tokenizer(self):
        try:
            if not PDF_PROCESSING_AVAILABLE:
                return
                
            self.encoding = tiktoken.encoding_for_model("text-embedding-3-small")
            logger.info("[VECTOR-PDF] Tiktoken encoder initialized")
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Failed to initialize tokenizer: {e}")
    
    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict:
        logger.info(f"[VECTOR-PDF] Extracting text from PDF: {filename}")
        
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing not available")
        
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
            
            doc.close()
            all_text = "\n\n".join(all_text_parts)
            
            logger.info(f"[VECTOR-PDF] Extracted {len(all_text)} chars from {len(pages_data)} pages")
            
            return {
                'success': True,
                'text': all_text,
                'pages': pages_data
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] PDF extraction error: {e}")
            return {
                'success': False,
                'text': '',
                'pages': [],
                'errors': [str(e)]
            }
    
    def extract_text_from_uploaded_file(self, file_content: bytes, filename: str) -> str:
        logger.info(f"[VECTOR-PDF] Processing {filename} ({len(file_content)} bytes)")
        
        try:
            if b'%PDF' in file_content[:100] or filename.lower().endswith('.pdf'):
                pdf_result = self.extract_text_from_pdf_bytes(file_content, filename)
                
                if pdf_result['success']:
                    return pdf_result['text']
                else:
                    return "PDF_PROCESSING_ERROR"
            else:
                text_content = file_content.decode('utf-8', errors='ignore')
                return text_content if text_content.strip() else "EMPTY_FILE"
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error processing {filename}: {e}")
            return "PROCESSING_ERROR"
    
    def create_semantic_chunks(self, text: str, max_tokens: int = 800) -> List[DocumentChunk]:
        logger.info(f"[VECTOR-PDF] Creating semantic chunks from {len(text)} chars")
        
        sections = self._split_by_sections(text)
        chunks = []
        chunk_index = 0
        
        for section in sections:
            if not section.strip() or len(section) < 20:
                continue
            
            token_count = self._count_tokens(section)
            chunk_type = self._identify_chunk_type(section)
            
            # ✅ IMPROVED METADATA based on chunk_type + better patterns
            metadata = {
                'section_length': len(section),
                'has_inquiry': chunk_type == 'inquiry',  # ✅ Base on classification
                'has_response': chunk_type == 'response',  # ✅ Base on classification
                'has_customer_name': self._detect_customer_name(section),  # ✅ Improved detection
                'chunk_quality': self._assess_chunk_quality(section, chunk_type)  # ✅ New quality metric
            }
            
            logger.info(f"[VECTOR-PDF] CHUNK #{chunk_index}: {chunk_type} ({len(section)} chars)")
            logger.info(f"[VECTOR-PDF]   Preview: {section[:100]}...")
            logger.info(f"[VECTOR-PDF]   Metadata: has_inquiry={metadata['has_inquiry']}, has_response={metadata['has_response']}, has_name={metadata['has_customer_name']}, quality={metadata['chunk_quality']}")
            
            chunks.append(DocumentChunk(
                content=section.strip(),
                page_number=1,
                chunk_index=chunk_index,
                token_count=token_count,
                chunk_type=chunk_type,
                metadata=metadata
            ))
            chunk_index += 1
        
        logger.info(f"[VECTOR-PDF] Created {len(chunks)} chunks")
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """
        🎯 Новий підхід: розділяє текст на чанки по маркерам Inquiry: та Reply:
        
        Логіка:
        1. Inquiry: ... (до Reply:) -> перший чанк
        2. Reply: ... (до наступного Inquiry:) -> другий чанк
        3. І так далі...
        """
        logger.info(f"[VECTOR-PDF] 🎯 NEW CHUNKING: Splitting by Inquiry:/Reply: markers...")
        
        sections = []
        
        # Знаходимо всі позиції Inquiry: та Reply:
        inquiry_pattern = re.compile(r'\bInquiry:\s*', re.IGNORECASE)
        reply_pattern = re.compile(r'\bReply:\s*', re.IGNORECASE)
        
        inquiry_positions = [(m.start(), m.end(), 'inquiry') for m in inquiry_pattern.finditer(text)]
        reply_positions = [(m.start(), m.end(), 'reply') for m in reply_pattern.finditer(text)]
        
        # Об'єднуємо та сортуємо всі позиції
        all_markers = sorted(inquiry_positions + reply_positions, key=lambda x: x[0])
        
        logger.info(f"[VECTOR-PDF] Found {len(inquiry_positions)} Inquiry: markers")
        logger.info(f"[VECTOR-PDF] Found {len(reply_positions)} Reply: markers")
        logger.info(f"[VECTOR-PDF] Total markers: {len(all_markers)}")
        
        if not all_markers:
            logger.warning(f"[VECTOR-PDF] ⚠️ No Inquiry:/Reply: markers found, using fallback")
            # Fallback: повертаємо весь текст як один чанк
            return [text.strip()] if text.strip() else []
        
        # Створюємо чанки між маркерами
        for i in range(len(all_markers)):
            marker_start, marker_end, marker_type = all_markers[i]
            
            # Визначаємо кінець чанка
            if i + 1 < len(all_markers):
                next_marker_start = all_markers[i + 1][0]
                chunk_text = text[marker_start:next_marker_start].strip()
            else:
                # Останній чанк - до кінця тексту
                chunk_text = text[marker_start:].strip()
            
            if chunk_text and len(chunk_text) > 20:
                sections.append(chunk_text)
                logger.info(f"[VECTOR-PDF]   Chunk {len(sections)}: {marker_type}, {len(chunk_text)} chars")
                logger.info(f"[VECTOR-PDF]     Preview: {chunk_text[:80]}...")
        
        logger.info(f"[VECTOR-PDF] ✅ Created {len(sections)} chunks using Inquiry:/Reply: splitting")
        return sections
    
    def _identify_chunk_type(self, text: str) -> str:
        """
        🎯 Спрощена класифікація: перевіряємо початок чанка
        
        Оскільки ми тепер ділимо по маркерам Inquiry:/Reply:,
        класифікація стає тривіальною - просто дивимося на початок
        """
        text_lower = text.lower().strip()
        
        # Перевіряємо початок чанка
        if text_lower.startswith('inquiry:'):
            logger.info(f"[VECTOR-PDF] ✅ INQUIRY (starts with 'Inquiry:')")
            return 'inquiry'
        elif text_lower.startswith('reply:'):
            logger.info(f"[VECTOR-PDF] ✅ RESPONSE (starts with 'Reply:')")
            return 'response'
        
        # Fallback для інших випадків (наприклад, якщо є вступний текст)
        # Перевіряємо, чи є маркер десь в тексті
        if 'inquiry:' in text_lower[:100]:
            logger.info(f"[VECTOR-PDF] ✅ INQUIRY (contains 'Inquiry:' in first 100 chars)")
            return 'inquiry'
        elif 'reply:' in text_lower[:100]:
            logger.info(f"[VECTOR-PDF] ✅ RESPONSE (contains 'Reply:' in first 100 chars)")
            return 'response'
        
        # Якщо це вступний текст (наприклад, "EXAMPLE FILE:")
        if text_lower.startswith('example') or 'example file' in text_lower[:100]:
            logger.info(f"[VECTOR-PDF] ✅ EXAMPLE (introductory text)")
            return 'example'
        
        logger.warning(f"[VECTOR-PDF] ⚠️ GENERAL (no clear marker found)")
        logger.warning(f"[VECTOR-PDF]   Text preview: {text[:100]}...")
        return 'general'
    
    def _count_tokens(self, text: str) -> int:
        if not self.encoding:
            return len(text) // 4
        return len(self.encoding.encode(text))
    
    def _detect_customer_name(self, text: str) -> bool:
        """🔍 Improved customer name detection with multiple patterns"""
        
        name_patterns = [
            r'name:\s*[A-Za-z]+[\s\.]*[A-Za-z]*\.?',  # "Name: Beau S.", "Name: Jenny Z"
            r'name\s+[A-Za-z]+[\s\.]*[A-Za-z]*\.?',   # "Name Stephen S." (no colon)
            r'name:\s*[A-Za-z]+',                     # Basic "Name: John"
            r'^[A-Za-z]+\s*[A-Za-z]\.?\s*$',         # "Beau S." at start of line
        ]
        
        text_clean = text.strip()
        for pattern in name_patterns:
            if re.search(pattern, text_clean, re.IGNORECASE):
                return True
        
        return False

    def _assess_chunk_quality(self, text: str, chunk_type: str) -> str:
        """
        🎯 Оцінка якості чанка для векторного пошуку
        
        З новим підходом розділення, всі inquiry та response чанки
        є повноцінними, тому якість завжди excellent
        """
        
        if chunk_type == 'inquiry':
            # Inquiry чанк тепер завжди містить повну інформацію про клієнта
            has_name = self._detect_customer_name(text)
            has_service = any(x in text.lower() for x in [
                'roof', 'repair', 'replace', 'remodel', 'construction', 'structural',
                'foundation', 'bathroom', 'kitchen', 'addition', 'deck', 'patio'
            ])
            has_location = bool(re.search(r'\d{5}', text))  # ZIP code
            has_timeline = any(x in text.lower() for x in ['soon as possible', 'flexible', 'specific date', 'require this service'])
            
            score = sum([has_name, has_service, has_location, has_timeline])
            return 'excellent' if score >= 3 else 'good' if score >= 2 else 'basic'
            
        elif chunk_type == 'response':
            # Response чанк тепер завжди містить повну відповідь бізнесу
            has_greeting = any(x in text.lower() for x in ['good afternoon', 'good morning', 'good evening', 'thanks', 'hello', 'hi'])
            has_personalization = any(x in text.lower() for x in ['hope', 'looking forward', 'sounds like', 'understand'])
            has_call_to_action = any(x in text.lower() for x in ['come by', 'walk', 'meet', 'stop by', 'let me know'])
            has_signature = any(x in text.lower() for x in ['-ben', 'talk soon', 'best', 'looking forward'])
            
            score = sum([has_greeting, has_personalization, has_call_to_action, has_signature])
            return 'excellent' if score >= 3 else 'good' if score >= 2 else 'basic'
        
        elif chunk_type == 'example':
            # Вступний текст або повний приклад
            return 'excellent'
        
        return 'basic'
    
    def generate_embeddings(self, chunks: List[DocumentChunk]) -> List[Tuple[DocumentChunk, List[float]]]:
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        logger.info(f"[VECTOR-PDF] Generating embeddings for {len(chunks)} chunks")
        
        try:
            texts = [chunk.content for chunk in chunks]
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=1536
            )
            
            embeddings_data = []
            for chunk, embedding_obj in zip(chunks, response.data):
                embeddings_data.append((chunk, embedding_obj.embedding))
            
            logger.info(f"[VECTOR-PDF] Generated {len(embeddings_data)} embeddings")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error generating embeddings: {e}")
            raise
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        return hashlib.sha256(file_content).hexdigest()
    
    def process_pdf_file(self, file_content: bytes, filename: str, business_id: str, location_id: Optional[str] = None, phone_available: bool = False) -> Dict:
        logger.info(f"[VECTOR-PDF] ======== PROCESSING PDF ========")
        logger.info(f"[VECTOR-PDF] File: {filename}")
        logger.info(f"[VECTOR-PDF] Business: {business_id}")
        logger.info(f"[VECTOR-PDF] Phone Available: {phone_available}")
        
        try:
            # Extract text
            if b'%PDF' in file_content[:100] or filename.lower().endswith('.pdf'):
                pdf_result = self.extract_text_from_pdf_bytes(file_content, filename)
                
                if not pdf_result['success']:
                    raise ValueError("Failed to extract text from PDF")
                
                all_text = pdf_result['text']
                page_count = len(pdf_result['pages'])
            else:
                all_text = file_content.decode('utf-8', errors='ignore')
                page_count = 1
            
            if not all_text.strip():
                raise ValueError("No text content found")
            
            # Create chunks
            chunks = self.create_semantic_chunks(all_text)
            
            if not chunks:
                raise ValueError("No chunks created")
            
            # Generate embeddings
            embeddings_data = self.generate_embeddings(chunks)
            
            # Save to database
            from .vector_models import VectorDocument, VectorChunk
            
            with transaction.atomic():
                file_hash = self.calculate_file_hash(file_content)
                
                # Handle duplicates - видаляємо тільки якщо той самий файл для того ж business + phone_available
                try:
                    existing_doc = VectorDocument.objects.get(
                        business_id=business_id,
                        phone_available=phone_available,
                        file_hash=file_hash
                    )
                    logger.warning(f"[VECTOR-PDF] Deleting existing document with same hash for this phone_available mode")
                    existing_doc.delete()
                except VectorDocument.DoesNotExist:
                    pass
                
                document = VectorDocument.objects.create(
                    business_id=business_id,
                    location_id=location_id,
                    phone_available=phone_available,
                    filename=filename,
                    file_hash=file_hash,
                    file_size=len(file_content),
                    page_count=page_count,
                    chunk_count=len(chunks),
                    total_tokens=sum(chunk.token_count for chunk in chunks),
                    processing_status='completed',
                    embedding_model='text-embedding-3-small',
                    embedding_dimensions=1536,
                    metadata={
                            'chunks_by_type': {
                                chunk_type: len([c for c in chunks if c.chunk_type == chunk_type])
                                for chunk_type in set(chunk.chunk_type for chunk in chunks)
                        }
                    }
                )
                
                # Create chunks
                chunk_objects = []
                for chunk, embedding in embeddings_data:
                    chunk_obj = VectorChunk(
                        document=document,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        token_count=chunk.token_count,
                        embedding=embedding,
                        chunk_type=chunk.chunk_type,
                        metadata=chunk.metadata
                    )
                    chunk_objects.append(chunk_obj)
                
                VectorChunk.objects.bulk_create(chunk_objects)
                
                logger.info(f"[VECTOR-PDF] ✅ SUCCESS: {len(chunk_objects)} chunks saved")
                
                # Log chunk statistics
                chunk_stats = document.metadata['chunks_by_type']
                logger.info(f"[VECTOR-PDF] Chunk types: {chunk_stats}")
                
                for chunk_type, count in chunk_stats.items():
                    logger.info(f"[VECTOR-PDF]   {chunk_type}: {count}")
            
            return {
                'document_id': document.id,
                'chunks_count': len(chunk_objects),
                'pages_count': page_count,
                'total_tokens': sum(chunk.token_count for chunk, _ in embeddings_data),
                'chunk_types': chunk_stats
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error processing PDF: {e}")
            raise
    
    def format_sample_replies(self, raw_content: str) -> str:
        if raw_content in ["PDF_BINARY_DETECTED", "PROCESSING_ERROR", "EMPTY_FILE", "ENCODING_ERROR"]:
            return raw_content
        
        if not raw_content or not raw_content.strip():
            return "EMPTY_CONTENT"
        
        # Basic text cleanup
        cleaned = raw_content.strip()
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
        cleaned = re.sub(r' +', ' ', cleaned)
        
        logger.info(f"[VECTOR-PDF] Formatted content: {len(cleaned)} chars")
        return cleaned
    
    def validate_sample_replies_content(self, content: str) -> tuple[bool, Optional[str]]:
        if not content or not content.strip():
            return False, "Empty content"
        
        if len(content.strip()) < 50:
            return False, "Content too short"
        
        if len(content) > 100000:
            return False, "Content too long"
        
        return True, None


# Global instances
vector_pdf_service = VectorPDFService()
simple_pdf_service = vector_pdf_service
