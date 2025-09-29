"""
🎯 Specialized Chunker for Sample Replies Documents
Розумний розподіл Sample Replies на inquiry/response пари
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SampleReplySection:
    """Структура одного прикладу Sample Reply"""
    example_number: Optional[int]
    inquiry_text: str
    response_text: str
    customer_name: Optional[str]
    service_type: Optional[str]
    location: Optional[str]
    raw_inquiry: str
    raw_response: str

class SampleRepliesChunker:
    """🎯 Спеціалізований chunker для Sample Replies документів"""
    
    def __init__(self):
        self.examples_found = []
        self.parsing_errors = []
    
    def parse_sample_replies_document(self, text: str) -> List[SampleReplySection]:
        """
        Парсить Sample Replies документ на структуровані приклади
        
        Очікувана структура:
        Example #1
        Inquiry information:
        Name: John D.
        Service details...
        Response:
        Business response...
        """
        
        logger.info(f"[SAMPLE-CHUNKER] 🎯 Parsing Sample Replies document")
        logger.info(f"[SAMPLE-CHUNKER] Document length: {len(text)} chars")
        
        # Очистка тексту
        text = self._clean_text(text)
        
        # Розділення на приклади
        examples = self._split_into_examples(text)
        
        logger.info(f"[SAMPLE-CHUNKER] 📋 Found {len(examples)} potential examples")
        
        # Парсинг кожного прикладу
        parsed_sections = []
        for i, example_text in enumerate(examples, 1):
            try:
                section = self._parse_single_example(example_text, i)
                if section:
                    parsed_sections.append(section)
                    logger.info(f"[SAMPLE-CHUNKER] ✅ Example {i}: {section.customer_name or 'Unknown'} - {section.service_type or 'Unknown service'}")
                    
            except Exception as e:
                error_msg = f"Example {i} parsing failed: {str(e)}"
                self.parsing_errors.append(error_msg)
                logger.warning(f"[SAMPLE-CHUNKER] ⚠️ {error_msg}")
        
        logger.info(f"[SAMPLE-CHUNKER] 🎉 Successfully parsed {len(parsed_sections)} examples")
        if self.parsing_errors:
            logger.warning(f"[SAMPLE-CHUNKER] ⚠️ {len(self.parsing_errors)} parsing errors occurred")
        
        return parsed_sections
    
    def _clean_text(self, text: str) -> str:
        """Очищає текст від зайвих символів"""
        
        # Видаляємо зайві пробіли та нормалізуємо переноси рядків
        text = re.sub(r'\\n+', '\\n', text)
        text = re.sub(r'[ \\t]+', ' ', text)
        text = text.strip()
        
        logger.info(f"[SAMPLE-CHUNKER] 🧹 Text cleaned: {len(text)} chars")
        return text
    
    def _split_into_examples(self, text: str) -> List[str]:
        """Розділяє документ на окремі приклади"""
        
        # Шукаємо маркери Example #1, Example #2, etc.
        example_pattern = r'Example\\s*#?\\s*(\\d+)'
        
        # Знайдемо всі маркери
        matches = list(re.finditer(example_pattern, text, re.IGNORECASE))
        
        if not matches:
            logger.warning("[SAMPLE-CHUNKER] ⚠️ No 'Example #' markers found, trying alternative splitting")
            return self._alternative_splitting(text)
        
        logger.info(f"[SAMPLE-CHUNKER] 📝 Found {len(matches)} example markers")
        
        examples = []
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            
            # Кінець цього прикладу = початок наступного або кінець тексту
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            example_text = text[start_pos:end_pos].strip()
            
            if len(example_text) > 50:  # Мінімальна довжина для валідного прикладу
                examples.append(example_text)
                logger.info(f"[SAMPLE-CHUNKER] 📄 Example {match.group(1)}: {len(example_text)} chars")
        
        return examples
    
    def _alternative_splitting(self, text: str) -> List[str]:
        """Альтернативне розділення якщо немає Example # маркерів"""
        
        # Спробуємо розділити по "Inquiry information:" блоках
        inquiry_pattern = r'Inquiry\\s+information:'
        
        parts = re.split(inquiry_pattern, text, flags=re.IGNORECASE)
        
        examples = []
        for i, part in enumerate(parts[1:], 1):  # Пропускаємо першу частину (header)
            if len(part.strip()) > 100:
                # Додаємо назад маркер
                full_example = f"Inquiry information:{part}"
                examples.append(full_example)
                logger.info(f"[SAMPLE-CHUNKER] 📄 Alternative split {i}: {len(full_example)} chars")
        
        if not examples:
            logger.warning("[SAMPLE-CHUNKER] ⚠️ Alternative splitting failed, using full text as single example")
            examples = [text]
        
        return examples
    
    def _parse_single_example(self, example_text: str, example_num: int) -> Optional[SampleReplySection]:
        """Парсить один приклад на inquiry + response"""
        
        logger.info(f"[SAMPLE-CHUNKER] 🔍 Parsing example {example_num}")
        
        # Розділяємо на inquiry та response частини
        response_split = re.split(r'Response:', example_text, flags=re.IGNORECASE)
        
        if len(response_split) < 2:
            logger.warning(f"[SAMPLE-CHUNKER] ⚠️ Example {example_num}: No 'Response:' marker found")
            return None
        
        inquiry_part = response_split[0].strip()
        response_part = response_split[1].strip() if len(response_split) > 1 else ""
        
        if not response_part:
            logger.warning(f"[SAMPLE-CHUNKER] ⚠️ Example {example_num}: Empty response part")
            return None
        
        # Витягуємо дані з inquiry частини
        customer_name = self._extract_customer_name(inquiry_part)
        service_type = self._extract_service_type(inquiry_part)
        location = self._extract_location(inquiry_part)
        
        # Очищуємо inquiry від "Inquiry information:" маркера
        clean_inquiry = re.sub(r'Inquiry\\s+information:', '', inquiry_part, flags=re.IGNORECASE).strip()
        
        section = SampleReplySection(
            example_number=example_num,
            inquiry_text=clean_inquiry,
            response_text=response_part,
            customer_name=customer_name,
            service_type=service_type,
            location=location,
            raw_inquiry=inquiry_part,
            raw_response=response_part
        )
        
        logger.info(f"[SAMPLE-CHUNKER] ✅ Example {example_num} parsed:")
        logger.info(f"[SAMPLE-CHUNKER]   Customer: {customer_name}")
        logger.info(f"[SAMPLE-CHUNKER]   Service: {service_type}")
        logger.info(f"[SAMPLE-CHUNKER]   Location: {location}")
        logger.info(f"[SAMPLE-CHUNKER]   Inquiry length: {len(clean_inquiry)} chars")
        logger.info(f"[SAMPLE-CHUNKER]   Response length: {len(response_part)} chars")
        
        return section
    
    def _extract_customer_name(self, inquiry_text: str) -> Optional[str]:
        """Витягує ім'я клієнта"""
        name_match = re.search(r'Name:\\s*([A-Z][a-z]+\\s*[A-Z]?\\.?)', inquiry_text)
        return name_match.group(1).strip() if name_match else None
    
    def _extract_service_type(self, inquiry_text: str) -> Optional[str]:
        """Витягує тип послуги"""
        # Шукаємо в другому рядку після Name:
        lines = inquiry_text.split('\\n')
        for line in lines[1:3]:  # Перевіряємо перші 2 рядки після Name
            line = line.strip()
            if line and not line.startswith(('Lead created:', 'What kind of', 'How many')):
                return line
        return None
    
    def _extract_location(self, inquiry_text: str) -> Optional[str]:
        """Витягує локацію"""
        # Шукаємо CA zip код або назву міста
        location_match = re.search(r'([A-Za-z\\s-]+,?\\s*CA\\s*\\d{5})', inquiry_text)
        if location_match:
            return location_match.group(1).strip()
        
        # Альтернативно шукаємо just ZIP
        zip_match = re.search(r'(\\d{5})', inquiry_text)
        if zip_match:
            return zip_match.group(1)
        
        return None
    
    def create_optimized_chunks(self, sections: List[SampleReplySection]) -> List[Dict]:
        """Створює оптимізовані chunks з розпарсених секцій"""
        
        logger.info(f"[SAMPLE-CHUNKER] 🧩 Creating optimized chunks from {len(sections)} sections")
        
        chunks = []
        chunk_index = 0
        
        for section in sections:
            # 1. Створюємо inquiry chunk
            inquiry_chunk = {
                'content': section.inquiry_text,
                'chunk_type': 'inquiry',
                'chunk_index': chunk_index,
                'metadata': {
                    'example_number': section.example_number,
                    'customer_name': section.customer_name,
                    'service_type': section.service_type,
                    'location': section.location,
                    'chunk_purpose': 'customer_data',
                    'has_inquiry': True,
                    'has_response': False
                }
            }
            chunks.append(inquiry_chunk)
            chunk_index += 1
            
            # 2. Створюємо response chunk
            response_chunk = {
                'content': section.response_text,
                'chunk_type': 'response', 
                'chunk_index': chunk_index,
                'metadata': {
                    'example_number': section.example_number,
                    'customer_name': section.customer_name,
                    'service_type': section.service_type,
                    'location': section.location,
                    'chunk_purpose': 'business_response',
                    'has_inquiry': False,
                    'has_response': True,
                    'response_style': self._analyze_response_style(section.response_text)
                }
            }
            chunks.append(response_chunk)
            chunk_index += 1
            
            # 3. Опційно створюємо combined example chunk
            if len(section.inquiry_text) + len(section.response_text) < 1000:  # Якщо не занадто довгий
                combined_chunk = {
                    'content': f"Customer inquiry:\\n{section.inquiry_text}\\n\\nBusiness response:\\n{section.response_text}",
                    'chunk_type': 'example',
                    'chunk_index': chunk_index, 
                    'metadata': {
                        'example_number': section.example_number,
                        'customer_name': section.customer_name,
                        'service_type': section.service_type,
                        'location': section.location,
                        'chunk_purpose': 'complete_example',
                        'has_inquiry': True,
                        'has_response': True
                    }
                }
                chunks.append(combined_chunk)
                chunk_index += 1
        
        logger.info(f"[SAMPLE-CHUNKER] ✅ Created {len(chunks)} optimized chunks")
        
        # Статистика
        stats = {}
        for chunk in chunks:
            chunk_type = chunk['chunk_type']
            stats[chunk_type] = stats.get(chunk_type, 0) + 1
        
        logger.info(f"[SAMPLE-CHUNKER] 📊 Chunk distribution: {stats}")
        
        return chunks
    
    def _analyze_response_style(self, response_text: str) -> Dict:
        """Аналізує стиль відповіді для кращого matching"""
        
        text_lower = response_text.lower()
        
        style_features = {
            'greeting_type': None,
            'tone': 'professional',
            'has_questions': '?' in response_text,
            'has_business_hours': any(time in text_lower for time in ['9am', '6pm', 'monday', 'friday']),
            'has_signature': any(name in text_lower for name in ['norma', 'talk soon']),
            'length_category': 'short' if len(response_text) < 200 else 'medium' if len(response_text) < 400 else 'long'
        }
        
        # Визначаємо тип привітання
        if 'good afternoon' in text_lower:
            style_features['greeting_type'] = 'afternoon'
        elif 'good morning' in text_lower:
            style_features['greeting_type'] = 'morning'
        elif 'good evening' in text_lower:
            style_features['greeting_type'] = 'evening'
        elif 'hello' in text_lower:
            style_features['greeting_type'] = 'hello'
        
        # Визначаємо тон
        if any(casual in text_lower for casual in ['thanks so much', "we'd be glad", 'talk soon']):
            style_features['tone'] = 'friendly'
        elif any(formal in text_lower for formal in ['we appreciate', 'thank you for your inquiry']):
            style_features['tone'] = 'formal'
        
        return style_features


# Global instance
sample_replies_chunker = SampleRepliesChunker()
