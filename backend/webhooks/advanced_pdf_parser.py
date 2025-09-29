"""
🚀 Professional PDF Parser with Multiple Fallback Methods
Підтримує pdfplumber, pdfminer, PyMuPDF з інтелектуальним вибором
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from io import BytesIO
import hashlib

logger = logging.getLogger(__name__)

# Спроба імпорту різних PDF парсерів
PDF_PARSERS_AVAILABLE = {}

try:
    import pdfplumber
    PDF_PARSERS_AVAILABLE['pdfplumber'] = True
    logger.info("[ADVANCED-PDF] ✅ pdfplumber available (PREFERRED)")
except ImportError:
    PDF_PARSERS_AVAILABLE['pdfplumber'] = False
    logger.warning("[ADVANCED-PDF] ⚠️ pdfplumber not available")

try:
    import pdfminer
    from pdfminer.high_level import extract_text, extract_text_to_fp
    from pdfminer.layout import LAParams
    PDF_PARSERS_AVAILABLE['pdfminer'] = True
    logger.info("[ADVANCED-PDF] ✅ pdfminer available")
except ImportError:
    PDF_PARSERS_AVAILABLE['pdfminer'] = False
    logger.warning("[ADVANCED-PDF] ⚠️ pdfminer not available")

try:
    import fitz  # PyMuPDF
    PDF_PARSERS_AVAILABLE['pymupdf'] = True
    logger.info("[ADVANCED-PDF] ✅ PyMuPDF available (FALLBACK)")
except ImportError:
    PDF_PARSERS_AVAILABLE['pymupdf'] = False
    logger.warning("[ADVANCED-PDF] ⚠️ PyMuPDF not available")


class AdvancedPDFParser:
    """🎯 Professional PDF Parser з інтелектуальним розпізнаванням структури"""
    
    def __init__(self):
        self.parsers_tried = []
        self.successful_parser = None
        
    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict:
        """
        Головний метод парсингу PDF з байтів
        Спробує різні парсери в порядку пріоритету
        """
        
        logger.info(f"[ADVANCED-PDF] 🚀 Starting advanced PDF parsing: {filename}")
        logger.info(f"[ADVANCED-PDF] PDF size: {len(pdf_bytes)} bytes")
        logger.info(f"[ADVANCED-PDF] Available parsers: {[k for k, v in PDF_PARSERS_AVAILABLE.items() if v]}")
        
        result = {
            'success': False,
            'text': '',
            'pages': [],
            'parser_used': None,
            'structure_preserved': False,
            'sections_detected': [],
            'errors': []
        }
        
        # Спробуємо парсери в порядку якості
        parsers_to_try = [
            ('pdfplumber', self._parse_with_pdfplumber),
            ('pdfminer', self._parse_with_pdfminer), 
            ('pymupdf', self._parse_with_pymupdf)
        ]
        
        for parser_name, parser_method in parsers_to_try:
            if not PDF_PARSERS_AVAILABLE.get(parser_name, False):
                continue
                
            logger.info(f"[ADVANCED-PDF] 🔄 Trying parser: {parser_name}")
            self.parsers_tried.append(parser_name)
            
            try:
                parser_result = parser_method(pdf_bytes, filename)
                
                if parser_result['success'] and parser_result['text'].strip():
                    result.update(parser_result)
                    result['parser_used'] = parser_name
                    self.successful_parser = parser_name
                    
                    logger.info(f"[ADVANCED-PDF] ✅ SUCCESS with {parser_name}")
                    logger.info(f"[ADVANCED-PDF] Extracted text length: {len(result['text'])} chars")
                    logger.info(f"[ADVANCED-PDF] Structure preserved: {result['structure_preserved']}")
                    
                    # Аналіз структури для Sample Replies
                    self._analyze_sample_replies_structure(result)
                    
                    return result
                    
            except Exception as e:
                error_msg = f"{parser_name} failed: {str(e)}"
                result['errors'].append(error_msg)
                logger.warning(f"[ADVANCED-PDF] ⚠️ {error_msg}")
                
        # Якщо всі парсери провалилися
        logger.error(f"[ADVANCED-PDF] ❌ ALL PARSERS FAILED for {filename}")
        result['errors'].append("All PDF parsers failed")
        return result
    
    def _parse_with_pdfplumber(self, pdf_bytes: bytes, filename: str) -> Dict:
        """🏆 НАЙКРАЩИЙ: pdfplumber - зберігає структуру та форматування"""
        
        logger.info("[ADVANCED-PDF] 📖 Using pdfplumber (structure-preserving)")
        
        result = {
            'success': False,
            'text': '',
            'pages': [],
            'structure_preserved': True,
            'sections_detected': []
        }
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            all_text_parts = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                # pdfplumber зберігає табуляцію та відступи
                page_text = page.extract_text(
                    x_tolerance=3,  # Краща обробка колонок
                    y_tolerance=3,  # Краща обробка рядків  
                    layout=True,    # Зберігає макет
                    x_density=7.25, # Висока точність
                    y_density=13    # Висока точність
                )
                
                if page_text:
                    # Зберігаємо оригінальне форматування
                    all_text_parts.append(page_text)
                    
                    result['pages'].append({
                        'page_number': page_num,
                        'text': page_text,
                        'char_count': len(page_text),
                        'has_tables': len(page.find_tables()) > 0,
                        'bbox': page.bbox
                    })
                    
                    logger.info(f"[ADVANCED-PDF] Page {page_num}: {len(page_text)} chars, tables: {len(page.find_tables())}")
            
            # Об'єднуємо сторінки з збереженням структури
            result['text'] = "\n\n".join(all_text_parts)
            result['success'] = len(result['text'].strip()) > 0
            
            logger.info(f"[ADVANCED-PDF] pdfplumber extracted: {len(result['text'])} chars from {len(result['pages'])} pages")
            
        return result
    
    def _parse_with_pdfminer(self, pdf_bytes: bytes, filename: str) -> Dict:
        """📚 ХОРОШИЙ: pdfminer - точний парсинг з layout analysis"""
        
        logger.info("[ADVANCED-PDF] 📚 Using pdfminer (layout-aware)")
        
        result = {
            'success': False,
            'text': '',
            'pages': [],
            'structure_preserved': True,
            'sections_detected': []
        }
        
        # Налаштування для кращого збереження структури
        laparams = LAParams(
            line_margin=0.5,      # Відстань між рядками
            word_margin=0.1,      # Відстань між словами  
            char_margin=2.0,      # Відстань між символами
            boxes_flow=0.5,       # Порядок читання блоків
            detect_vertical=True  # Вертикальний текст
        )
        
        try:
            text = extract_text(
                BytesIO(pdf_bytes),
                laparams=laparams,
                output_type='text',
                codec='utf-8'
            )
            
            result['text'] = text
            result['success'] = len(text.strip()) > 0
            
            # pdfminer не дає інформацію про сторінки в цьому режимі
            result['pages'] = [{'page_number': 1, 'text': text, 'char_count': len(text)}]
            
            logger.info(f"[ADVANCED-PDF] pdfminer extracted: {len(text)} chars")
            
        except Exception as e:
            logger.error(f"[ADVANCED-PDF] pdfminer error: {e}")
            result['success'] = False
            
        return result
    
    def _parse_with_pymupdf(self, pdf_bytes: bytes, filename: str) -> Dict:
        """⚡ ШВИДКИЙ: PyMuPDF - швидкий але менш точний"""
        
        logger.info("[ADVANCED-PDF] ⚡ Using PyMuPDF (fast fallback)")
        
        result = {
            'success': False,
            'text': '',
            'pages': [],
            'structure_preserved': False,  # PyMuPDF гірше зберігає структуру
            'sections_detected': []
        }
        
        doc = fitz.open("pdf", pdf_bytes)
        all_text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            if page_text.strip():
                all_text_parts.append(page_text)
                
                result['pages'].append({
                    'page_number': page_num + 1,
                    'text': page_text,
                    'char_count': len(page_text)
                })
        
        doc.close()
        
        result['text'] = "\n\n".join(all_text_parts)
        result['success'] = len(result['text'].strip()) > 0
        
        logger.info(f"[ADVANCED-PDF] PyMuPDF extracted: {len(result['text'])} chars from {len(result['pages'])} pages")
        
        return result
    
    def _analyze_sample_replies_structure(self, result: Dict):
        """🔍 Аналіз структури Sample Replies документа"""
        
        text = result['text']
        logger.info(f"[ADVANCED-PDF] 🔍 Analyzing Sample Replies structure...")
        
        # Пошук ключових секцій
        sections_found = []
        
        # Example markers
        example_pattern = r'Example\s*#?\s*\d+'
        examples = re.findall(example_pattern, text, re.IGNORECASE)
        if examples:
            sections_found.append(f"Found {len(examples)} examples: {examples}")
            
        # Inquiry sections  
        inquiry_pattern = r'Inquiry information:'
        inquiries = re.findall(inquiry_pattern, text, re.IGNORECASE)
        if inquiries:
            sections_found.append(f"Found {len(inquiries)} inquiry sections")
            
        # Response sections
        response_pattern = r'Response:'
        responses = re.findall(response_pattern, text, re.IGNORECASE) 
        if responses:
            sections_found.append(f"Found {len(responses)} response sections")
            
        # Customer names
        name_pattern = r'Name:\s*([A-Z][a-z]+\s*[A-Z]?\.?)'
        names = re.findall(name_pattern, text)
        if names:
            sections_found.append(f"Found customer names: {names}")
            
        # Business responses (Norma signatures)
        norma_pattern = r'Talk soon,\s*Norma'
        norma_responses = re.findall(norma_pattern, text, re.IGNORECASE)
        if norma_responses:
            sections_found.append(f"Found {len(norma_responses)} Norma signatures")
        
        result['sections_detected'] = sections_found
        
        # Логування структурного аналізу
        logger.info(f"[ADVANCED-PDF] 📋 Structure Analysis Results:")
        for section in sections_found:
            logger.info(f"[ADVANCED-PDF]   ✅ {section}")
            
        if not sections_found:
            logger.warning(f"[ADVANCED-PDF] ⚠️ No Sample Replies structure detected!")
            logger.info(f"[ADVANCED-PDF] Text preview: {text[:500]}...")
        
        # Оцінка якості парсингу
        structure_score = len(sections_found)
        result['structure_quality_score'] = structure_score
        
        if structure_score >= 3:
            logger.info(f"[ADVANCED-PDF] ✅ EXCELLENT structure preservation (score: {structure_score})")
        elif structure_score >= 1:  
            logger.info(f"[ADVANCED-PDF] ⚠️ PARTIAL structure preservation (score: {structure_score})")
        else:
            logger.warning(f"[ADVANCED-PDF] ❌ POOR structure preservation (score: {structure_score})")
        
        return result


# Глобальна instance
advanced_pdf_parser = AdvancedPDFParser()
