"""
🔍 Minimal Working Vector PDF Service
Simplified version without broken code
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

# PDF processing imports
try:
    import fitz  # PyMuPDF
    import tiktoken
    import numpy as np
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Представляє семантичний чанк документу"""
    content: str
    page_number: int
    chunk_index: int
    token_count: int
    chunk_type: str
    metadata: Dict

class VectorPDFService:
    """🔍 Мінімальний векторний сервіс для обробки PDF"""
    
    def __init__(self):
        self.openai_client = None
        self.encoding = None
        self._init_openai()
        self._init_tokenizer()
    
    def _init_openai(self):
        """Ініціалізація OpenAI клієнта"""
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
        """Ініціалізація tiktoken енкодера"""
        try:
            if not PDF_PROCESSING_AVAILABLE:
                logger.warning("[VECTOR-PDF] Tiktoken not available")
                return
                
            self.encoding = tiktoken.encoding_for_model("text-embedding-3-small")
            logger.info("[VECTOR-PDF] Tiktoken encoder initialized")
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Failed to initialize tokenizer: {e}")
    
    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict:
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
            
            doc.close()
            all_text = "\n\n".join(all_text_parts)
            
            logger.info(f"[VECTOR-PDF] Extracted {len(all_text)} chars from {len(pages_data)} pages")
            
            return {
                'success': True,
                'text': all_text,
                'pages': pages_data,
                'parser_used': 'pymupdf'
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] PDF extraction error: {e}")
            return {
                'success': False,
                'text': '',
                'pages': [],
                'errors': [str(e)]
            }
    
    def create_semantic_chunks(self, text: str, max_tokens: int = 800) -> List[DocumentChunk]:
        """Створює семантичні чанки з тексту"""
        
        logger.info(f"[VECTOR-PDF] Creating semantic chunks...")
        logger.info(f"[VECTOR-PDF] Text length: {len(text)} chars")
        
        # Розділення на секції
        sections = self._split_by_sections(text)
        
        chunks = []
        chunk_index = 0
        
        for section in sections:
            if not section.strip() or len(section) < 20:
                continue
            
            token_count = self._count_tokens(section)
            chunk_type = self._identify_chunk_type(section)
            
            logger.info(f"[VECTOR-PDF] 🧩 CHUNK #{chunk_index}:")
            logger.info(f"[VECTOR-PDF]   Type: {chunk_type}")
            logger.info(f"[VECTOR-PDF]   Length: {len(section)} chars")
            logger.info(f"[VECTOR-PDF]   Preview: {section[:100]}...")
            
            chunks.append(DocumentChunk(
                content=section.strip(),
                page_number=1,
                chunk_index=chunk_index,
                token_count=token_count,
                chunk_type=chunk_type,
                metadata={
                    'section_length': len(section),
                    'has_inquiry': 'inquiry information:' in section.lower(),
                    'has_response': 'response:' in section.lower(),
                    'has_customer_name': bool(re.search(r'name:\s*\w+', section, re.IGNORECASE)),
                }
            ))
            chunk_index += 1
        
        logger.info(f"[VECTOR-PDF] Created {len(chunks)} chunks")
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """Розділяє текст на логічні секції"""
        
        logger.info(f"[VECTOR-PDF] Splitting text into sections...")
        
        patterns = [
            r'Example\s*#\d+',
            r'Inquiry information:',
            r'Response:',
            r'\n\n\n+',
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
        
        return [s for s in sections if len(s.strip()) > 20]
    
    def _identify_chunk_type(self, text: str) -> str:
        """Визначає тип чанка з enhanced logic"""
        
        text_lower = text.lower().strip()
        
        # Explicit markers
        if 'inquiry information:' in text_lower:
            return 'inquiry'
        elif 'response:' in text_lower:
            return 'response'
        
        # Business response patterns (Norma's style)
        business_patterns = ['good afternoon', 'good morning', 'thanks for reaching', 
                           'thanks so much', "we'd be glad", 'talk soon', 'norma']
        business_matches = sum(1 for pattern in business_patterns if pattern in text_lower)
        
        # Customer inquiry patterns
        inquiry_patterns = ['name:', 'lead created:', 'what kind of', 'how many stories']
        inquiry_matches = sum(1 for pattern in inquiry_patterns if pattern in text_lower)
        
        if business_matches >= 2:
            logger.info(f"[VECTOR-PDF] ✅ BUSINESS RESPONSE ({business_matches} matches)")
            return 'response'
        elif inquiry_matches >= 2:
            logger.info(f"[VECTOR-PDF] ✅ CUSTOMER INQUIRY ({inquiry_matches} matches)")
            return 'inquiry'
        elif business_matches > 0:
            return 'response'
        elif inquiry_matches > 0:
            return 'inquiry'
        else:
            return 'general'
    
    def _count_tokens(self, text: str) -> int:
        """Підрахунок токенів"""
        if not self.encoding:
            return len(text) // 4
        return len(self.encoding.encode(text))
    
    def generate_embeddings(self, chunks: List[DocumentChunk]) -> List[Tuple[DocumentChunk, List[float]]]:
        """Генерує OpenAI ембедінги"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        logger.info(f"[VECTOR-PDF] Generating embeddings for {len(chunks)} chunks")
        
        embeddings_data = []
        
        try:
            texts = [chunk.content for chunk in chunks]
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=1536
            )
            
            for chunk, embedding_obj in zip(chunks, response.data):
                embeddings_data.append((chunk, embedding_obj.embedding))
            
            logger.info(f"[VECTOR-PDF] Generated {len(embeddings_data)} embeddings")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error generating embeddings: {e}")
            raise
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """Розраховує хеш файлу"""
        return hashlib.sha256(file_content).hexdigest()
    
    def process_pdf_file(
        self, 
        file_content: bytes, 
        filename: str, 
        business_id: str,
        location_id: Optional[str] = None
    ) -> Dict:
        """Головний метод обробки PDF"""
        
        logger.info(f"[VECTOR-PDF] ======== PROCESSING PDF ========")
        logger.info(f"[VECTOR-PDF] File: {filename}")
        logger.info(f"[VECTOR-PDF] Business: {business_id}")
        
        try:
            # Витягування тексту
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
            
            # Створення чанків
            chunks = self.create_semantic_chunks(all_text)
            
            if not chunks:
                raise ValueError("No chunks created")
            
            # Генерація ембедінгів
            embeddings_data = self.generate_embeddings(chunks)
            
            # Збереження в БД
            from .vector_models import VectorDocument, VectorChunk
            
            with transaction.atomic():
                file_hash = self.calculate_file_hash(file_content)
                
                document = VectorDocument.objects.create(
                    business_id=business_id,
                    location_id=location_id,
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
                
                # Створення чанків
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
                logger.info(f"[VECTOR-PDF] Types: {document.metadata['chunks_by_type']}")
            
            return {
                'document_id': document.id,
                'chunks_count': len(chunk_objects),
                'chunk_types': document.metadata['chunks_by_type']
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error: {e}")
            raise


# Глобальна змінна (ВАЖЛИВО!)
vector_pdf_service = VectorPDFService()
simple_pdf_service = vector_pdf_service  # Legacy compatibility
