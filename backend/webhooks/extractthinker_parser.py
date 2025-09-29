"""
🎯 ExtractThinker-Based Sample Replies Parser
Professional structured data extraction using AI + Pydantic contracts
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# ExtractThinker imports with fallback
try:
    from extract_thinker import Extractor, ClassificationStrategy, ExtractionStrategy
    from extract_thinker.splitter import MarkdownSplitter
    EXTRACTTHINKER_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("[EXTRACTTHINKER] ✅ ExtractThinker library available")
except ImportError as e:
    EXTRACTTHINKER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"[EXTRACTTHINKER] ⚠️ ExtractThinker not available: {e}")

from .extraction_contracts import CustomerInquiry, BusinessResponse, SampleReplyExample, SampleRepliesDocument

logger = logging.getLogger(__name__)


class SampleRepliesSplitter:
    """🔍 Custom Splitter для Sample Replies документів"""
    
    @staticmethod
    def split_by_markers(text: str) -> List[Dict[str, str]]:
        """Розділяє документ за маркерами Inquiry/Response"""
        
        logger.info(f"[EXTRACTTHINKER-SPLITTER] 📄 Splitting document by markers")
        logger.info(f"[EXTRACTTHINKER-SPLITTER] Document length: {len(text)} chars")
        
        # Patterns для розділення
        patterns = {
            'example': r'Example\s*#?\s*(\d+)',
            'inquiry': r'Inquiry\s+information:',
            'response': r'Response:'
        }
        
        # Знаходимо всі маркери з позиціями
        markers = []
        
        for marker_type, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                markers.append({
                    'type': marker_type,
                    'position': match.start(),
                    'text': match.group(),
                    'number': int(match.group(1)) if marker_type == 'example' and match.groups() else None
                })
        
        # Сортуємо за позицією
        markers.sort(key=lambda x: x['position'])
        
        logger.info(f"[EXTRACTTHINKER-SPLITTER] Found {len(markers)} markers:")
        for marker in markers:
            logger.info(f"[EXTRACTTHINKER-SPLITTER]   {marker['type']}: pos {marker['position']} - '{marker['text']}'")
        
        # Розділяємо на sections
        sections = []
        
        for i, marker in enumerate(markers):
            start_pos = marker['position']
            
            # Кінець секції = початок наступного маркера або кінець тексту
            if i + 1 < len(markers):
                end_pos = markers[i + 1]['position']
            else:
                end_pos = len(text)
            
            section_text = text[start_pos:end_pos].strip()
            
            if len(section_text) > 20:  # Фільтруємо дуже короткі секції
                sections.append({
                    'type': marker['type'],
                    'content': section_text,
                    'example_number': marker.get('number'),
                    'start_position': start_pos,
                    'end_position': end_pos
                })
                
                logger.info(f"[EXTRACTTHINKER-SPLITTER] Section {len(sections)}: {marker['type']} ({len(section_text)} chars)")
        
        logger.info(f"[EXTRACTTHINKER-SPLITTER] ✅ Created {len(sections)} sections")
        return sections


class ExtractThinkerParser:
    """🧠 AI-Powered Sample Replies Parser using ExtractThinker"""
    
    def __init__(self):
        self.extractor = None
        self.is_available = EXTRACTTHINKER_AVAILABLE
        self._init_extractor()
    
    def _init_extractor(self):
        """Ініціалізація ExtractThinker з OpenAI"""
        
        if not self.is_available:
            logger.warning("[EXTRACTTHINKER] ⚠️ ExtractThinker not available - using fallback parsing")
            return
        
        try:
            # Отримуємо OpenAI API key
            import os
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                # Fallback to Django settings
                from .models import AISettings
                ai_settings = AISettings.objects.first()
                if ai_settings and ai_settings.openai_api_key:
                    openai_api_key = ai_settings.openai_api_key
            
            if not openai_api_key:
                raise ValueError("No OpenAI API key found")
            
            # Ініціалізуємо ExtractThinker
            self.extractor = Extractor(
                api_key=openai_api_key,
                model_name="gpt-4o-mini",  # Економна модель для extraction
                classification_strategy=ClassificationStrategy.ZERO_SHOT,
                extraction_strategy=ExtractionStrategy.LLM
            )
            
            logger.info("[EXTRACTTHINKER] ✅ ExtractThinker initialized successfully")
            
        except Exception as e:
            logger.error(f"[EXTRACTTHINKER] ❌ Failed to initialize: {e}")
            self.extractor = None
            self.is_available = False
    
    def parse_sample_replies_document(self, text: str) -> Optional[SampleRepliesDocument]:
        """
        🎯 Головний метод парсингу Sample Replies документа
        
        1. Розділяє документ за маркерами
        2. Витягує структуровані дані з кожної секції
        3. Повертає повністю структурований документ
        """
        
        logger.info(f"[EXTRACTTHINKER] 🚀 PARSING SAMPLE REPLIES DOCUMENT")
        logger.info(f"[EXTRACTTHINKER] Document length: {len(text)} chars")
        
        if not self.is_available:
            logger.warning("[EXTRACTTHINKER] ⚠️ ExtractThinker not available, using fallback")
            return self._fallback_parsing(text)
        
        try:
            # 1. Розділяємо документ на секції
            sections = SampleRepliesSplitter.split_by_markers(text)
            
            if not sections:
                logger.warning("[EXTRACTTHINKER] ⚠️ No sections found, using fallback")
                return self._fallback_parsing(text)
            
            # 2. Групуємо секції в приклади (inquiry + response пари)
            examples = self._group_sections_into_examples(sections)
            
            # 3. Витягуємо structured data для кожного прикладу
            structured_examples = []
            
            for example_data in examples:
                try:
                    structured_example = self._extract_example_data(example_data)
                    if structured_example:
                        structured_examples.append(structured_example)
                        
                except Exception as e:
                    logger.warning(f"[EXTRACTTHINKER] ⚠️ Failed to extract example {example_data.get('example_number', '?')}: {e}")
            
            # 4. Створюємо повний документ
            document = SampleRepliesDocument(
                document_title=self._extract_document_title(text),
                business_name=self._extract_business_name(text),
                examples=structured_examples,
                total_examples=len(structured_examples),
                extraction_quality=self._assess_extraction_quality(structured_examples),
                raw_document_text=text
            )
            
            logger.info(f"[EXTRACTTHINKER] ✅ EXTRACTION SUCCESS:")
            logger.info(f"[EXTRACTTHINKER]   Examples found: {len(structured_examples)}")
            logger.info(f"[EXTRACTTHINKER]   Quality: {document.extraction_quality}")
            logger.info(f"[EXTRACTTHINKER]   Business: {document.business_name}")
            
            return document
            
        except Exception as e:
            logger.error(f"[EXTRACTTHINKER] ❌ Extraction failed: {e}")
            return self._fallback_parsing(text)
    
    def _group_sections_into_examples(self, sections: List[Dict]) -> List[Dict]:
        """Групує inquiry та response секції в приклади"""
        
        logger.info(f"[EXTRACTTHINKER] 🔗 Grouping {len(sections)} sections into examples")
        
        examples = []
        current_example = {}
        current_example_number = None
        
        for section in sections:
            section_type = section['type']
            
            if section_type == 'example':
                # Новий приклад почався
                if current_example:
                    examples.append(current_example)
                
                current_example = {
                    'example_number': section.get('example_number'),
                    'sections': []
                }
                current_example_number = section.get('example_number')
                
            # Додаємо секцію до поточного прикладу
            current_example.setdefault('sections', []).append(section)
        
        # Додаємо останній приклад
        if current_example:
            examples.append(current_example)
        
        logger.info(f"[EXTRACTTHINKER] ✅ Grouped into {len(examples)} examples")
        
        for i, example in enumerate(examples):
            section_types = [s['type'] for s in example['sections']]
            logger.info(f"[EXTRACTTHINKER]   Example {example.get('example_number', i+1)}: {section_types}")
        
        return examples
    
    def _extract_example_data(self, example_data: Dict) -> Optional[SampleReplyExample]:
        """Витягує структуровані дані з одного прикладу"""
        
        example_num = example_data.get('example_number', 0)
        sections = example_data.get('sections', [])
        
        logger.info(f"[EXTRACTTHINKER] 🔍 Extracting data from example {example_num}")
        
        # Знаходимо inquiry та response секції
        inquiry_section = None
        response_section = None
        
        for section in sections:
            if section['type'] == 'inquiry':
                inquiry_section = section
            elif section['type'] == 'response':
                response_section = section
        
        if not inquiry_section or not response_section:
            logger.warning(f"[EXTRACTTHINKER] ⚠️ Example {example_num}: Missing inquiry or response section")
            return None
        
        # Витягуємо structured data за допомогою ExtractThinker
        try:
            # Extract Inquiry
            inquiry_text = inquiry_section['content']
            logger.info(f"[EXTRACTTHINKER] 🔍 Extracting inquiry from: {inquiry_text[:100]}...")
            
            inquiry_result = self.extractor.extract(
                text=inquiry_text,
                schema=CustomerInquiry,
                classification_strategy=ClassificationStrategy.ZERO_SHOT
            )
            
            if not inquiry_result or not inquiry_result.data:
                logger.warning(f"[EXTRACTTHINKER] ⚠️ Failed to extract inquiry data")
                return None
            
            # Extract Response
            response_text = response_section['content']
            logger.info(f"[EXTRACTTHINKER] 🔍 Extracting response from: {response_text[:100]}...")
            
            response_result = self.extractor.extract(
                text=response_text,
                schema=BusinessResponse,
                classification_strategy=ClassificationStrategy.ZERO_SHOT
            )
            
            if not response_result or not response_result.data:
                logger.warning(f"[EXTRACTTHINKER] ⚠️ Failed to extract response data")
                return None
            
            # Створюємо structured example
            structured_example = SampleReplyExample(
                example_number=example_num,
                inquiry=inquiry_result.data,
                response=response_result.data,
                context_match_score=self._calculate_context_match(inquiry_result.data, response_result.data)
            )
            
            logger.info(f"[EXTRACTTHINKER] ✅ Example {example_num} extracted successfully")
            logger.info(f"[EXTRACTTHINKER]   Customer: {inquiry_result.data.customer_name}")
            logger.info(f"[EXTRACTTHINKER]   Service: {inquiry_result.data.service_type}")
            logger.info(f"[EXTRACTTHINKER]   Response tone: {response_result.data.tone}")
            
            return structured_example
            
        except Exception as e:
            logger.error(f"[EXTRACTTHINKER] ❌ Failed to extract example {example_num}: {e}")
            return None
    
    def _calculate_context_match(self, inquiry: CustomerInquiry, response: BusinessResponse) -> float:
        """Розраховує наскільки inquiry та response підходять один одному"""
        
        match_score = 0.0
        
        # Перевірка чи ім'я клієнта згадується в response
        if inquiry.customer_name and response.customer_name_mentioned:
            if inquiry.customer_name.lower() in response.customer_name_mentioned.lower():
                match_score += 0.3
        
        # Перевірка чи service type згадується в response
        if inquiry.service_type and response.service_acknowledgment:
            service_words = inquiry.service_type.lower().split()
            acknowledgment_lower = response.service_acknowledgment.lower()
            if any(word in acknowledgment_lower for word in service_words):
                match_score += 0.3
        
        # Перевірка на професійність response
        if response.greeting_type and response.closing_phrase:
            match_score += 0.2
        
        # Перевірка на питання в response (engagement)
        if response.questions_asked and len(response.questions_asked) > 0:
            match_score += 0.2
        
        return min(match_score, 1.0)  # Cap at 1.0
    
    def _extract_document_title(self, text: str) -> Optional[str]:
        """Витягує назву документа"""
        
        lines = text.split('\n')[:5]  # Перші 5 рядків
        
        for line in lines:
            line = line.strip()
            if len(line) > 10 and 'sample replies' in line.lower():
                return line
        
        return None
    
    def _extract_business_name(self, text: str) -> Optional[str]:
        """Витягує назву бізнесу"""
        
        # Шукаємо в назві документа
        title_match = re.search(r'Sample Replies\s*[–-]\s*(.+)', text, re.IGNORECASE)
        if title_match:
            business_name = title_match.group(1).strip()
            # Видаляємо "Roofing" якщо в кінці
            business_name = re.sub(r'\s*Roofing\s*$', '', business_name, re.IGNORECASE)
            return business_name
        
        return None
    
    def _assess_extraction_quality(self, examples: List[SampleReplyExample]) -> str:
        """Оцінює якість extraction"""
        
        if not examples:
            return "poor"
        
        # Рахуємо скільки examples мають повні дані
        complete_examples = 0
        
        for example in examples:
            inquiry = example.inquiry
            response = example.response
            
            # Перевірка повноти inquiry
            inquiry_complete = bool(
                inquiry.customer_name and 
                inquiry.service_type and 
                inquiry.location
            )
            
            # Перевірка повноти response
            response_complete = bool(
                response.greeting_type and 
                response.acknowledgment_phrase and 
                response.closing_phrase
            )
            
            if inquiry_complete and response_complete:
                complete_examples += 1
        
        completion_rate = complete_examples / len(examples)
        
        if completion_rate >= 0.8:
            return "excellent"
        elif completion_rate >= 0.6:
            return "good"
        elif completion_rate >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _fallback_parsing(self, text: str) -> SampleRepliesDocument:
        """Fallback parsing без ExtractThinker"""
        
        logger.warning("[EXTRACTTHINKER] 🔄 Using fallback parsing (no AI extraction)")
        
        # Простий regex-based fallback
        sections = SampleRepliesSplitter.split_by_markers(text)
        
        examples = []
        current_inquiry = None
        current_response = None
        
        for section in sections:
            if section['type'] == 'inquiry':
                current_inquiry = section['content']
            elif section['type'] == 'response' and current_inquiry:
                current_response = section['content']
                
                # Створюємо простий приклад без AI extraction
                simple_example = SampleReplyExample(
                    example_number=section.get('example_number', len(examples) + 1),
                    inquiry=CustomerInquiry(
                        raw_text=current_inquiry,
                        customer_name=self._simple_extract_name(current_inquiry),
                        service_type=self._simple_extract_service(current_inquiry)
                    ),
                    response=BusinessResponse(
                        raw_text=current_response,
                        greeting_type=self._simple_extract_greeting(current_response),
                        tone=self._simple_extract_tone(current_response)
                    )
                )
                
                examples.append(simple_example)
                current_inquiry = None
                current_response = None
        
        return SampleRepliesDocument(
            document_title=self._extract_document_title(text),
            business_name=self._extract_business_name(text),
            examples=examples,
            total_examples=len(examples),
            extraction_quality="fair",  # Fallback завжди "fair"
            raw_document_text=text
        )
    
    def _simple_extract_name(self, text: str) -> Optional[str]:
        """Простий regex для витягування імені"""
        match = re.search(r'Name:\s*([A-Z][a-z]+\s*[A-Z]?\.?)', text)
        return match.group(1).strip() if match else None
    
    def _simple_extract_service(self, text: str) -> Optional[str]:
        """Простий regex для витягування типу послуги"""
        lines = text.split('\n')
        for line in lines[1:3]:  # 2-3 рядки після Name
            line = line.strip()
            if line and not line.startswith(('Lead created:', 'What kind of')):
                return line
        return None
    
    def _simple_extract_greeting(self, text: str) -> Optional[str]:
        """Простий regex для витягування типу привітання"""
        text_lower = text.lower()
        if 'good afternoon' in text_lower:
            return 'Good afternoon'
        elif 'good morning' in text_lower:
            return 'Good morning' 
        elif 'hello' in text_lower:
            return 'Hello'
        return None
    
    def _simple_extract_tone(self, text: str) -> str:
        """Простий аналіз тону"""
        text_lower = text.lower()
        
        if any(casual in text_lower for casual in ['thanks so much', "we'd be glad", 'talk soon']):
            return 'friendly'
        elif any(formal in text_lower for formal in ['we appreciate', 'thank you for your inquiry']):
            return 'formal'
        else:
            return 'professional'


# Глобальна instance
extractthinker_parser = ExtractThinkerParser()
