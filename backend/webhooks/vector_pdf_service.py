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
        """🔄 Simplified: Uses standard chunking with enhanced classification"""
        
        logger.info("[VECTOR-PDF] 🔄 Using simplified Sample Replies processing")
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
            r'\n\n