"""
🔍 Vector-Enhanced PDF Processing Service for Sample Replies
Семантичне чанкування, генерація ембедінгів OpenAI та векторне зберігання
"""

import logging
import re
import hashlib
import asyncio
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
    """🔍 Векторний сервіс для обробки PDF з семантичним чанкуванням та ембедінгами"""
    
    def __init__(self):
        self.openai_client = None
        self.encoding = None
        self._init_openai()
        self._init_tokenizer()
    
    def _init_openai(self):
        """Ініціалізація OpenAI клієнта"""
        try:
            from .models import AISettings
            
            # Try environment variable first
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                # Try database settings
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
        """Ініціалізація tiktoken encoder для text-embedding-3-small"""
        try:
            if PDF_PROCESSING_AVAILABLE:
                self.encoding = tiktoken.get_encoding("cl100k_base")
                logger.info("[VECTOR-PDF] Tiktoken encoder initialized")
            else:
                logger.warning("[VECTOR-PDF] Tiktoken not available, using fallback token counting")
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
                    
                    logger.info(f"[VECTOR-PDF] Page {page_num + 1}: {len(text)} chars")
            
            doc.close()
            
            all_text = "\n\n".join(all_text_parts)
            
            # Аналіз структури PDF
            text_lower = all_text.lower()
            structure_indicators = {
                'inquiry_information': 'inquiry information:' in text_lower,
                'response_marker': 'response:' in text_lower,
                'example_marker': 'example #' in text_lower,
                'customer_names': len(re.findall(r'name:\s*[a-z]+ [a-z]\.?', text_lower)),
                'norma_signatures': len(re.findall(r'talk soon,?\s*norma', text_lower, re.IGNORECASE))
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
            }
    

            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Fallback extraction error: {e}")
            return {
                'success': False,
                'text': '',
                'pages': [],
                'parser_used': None,
                'structure_preserved': False,
                'sections_detected': [],
                'errors': [str(e)]
            }
    
    def extract_text_from_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """Базовий парсинг файлу з підтримкою PDF та text"""
        
        logger.info(f"[VECTOR-PDF] 📄 Processing {filename} ({len(file_content)} bytes)")
        
        try:
            # Перевірка чи це PDF файл
            if b'%PDF' in file_content[:100] or filename.lower().endswith('.pdf'):
                if not PDF_PROCESSING_AVAILABLE:
                    logger.warning(f"[VECTOR-PDF] ⚠️ PDF detected but PyMuPDF not available: {filename}")
                    return "PDF_BINARY_DETECTED_NO_PARSER"
                
                # Збереження тимчасового файлу для PyMuPDF
                temp_path = f"temp_pdfs/{hashlib.md5(file_content).hexdigest()}_{filename}"
                saved_path = default_storage.save(temp_path, ContentFile(file_content))
                full_path = default_storage.path(saved_path)
                
                try:
                    # Using new extract_text_from_pdf_bytes method instead
                    all_text = "\n\n".join(page['text'] for page in pages_data)
                    return all_text
                finally:
                    # Очищення тимчасового файлу
                    try:
                        default_storage.delete(saved_path)
                    except:
                        pass
            else:
                # Спроба витягти текст як plain text
                text_content = file_content.decode('utf-8', errors='ignore')
                
                # Перевірка чи файл не порожній
                if not text_content.strip():
                    logger.warning(f"[VECTOR-PDF] ⚠️ Empty file: {filename}")
                    return "EMPTY_FILE"
                
                logger.info(f"[VECTOR-PDF] ✅ Successfully extracted {len(text_content)} characters")
                return text_content
                
        except UnicodeDecodeError:
            logger.error(f"[VECTOR-PDF] ❌ Unicode decode error: {filename}")
            return "ENCODING_ERROR"
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] ❌ Error processing {filename}: {e}")
            return "PROCESSING_ERROR"
    
    def create_semantic_chunks(self, text: str, max_tokens: int = 800) -> List[DocumentChunk]:
        """🎯 Розумне створення chunks з детекцією Sample Replies структури"""
        
        logger.info(f"[VECTOR-PDF] 🧠 SMART CHUNKING: Analyzing document structure...")
        logger.info(f"[VECTOR-PDF] Text length: {len(text)} chars, max_tokens: {max_tokens}")
        
        # Детекція чи це Sample Replies документ
        is_sample_replies = self._detect_sample_replies_document(text)
        
        if is_sample_replies:
            logger.info(f"[VECTOR-PDF] 🎯 SAMPLE REPLIES DETECTED - Using specialized chunker")
            return self._create_sample_replies_chunks(text, max_tokens)
        else:
            logger.info(f"[VECTOR-PDF] 📄 REGULAR DOCUMENT - Using standard chunking")
            return self._create_standard_chunks(text, max_tokens)
    
    def _detect_sample_replies_document(self, text: str) -> bool:
        """Детектує чи це документ Sample Replies"""
        
        text_lower = text.lower()
        
        # Ключові індикатори Sample Replies
        indicators = [
            'inquiry information:' in text_lower,
            'response:' in text_lower,
            'example #' in text_lower or 'example#' in text_lower,
            bool(re.search(r'name:\s*[a-z]+ [a-z]\.?', text_lower)),  # Name: John D. - перетворюємо в boolean
            'talk soon' in text_lower
        ]
        
        detected_count = sum(indicators)
        is_sample_replies = detected_count >= 2  # Мінімум 2 індикатори
        
        logger.info(f"[VECTOR-PDF] 🔍 Sample Replies detection:")
        logger.info(f"[VECTOR-PDF]   Indicators found: {detected_count}/5")
        logger.info(f"[VECTOR-PDF]   Is Sample Replies: {is_sample_replies}")
        
        return is_sample_replies
    
    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Fallback: використовує стандартний chunking для Sample Replies"""
        
        logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker not available - using enhanced standard method")
        return self._create_standard_chunks(text, max_tokens)

    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """Стандартне створення chunks (original method)"""
        
        logger.info(f"[VECTOR-PDF] 📄 Using standard chunking method")
        
        chunks = []
        chunk_index = 0
        
        # Розділення на секції/приклади спочатку
        sections = self._split_by_sections(text)
        
        for section in sections:
            if not section.strip():
                continue
            
            # Додаткове розділення якщо секція занадто довга
            section_chunks = self._split_long_text(section, max_tokens)
            
            for chunk_text in section_chunks:
                token_count = self._count_tokens(chunk_text)
                
                if token_count > 0:
                    chunk_type = self._identify_chunk_type(chunk_text)
                    
                    logger.info(f"[VECTOR-PDF] 🧩 CREATING CHUNK #{chunk_index}:")
                    logger.info(f"[VECTOR-PDF]   Text length: {len(chunk_text)} chars")
                    logger.info(f"[VECTOR-PDF]   Token count: {token_count}")
                    logger.info(f"[VECTOR-PDF]   Classified as: {chunk_type}")
                    logger.info(f"[VECTOR-PDF]   Content preview: {chunk_text[:150]}...")
                    
                    # Детальна перевірка metadata
                    has_inquiry = 'Inquiry information:' in chunk_text or 'Name:' in chunk_text
                    has_response = 'Response:' in chunk_text
                    has_customer_name = bool(re.search(r'Name:\s*\w+', chunk_text))
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
                    chunk_index += 1
        
        logger.info(f"[VECTOR-PDF] Created {len(chunks)} standard chunks")
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """Розділяє текст на логічні секції"""
        
        logger.info(f"[VECTOR-PDF] 📄 SPLITTING TEXT INTO SECTIONS:")
        logger.info(f"[VECTOR-PDF] Original text length: {len(text)} chars")
        logger.info(f"[VECTOR-PDF] Text preview (first 300 chars): {text[:300]}...")
        
        # Паттерни для розділення Sample Replies
        patterns = [
            r'Example\s*#\d+',
            r'Inquiry information:',
            r'Response:',
            r'\n\n\n+',  # Множинні переноси рядків
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
        
        return filtered_sections
    
    def _split_long_text(self, text: str, max_tokens: int) -> List[str]:
        """Розділяє текст що занадто довгий на менші чанки"""
        if not self.encoding:
            # Fallback: розділення за символами
            max_chars = max_tokens * 4
            if len(text) <= max_chars:
                return [text]
            
            chunks = []
            for i in range(0, len(text), max_chars):
                chunks.append(text[i:i + max_chars])
            return chunks
        
        token_count = len(self.encoding.encode(text))
        
        if token_count <= max_tokens:
            return [text]
        
        # Розділення за реченнями
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            test_chunk = f"{current_chunk} {sentence}".strip()
            if len(self.encoding.encode(test_chunk)) <= max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """Підрахунок токенів в тексті"""
        if not self.encoding:
            return len(text) // 4  # Приблизна оцінка
        return len(self.encoding.encode(text))
    
    def _identify_chunk_type(self, text: str) -> str:
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
            
            classification_result = hybrid_classifier.classify_chunk_hybrid(text)
            
            logger.info(f"[VECTOR-PDF] 🏆 Hybrid Classification:")
            logger.info(f"[VECTOR-PDF]   - Type: {classification_result.predicted_type}")
            logger.info(f"[VECTOR-PDF]   - Confidence: {classification_result.confidence_score:.2f}")
            logger.info(f"[VECTOR-PDF]   - Method: {classification_result.method_used}")
            logger.info(f"[VECTOR-PDF]   - Rule matches: {classification_result.rule_matches}")
            
            return classification_result.predicted_type
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] ❌ Hybrid classification failed: {e}")
            logger.warning("[VECTOR-PDF] 🔄 Using basic fallback classification...")
            
            # Basic fallback (minimal rules)
            text_lower = text.lower().strip()
            
            if 'response:' in text_lower:
                return 'response'
            elif 'inquiry information:' in text_lower:
                return 'inquiry'
            elif ('inquiry information:' in text_lower and 'response:' in text_lower):
                return 'example'
            elif any(phrase in text_lower for phrase in ['good afternoon', 'thanks for reaching', "we'd be glad", 'talk soon']):
                return 'response'
            elif any(phrase in text_lower for phrase in ['name:', 'lead created:', 'ca 9', 'what kind of']):
                return 'inquiry'
            else:
                return 'general'
    
    def generate_embeddings(self, chunks: List[DocumentChunk]) -> List[Tuple[DocumentChunk, List[float]]]:
        """Генерує OpenAI ембедінги для чанків"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        logger.info(f"[VECTOR-PDF] Generating embeddings for {len(chunks)} chunks")
        
        embeddings_data = []
        batch_size = 100  # OpenAI batch limit
        
        try:
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                texts = [chunk.content for chunk in batch_chunks]
                
                logger.info(f"[VECTOR-PDF] Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
                
                # Generate embeddings using text-embedding-3-small
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts,
                    dimensions=1536  # Standard dimension for text-embedding-3-small
                )
                
                for chunk, embedding_obj in zip(batch_chunks, response.data):
                    embeddings_data.append((chunk, embedding_obj.embedding))
            
            logger.info(f"[VECTOR-PDF] Generated {len(embeddings_data)} embeddings successfully")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error generating embeddings: {e}")
            raise
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """Розраховує SHA-256 хеш вмісту файлу"""
        return hashlib.sha256(file_content).hexdigest()
    
    def process_pdf_file(
        self, 
        file_content: bytes, 
        filename: str, 
        business_id: str,
        location_id: Optional[str] = None
    ) -> Dict:
        """Головний метод для обробки PDF файлу та збереження чанків з ембедінгами"""
        
        logger.info(f"[VECTOR-PDF] ======== PROCESSING PDF FOR VECTOR STORAGE ========")
        logger.info(f"[VECTOR-PDF] File: {filename}")
        logger.info(f"[VECTOR-PDF] Business ID: {business_id}")
        logger.info(f"[VECTOR-PDF] Location ID: {location_id}")
        logger.info(f"[VECTOR-PDF] File size: {len(file_content)} bytes")
        
        try:
            # Витягування тексту з файлу
            if b'%PDF' in file_content[:100] or filename.lower().endswith('.pdf'):
                logger.info(f"[VECTOR-PDF] 📄 PDF detected: {filename}")
                
                # Використовуємо професійний PDF parser
                pdf_result = self.extract_text_from_pdf_bytes(file_content, filename)
                
                if not pdf_result['success']:
                    raise ValueError("Failed to extract text from PDF with all available parsers")
                
                all_text = pdf_result['text']
                page_count = len(pdf_result['pages'])
                
                logger.info(f"[VECTOR-PDF] 📊 PDF Extraction Results:")
                logger.info(f"[VECTOR-PDF]   Parser used: {pdf_result['parser_used']}")
                logger.info(f"[VECTOR-PDF]   Pages: {page_count}")
                logger.info(f"[VECTOR-PDF]   Text length: {len(all_text)} chars")
                logger.info(f"[VECTOR-PDF]   Structure preserved: {pdf_result['structure_preserved']}")
                
                # Додаємо інформацію про парсер у metadata
                file_hash = self.calculate_file_hash(file_content)
            else:
                # Plain text file
                all_text = file_content.decode('utf-8', errors='ignore')
                page_count = 1
                file_hash = self.calculate_file_hash(file_content)
            
            if not all_text.strip():
                raise ValueError("No text content found in file")
            
            # Створення семантичних чанків
            chunks = self.create_semantic_chunks(all_text)
            
            if not chunks:
                raise ValueError("No valid chunks created from document")
            
            # Генерація ембедінгів
            embeddings_data = self.generate_embeddings(chunks)
            
            # Збереження в базі даних
            from .vector_models import VectorDocument, VectorChunk
            
            with transaction.atomic():
                # Створення документа
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
                        'processing_info': {
                            'total_chunks': len(chunks),
                            'chunks_by_type': {
                                chunk_type: len([c for c in chunks if c.chunk_type == chunk_type])
                                for chunk_type in set(chunk.chunk_type for chunk in chunks)
                            },
                            'avg_tokens_per_chunk': sum(chunk.token_count for chunk in chunks) / len(chunks)
                        },
                        'pdf_parsing_info': {
                            'parser_used': pdf_result.get('parser_used', 'unknown'),
                            'structure_preserved': pdf_result.get('structure_preserved', False),
                            'sections_detected': pdf_result.get('sections_detected', []),
                            'pages_parsed': page_count,
                            'structure_quality_score': pdf_result.get('structure_quality_score', 0)
                        } if 'pdf_result' in locals() else {}
                    }
                )
                
                # Створення чанків з ембедінгами
                chunk_objects = []
                for chunk, embedding in embeddings_data:
                    chunk_obj = VectorChunk(
                        document=document,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        token_count=chunk.token_count,
                        embedding=embedding,  # pgvector обробить це
                        chunk_type=chunk.chunk_type,
                        metadata=chunk.metadata
                    )
                    chunk_objects.append(chunk_obj)
                
                # Bulk create chunks
                VectorChunk.objects.bulk_create(chunk_objects)
                
                logger.info(f"[VECTOR-PDF] ✅ Successfully processed PDF:")
                logger.info(f"[VECTOR-PDF] - Document ID: {document.id}")
                logger.info(f"[VECTOR-PDF] - Chunks created: {len(chunk_objects)}")
                logger.info(f"[VECTOR-PDF] - Total tokens: {sum(chunk.token_count for chunk in chunks)}")
                logger.info(f"[VECTOR-PDF] - Chunk types: {document.metadata['processing_info']['chunks_by_type']}")
            
            logger.info(f"[VECTOR-PDF] ================================================")
            
            return {
                'document_id': document.id,
                'chunks_count': len(chunk_objects),
                'total_tokens': sum(chunk.token_count for chunk in chunks),
                'pages_count': page_count,
                'chunk_types': document.metadata['processing_info']['chunks_by_type']
            }
            
        except Exception as e:
            logger.error(f"[VECTOR-PDF] Error processing PDF: {e}")
            logger.exception("PDF processing error details")
            raise
    
    def create_semantic_chunks(self, text: str, max_tokens: int = 800) -> List[DocumentChunk]:
        """🎯 Розумне створення chunks з детекцією Sample Replies структури"""
        
        logger.info(f"[VECTOR-PDF] 🧠 SMART CHUNKING: Analyzing document structure...")
        logger.info(f"[VECTOR-PDF] Text length: {len(text)} chars, max_tokens: {max_tokens}")
        
        # Детекція чи це Sample Replies документ
        is_sample_replies = self._detect_sample_replies_document(text)
        
        if is_sample_replies:
            logger.info(f"[VECTOR-PDF] 🎯 SAMPLE REPLIES DETECTED - Using specialized chunker")
            return self._create_sample_replies_chunks(text, max_tokens)
        else:
            logger.info(f"[VECTOR-PDF] 📄 REGULAR DOCUMENT - Using standard chunking")
            return self._create_standard_chunks(text, max_tokens)
    
    def _detect_sample_replies_document(self, text: str) -> bool:
        """Детектує чи це документ Sample Replies"""
        
        text_lower = text.lower()
        
        # Ключові індикатори Sample Replies
        indicators = [
            'inquiry information:' in text_lower,
            'response:' in text_lower,
            'example #' in text_lower or 'example#' in text_lower,
            bool(re.search(r'name:\s*[a-z]+ [a-z]\.?', text_lower)),  # Name: John D. - перетворюємо в boolean
            'talk soon' in text_lower
        ]
        
        detected_count = sum(indicators)
        is_sample_replies = detected_count >= 2  # Мінімум 2 індикатори
        
        logger.info(f"[VECTOR-PDF] 🔍 Sample Replies detection:")
        logger.info(f"[VECTOR-PDF]   Indicators found: {detected_count}/5")
        logger.info(f"[VECTOR-PDF]   Is Sample Replies: {is_sample_replies}")
        
        return is_sample_replies
    
    def _create_sample_replies_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """🔄 Fallback: використовує стандартний chunking для Sample Replies"""
        
        logger.warning("[VECTOR-PDF] ⚠️ Specialized chunker not available - using enhanced standard method")
        return self._create_standard_chunks(text, max_tokens)

    def _create_standard_chunks(self, text: str, max_tokens: int) -> List[DocumentChunk]:
        """Стандартне створення chunks (original method)"""
        
        logger.info(f"[VECTOR-PDF] 📄 Using standard chunking method")
        
        chunks = []
        chunk_index = 0
        
        # Розділення на секції/приклади спочатку
        sections = self._split_by_sections(text)
        
        for section in sections:
            if not section.strip():
                continue
            
            # Додаткове розділення якщо секція занадто довга
            section_chunks = self._split_long_text(section, max_tokens)
            
            for chunk_text in section_chunks:
                token_count = self._count_tokens(chunk_text)
                
                if token_count > 0:
                    chunk_type = self._identify_chunk_type(chunk_text)
                    
                    logger.info(f"[VECTOR-PDF] 🧩 CREATING CHUNK #{chunk_index}:")
                    logger.info(f"[VECTOR-PDF]   Text length: {len(chunk_text)} chars")
                    logger.info(f"[VECTOR-PDF]   Token count: {token_count}")
                    logger.info(f"[VECTOR-PDF]   Classified as: {chunk_type}")
                    logger.info(f"[VECTOR-PDF]   Content preview: {chunk_text[:150]}...")
                    
                    # Детальна перевірка metadata
                    has_inquiry = 'Inquiry information:' in chunk_text or 'Name:' in chunk_text
                    has_response = 'Response:' in chunk_text
                    has_customer_name = bool(re.search(r'Name:\s*\w+', chunk_text))
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
                    chunk_index += 1
        
        logger.info(f"[VECTOR-PDF] Created {len(chunks)} standard chunks")
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """Розділяє текст на логічні секції"""
        
        logger.info(f"[VECTOR-PDF] 📄 SPLITTING TEXT INTO SECTIONS:")
        logger.info(f"[VECTOR-PDF] Original text length: {len(text)} chars")
        logger.info(f"[VECTOR-PDF] Text preview (first 300 chars): {text[:300]}...")
        
        # Паттерни для розділення Sample Replies
        patterns = [
            r'Example\s*#\d+',
            r'Inquiry information:',
            r'Response:',
            r'\n\n\n+',  # Множинні переноси рядків
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
        
        return filtered_sections
    
    def _split_long_text(self, text: str, max_tokens: int) -> List[str]:
        """Розділяє текст що занадто довгий на менші чанки"""
        if not self.encoding:
            # Fallback: розділення за символами
            max_chars = max_tokens * 4
            if len(text) <= max_chars:
                return [text]
            
            chunks = []
            for i in range(0, len(text), max_chars):
                chunks.append(text[i:i + max_chars])
            return chunks
        
        token_count = len(self.encoding.encode(text))
        
        if token_count <= max_tokens:
            return [text]
        
        # Розділення за реченнями
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            test_chunk = f"{current_chunk} {sentence}".strip()
            if len(self.encoding.encode(test_chunk)) <= max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """Підрахунок токенів в тексті"""
        if not self.encoding:
            return len(text) // 4  # Приблизна оцінка
        return len(self.encoding.encode(text))
    
    def _identify_chunk_type(self, text: str) -> str:
        """Визначає тип контенту секції"""
        text_lower = text.lower()
        
        if 'inquiry information:' in text_lower:
            return 'inquiry'
        elif 'response:' in text_lower:
            return 'response'  
        elif ('inquiry information:' in text_lower and 'response:' in text_lower):
            return 'example'
        else:
            return 'general'
    
    def format_sample_replies(self, raw_content: str) -> str:
        """Форматування sample replies для AI використання"""
        
        # Перевірка на коди помилок
        if raw_content in ["PDF_BINARY_DETECTED", "PROCESSING_ERROR", "EMPTY_FILE", "ENCODING_ERROR", "PDF_BINARY_DETECTED_NO_PARSER"]:
            return raw_content
        
        if not raw_content or not raw_content.strip():
            return "EMPTY_CONTENT"
        
        # Базове очищення тексту
        cleaned = raw_content.strip()
        
        # Видаляємо зайві пробіли та переноси рядків
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)  # Замінюємо 3+ переноси на 2
        cleaned = re.sub(r' +', ' ', cleaned)  # Замінюємо багато пробілів на один
        cleaned = re.sub(r'\t+', ' ', cleaned)  # Замінюємо табуляції на пробіл
        
        # Видаляємо зайві пробіли на початку рядків
        lines = cleaned.split('\n')
        lines = [line.strip() for line in lines]
        cleaned = '\n'.join(lines)
        
        # Видаляємо порожні рядки на початку та в кінці
        cleaned = cleaned.strip()
        
        logger.info(f"[VECTOR-PDF] 🔧 Formatted sample replies:")
        logger.info(f"[VECTOR-PDF] - Original length: {len(raw_content)} chars")
        logger.info(f"[VECTOR-PDF] - Cleaned length: {len(cleaned)} chars")
        logger.info(f"[VECTOR-PDF] - Preview: {cleaned[:200]}...")
        
        return cleaned
    
    def validate_sample_replies_content(self, content: str) -> tuple[bool, Optional[str]]:
        """Валідує чи контент підходить для Sample Replies"""
        
        if not content or not content.strip():
            return False, "Контент порожній"
        
        if len(content.strip()) < 50:
            return False, "Контент занадто короткий (мінімум 50 символів)"
        
        if len(content) > 100000:  # Збільшили ліміт для векторного рішення
            return False, "Контент занадто довгий (максимум 100,000 символів)"
        
        # Перевірка чи є хоча б деякі ключові слова для Sample Replies
        content_lower = content.lower()
        keywords = [
            'inquiry', 'response', 'customer', 'hello', 'thank you', 
            'service', 'business', 'contact', 'help', 'question',
            'запит', 'відповідь', 'клієнт', 'дякую', 'послуга'
        ]
        
        has_keywords = any(keyword in content_lower for keyword in keywords)
        
        if not has_keywords:
            return False, "Контент не схожий на Sample Replies (немає ключових слів)"
        
        logger.info(f"[VECTOR-PDF] ✅ Content validation passed")
        return True, None

# Глобальний інстанс векторного сервісу
vector_pdf_service = VectorPDFService()

# Legacy інстанс для backward compatibility
simple_pdf_service = vector_pdf_service
