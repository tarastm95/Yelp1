"""
🎯 Simple AI-Powered Extractor (без ExtractThinker)
Використовує тільки OpenAI API + Pydantic для structured extraction
"""

import logging
import re
import json
from typing import List, Dict, Optional, Tuple

# Lightweight imports only
from .extraction_contracts import CustomerInquiry, BusinessResponse, SampleReplyExample, SampleRepliesDocument

logger = logging.getLogger(__name__)


class SimpleAIExtractor:
    """🧠 Lightweight AI Extractor using only OpenAI + Pydantic"""
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """Ініціалізація OpenAI клієнта"""
        try:
            import os
            import openai
            
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                from .models import AISettings
                ai_settings = AISettings.objects.first()
                if ai_settings and ai_settings.openai_api_key:
                    openai_api_key = ai_settings.openai_api_key
            
            if openai_api_key:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("[SIMPLE-AI-EXTRACTOR] ✅ OpenAI client initialized")
            else:
                logger.error("[SIMPLE-AI-EXTRACTOR] ❌ No OpenAI API key found")
                
        except Exception as e:
            logger.error(f"[SIMPLE-AI-EXTRACTOR] ❌ Failed to initialize: {e}")
    
    def parse_sample_replies_document(self, text: str) -> Optional[SampleRepliesDocument]:
        """
        🎯 Головний метод парсингу Sample Replies документа
        """
        
        logger.info(f"[SIMPLE-AI-EXTRACTOR] 🚀 PARSING SAMPLE REPLIES DOCUMENT")
        logger.info(f"[SIMPLE-AI-EXTRACTOR] Document length: {len(text)} chars")
        
        if not self.openai_client:
            logger.warning("[SIMPLE-AI-EXTRACTOR] ⚠️ OpenAI not available, using regex fallback")
            return self._regex_fallback_parsing(text)
        
        try:
            # 1. Розділяємо документ на секції
            sections = self._split_by_markers(text)
            
            if not sections:
                logger.warning("[SIMPLE-AI-EXTRACTOR] ⚠️ No sections found")
                return self._regex_fallback_parsing(text)
            
            # 2. Групуємо секції в приклади
            examples = self._group_sections_into_examples(sections)
            
            # 3. Витягуємо structured data для кожного прикладу
            structured_examples = []
            
            for example_data in examples:
                try:
                    structured_example = self._extract_example_with_openai(example_data)
                    if structured_example:
                        structured_examples.append(structured_example)
                        
                except Exception as e:
                    logger.warning(f"[SIMPLE-AI-EXTRACTOR] ⚠️ Failed to extract example: {e}")
            
            # 4. Створюємо документ
            document = SampleRepliesDocument(
                document_title=self._extract_document_title(text),
                business_name=self._extract_business_name(text),
                examples=structured_examples,
                total_examples=len(structured_examples),
                extraction_quality=self._assess_quality(structured_examples),
                raw_document_text=text
            )
            
            logger.info(f"[SIMPLE-AI-EXTRACTOR] ✅ SUCCESS: {len(structured_examples)} examples extracted")
            return document
            
        except Exception as e:
            logger.error(f"[SIMPLE-AI-EXTRACTOR] ❌ Extraction failed: {e}")
            return self._regex_fallback_parsing(text)
    
    def _split_by_markers(self, text: str) -> List[Dict]:
        """Розділяє документ за маркерами"""
        
        patterns = {
            'example': r'Example\s*#?\s*(\d+)',
            'inquiry': r'Inquiry\s+information:',
            'response': r'Response:'
        }
        
        markers = []
        for marker_type, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                markers.append({
                    'type': marker_type,
                    'position': match.start(),
                    'text': match.group(),
                    'number': int(match.group(1)) if marker_type == 'example' and match.groups() else None
                })
        
        markers.sort(key=lambda x: x['position'])
        
        logger.info(f"[SIMPLE-AI-EXTRACTOR] Found {len(markers)} markers")
        
        sections = []
        for i, marker in enumerate(markers):
            start_pos = marker['position']
            end_pos = markers[i + 1]['position'] if i + 1 < len(markers) else len(text)
            section_text = text[start_pos:end_pos].strip()
            
            if len(section_text) > 20:
                sections.append({
                    'type': marker['type'],
                    'content': section_text,
                    'example_number': marker.get('number')
                })
        
        return sections
    
    def _group_sections_into_examples(self, sections: List[Dict]) -> List[Dict]:
        """Групує секції в inquiry+response пари"""
        
        examples = []
        current_example = None
        
        for section in sections:
            if section['type'] == 'example':
                # Зберігаємо попередній приклад
                if current_example and current_example.get('inquiry') and current_example.get('response'):
                    examples.append(current_example)
                
                # Новий приклад
                current_example = {
                    'example_number': section.get('example_number'),
                    'inquiry': None,
                    'response': None
                }
                
            elif section['type'] == 'inquiry' and current_example is not None:
                current_example['inquiry'] = section
                
            elif section['type'] == 'response' and current_example is not None:
                current_example['response'] = section
        
        # Додаємо останній приклад
        if current_example and current_example.get('inquiry') and current_example.get('response'):
            examples.append(current_example)
        
        logger.info(f"[SIMPLE-AI-EXTRACTOR] Grouped into {len(examples)} complete examples")
        return examples
    
    def _extract_example_with_openai(self, example_data: Dict) -> Optional[SampleReplyExample]:
        """Витягує structured data використовуючи OpenAI API"""
        
        inquiry_section = example_data.get('inquiry', {})
        response_section = example_data.get('response', {})
        
        if not inquiry_section or not response_section:
            return None
        
        inquiry_text = inquiry_section.get('content', '')
        response_text = response_section.get('content', '')
        
        logger.info(f"[SIMPLE-AI-EXTRACTOR] 🧠 Extracting with OpenAI...")
        
        try:
            # Extract inquiry data
            inquiry_data = self._extract_inquiry_data(inquiry_text)
            
            # Extract response data  
            response_data = self._extract_response_data(response_text, inquiry_data.get('customer_name'))
            
            # Створюємо Pydantic об'єкти
            inquiry_obj = CustomerInquiry(
                raw_text=inquiry_text,
                **inquiry_data
            )
            
            response_obj = BusinessResponse(
                raw_text=response_text,
                **response_data
            )
            
            return SampleReplyExample(
                example_number=example_data.get('example_number'),
                inquiry=inquiry_obj,
                response=response_obj,
                context_match_score=self._calculate_context_match(inquiry_obj, response_obj)
            )
            
        except Exception as e:
            logger.error(f"[SIMPLE-AI-EXTRACTOR] ❌ OpenAI extraction failed: {e}")
            return self._regex_fallback_example(example_data)
    
    def _extract_inquiry_data(self, inquiry_text: str) -> Dict:
        """Витягує дані inquiry через OpenAI"""
        
        system_prompt = """You are a data extraction specialist. Extract structured information from customer inquiry text.

Return ONLY valid JSON with these fields (use null if not found):
{
  "customer_name": "First name + Last initial (e.g., 'Beau S.')",
  "service_type": "Type of service requested",
  "location": "Full location including city, state, ZIP",
  "roof_covering_type": "Type of roof covering requested",
  "building_stories": "Number of stories",
  "service_urgency": "When service is needed",
  "zip_code": "ZIP code only"
}

Extract exactly as written in the text. Use null for missing fields."""

        user_prompt = f"Extract data from this customer inquiry:\n\n{inquiry_text}"
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '')
            
            result = json.loads(result_text)
            logger.info(f"[SIMPLE-AI-EXTRACTOR] ✅ Inquiry extracted: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"[SIMPLE-AI-EXTRACTOR] ⚠️ OpenAI inquiry extraction failed: {e}")
            return self._regex_extract_inquiry(inquiry_text)
    
    def _extract_response_data(self, response_text: str, customer_name: Optional[str] = None) -> Dict:
        """Витягує дані response через OpenAI"""
        
        system_prompt = """You are a business communication analyst. Extract structured information from business response text.

Return ONLY valid JSON with these fields (use null if not found):
{
  "greeting_type": "Type of greeting used",
  "customer_name_mentioned": "Customer name mentioned in response",
  "acknowledgment_phrase": "How business acknowledges the request",
  "questions_asked": ["List", "of", "questions", "asked"],
  "availability_mention": "Business hours or availability mentioned",
  "closing_phrase": "How the response ends",
  "signature": "Person who signed the response",
  "tone": "Overall tone (friendly/professional/formal)"
}

Extract exactly as written. Use null for missing fields."""

        user_prompt = f"Extract data from this business response:\n\n{response_text}"
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '')
            
            result = json.loads(result_text)
            logger.info(f"[SIMPLE-AI-EXTRACTOR] ✅ Response extracted: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"[SIMPLE-AI-EXTRACTOR] ⚠️ OpenAI response extraction failed: {e}")
            return self._regex_extract_response(response_text)
    
    def _regex_extract_inquiry(self, text: str) -> Dict:
        """Regex fallback для inquiry"""
        
        result = {}
        
        # Customer name
        name_match = re.search(r'Name:\s*([A-Z][a-z]+\s*[A-Z]?\.?)', text)
        if name_match:
            result['customer_name'] = name_match.group(1).strip()
        
        # Service type (зазвичай другий рядок)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines[1:4]:
            if not line.startswith(('Lead created:', 'What kind of', 'How many')):
                result['service_type'] = line
                break
        
        # Location with ZIP
        location_match = re.search(r'([A-Za-z\s-]+,?\s*CA\s*\d{5})', text)
        if location_match:
            result['location'] = location_match.group(1).strip()
        
        # ZIP code
        zip_match = re.search(r'(\d{5})', text)
        if zip_match:
            result['zip_code'] = zip_match.group(1)
        
        # Building stories
        stories_match = re.search(r'(\d+\s*stor(?:y|ies))', text, re.IGNORECASE)
        if stories_match:
            result['building_stories'] = stories_match.group(1)
        
        # Roof covering
        if 'asphalt shingles' in text.lower():
            result['roof_covering_type'] = 'Asphalt shingles'
        elif 'concrete tile' in text.lower():
            result['roof_covering_type'] = 'Concrete tile'
        
        # Service urgency
        if 'as soon as possible' in text.lower():
            result['service_urgency'] = 'As soon as possible'
        elif "i'm flexible" in text.lower():
            result['service_urgency'] = "I'm flexible"
        
        logger.info(f"[SIMPLE-AI-EXTRACTOR] 🔄 Regex inquiry fallback: {result}")
        return result
    
    def _regex_extract_response(self, text: str) -> Dict:
        """Regex fallback для response"""
        
        result = {}
        text_lower = text.lower()
        
        # Greeting type
        if 'good afternoon' in text_lower:
            result['greeting_type'] = 'Good afternoon'
        elif 'good morning' in text_lower:
            result['greeting_type'] = 'Good morning'
        elif 'hello' in text_lower:
            result['greeting_type'] = 'Hello'
        
        # Customer name mentioned
        customer_match = re.search(r'good\s+(?:afternoon|morning)\s+([A-Z][a-z]+)', text, re.IGNORECASE)
        if customer_match:
            result['customer_name_mentioned'] = customer_match.group(1)
        
        # Acknowledgment
        if 'thanks for reaching out' in text_lower:
            result['acknowledgment_phrase'] = 'Thanks for reaching out'
        elif 'thank you for' in text_lower:
            result['acknowledgment_phrase'] = 'Thank you for'
        
        # Questions (simple detection)
        questions = re.findall(r'([^.!?]*\?)', text)
        if questions:
            result['questions_asked'] = [q.strip() + '?' for q in questions]
        
        # Availability  
        if 'monday to friday' in text_lower or '9am' in text_lower:
            availability_match = re.search(r'(monday to friday between \d+am and \d+pm)', text_lower)
            if availability_match:
                result['availability_mention'] = availability_match.group(1)
        
        # Closing phrase
        if 'talk soon' in text_lower:
            result['closing_phrase'] = 'Talk soon'
        elif 'let me know' in text_lower:
            result['closing_phrase'] = 'Let me know'
        
        # Signature
        if 'norma' in text_lower:
            result['signature'] = 'Norma'
        
        # Tone analysis
        if any(casual in text_lower for casual in ['thanks so much', "we'd be glad", 'talk soon']):
            result['tone'] = 'friendly'
        elif any(formal in text_lower for formal in ['we appreciate', 'thank you for your inquiry']):
            result['tone'] = 'formal'
        else:
            result['tone'] = 'professional'
        
        logger.info(f"[SIMPLE-AI-EXTRACTOR] 🔄 Regex response fallback: {result}")
        return result
    
    def _calculate_context_match(self, inquiry: CustomerInquiry, response: BusinessResponse) -> float:
        """Розраховує context match score"""
        
        score = 0.0
        
        # Name matching
        if inquiry.customer_name and response.customer_name_mentioned:
            if inquiry.customer_name.split()[0].lower() in response.customer_name_mentioned.lower():
                score += 0.4
        
        # Service acknowledgment
        if inquiry.service_type and any(word in response.raw_text.lower() 
                                       for word in inquiry.service_type.lower().split()):
            score += 0.3
        
        # Professional response structure
        if response.greeting_type and response.closing_phrase:
            score += 0.3
        
        return min(score, 1.0)
    
    def _extract_document_title(self, text: str) -> Optional[str]:
        """Витягує title документа"""
        lines = text.split('\n')[:3]
        for line in lines:
            line = line.strip()
            if len(line) > 10 and ('sample replies' in line.lower() or 'roofing' in line.lower()):
                return line
        return None
    
    def _extract_business_name(self, text: str) -> Optional[str]:
        """Витягує назву бізнесу"""
        title_match = re.search(r'Sample Replies\s*[–-]\s*(.+)', text, re.IGNORECASE)
        if title_match:
            business_name = title_match.group(1).strip()
            business_name = re.sub(r'\s*Roofing\s*$', '', business_name, re.IGNORECASE)
            return business_name
        return None
    
    def _assess_quality(self, examples: List[SampleReplyExample]) -> str:
        """Оцінює якість extraction"""
        if not examples:
            return "poor"
        
        complete_count = 0
        for example in examples:
            if (example.inquiry.customer_name and 
                example.inquiry.service_type and 
                example.response.greeting_type and 
                example.response.tone):
                complete_count += 1
        
        rate = complete_count / len(examples)
        
        if rate >= 0.8:
            return "excellent"
        elif rate >= 0.6:
            return "good"
        elif rate >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _regex_fallback_parsing(self, text: str) -> SampleRepliesDocument:
        """Повний regex fallback без AI"""
        
        logger.warning("[SIMPLE-AI-EXTRACTOR] 🔄 Using complete regex fallback")
        
        sections = self._split_by_markers(text)
        examples = self._group_sections_into_examples(sections)
        
        structured_examples = []
        for example_data in examples:
            inquiry_text = example_data['inquiry']['content']
            response_text = example_data['response']['content']
            
            inquiry_obj = CustomerInquiry(
                raw_text=inquiry_text,
                **self._regex_extract_inquiry(inquiry_text)
            )
            
            response_obj = BusinessResponse(
                raw_text=response_text,
                **self._regex_extract_response(response_text)
            )
            
            structured_examples.append(SampleReplyExample(
                example_number=example_data.get('example_number'),
                inquiry=inquiry_obj,
                response=response_obj,
                context_match_score=self._calculate_context_match(inquiry_obj, response_obj)
            ))
        
        return SampleRepliesDocument(
            document_title=self._extract_document_title(text),
            business_name=self._extract_business_name(text),
            examples=structured_examples,
            total_examples=len(structured_examples),
            extraction_quality="fair",
            raw_document_text=text
        )


# Global instance
simple_ai_extractor = SimpleAIExtractor()
