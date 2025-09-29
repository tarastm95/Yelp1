"""
🚀 Hybrid Enterprise-Grade Chunk Classifier
Гібридний підхід: Rules → Scoring → Zero-shot → ML Fallback

Based on professional NLP pipeline architecture for business document classification.
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Advanced NLP dependencies with fallback handling
try:
    import spacy
    from spacy.matcher import Matcher, PhraseMatcher
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import pdfplumber
    import pdfminer
    ADVANCED_PDF_AVAILABLE = True
except ImportError:
    ADVANCED_PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Результат класифікації з confidence scoring"""
    predicted_type: str
    confidence_score: float
    method_used: str
    rule_matches: Dict[str, int]
    fallback_used: bool = False

class HybridChunkClassifier:
    """🧠 Enterprise-grade гібридний classifier для Sample Replies"""
    
    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.phrase_matcher = None
        self.zero_shot_classifier = None
        self.confidence_threshold = 1.0  # ⬇️ Знижений поріг для кращого розпізнавання
        
        self._init_spacy()
        self._init_zero_shot()
        self._setup_patterns()
    
    def _init_spacy(self):
        """Ініціалізація spaCy з Matcher/PhraseMatcher"""
        if not SPACY_AVAILABLE:
            logger.warning("[HYBRID-CLASSIFIER] ⚠️ spaCy not available, using basic rules")
            return
        
        try:
            # Завантажуємо мілку модель для швидкості
            self.nlp = spacy.load("en_core_web_sm")
            self.matcher = Matcher(self.nlp.vocab)
            self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
            
            logger.info("[HYBRID-CLASSIFIER] ✅ spaCy initialized successfully")
            
        except OSError:
            logger.warning("[HYBRID-CLASSIFIER] ⚠️ spaCy model not found, downloading...")
            try:
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
                self.nlp = spacy.load("en_core_web_sm")
                self.matcher = Matcher(self.nlp.vocab)
                self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
                logger.info("[HYBRID-CLASSIFIER] ✅ spaCy model downloaded and initialized")
            except Exception as e:
                logger.error(f"[HYBRID-CLASSIFIER] ❌ Failed to download spaCy model: {e}")
                self.nlp = None
        
        except Exception as e:
            logger.error(f"[HYBRID-CLASSIFIER] ❌ spaCy initialization failed: {e}")
            self.nlp = None
    
    def _init_zero_shot(self):
        """Ініціалізація zero-shot classifier для edge cases"""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("[HYBRID-CLASSIFIER] ⚠️ Transformers not available, no zero-shot fallback")
            return
        
        try:
            # Легка модель для zero-shot classification
            self.zero_shot_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # CPU only для стабільності
            )
            logger.info("[HYBRID-CLASSIFIER] ✅ Zero-shot classifier initialized")
            
        except Exception as e:
            logger.error(f"[HYBRID-CLASSIFIER] ❌ Zero-shot initialization failed: {e}")
            self.zero_shot_classifier = None
    
    def _setup_patterns(self):
        """Налаштування spaCy patterns для rule-based classification"""
        if not self.matcher:
            return
        
        # 💬 BUSINESS RESPONSE patterns (Norma's communication style)
        response_patterns = [
            # Greetings
            [{"LOWER": "good"}, {"LOWER": {"IN": ["afternoon", "morning", "evening"]}}],
            [{"LOWER": "hello"}, {"LOWER": {"IN": ["there", "john", "sarah", "mike"]}, "OP": "?"}],
            
            # Acknowledgments
            [{"LOWER": "thanks"}, {"LOWER": "for"}, {"LOWER": {"IN": ["reaching", "contacting", "sharing"]}}],
            [{"LOWER": "thank"}, {"LOWER": "you"}, {"LOWER": "for"}],
            
            # Business language
            [{"LOWER": "we"}, {"LOWER": {"IN": ["would", "could", "can", "are", "will"]}}],
            [{"LOWER": "we'd"}, {"LOWER": "be"}, {"LOWER": {"IN": ["glad", "happy"]}}],
            [{"LOWER": "our"}, {"LOWER": {"IN": ["team", "company", "services"]}}],
            
            # Closing phrases
            [{"LOWER": "talk"}, {"LOWER": "soon"}],
            [{"LOWER": "let"}, {"LOWER": "me"}, {"LOWER": "know"}],
            [{"LOWER": "please"}, {"LOWER": {"IN": ["let", "feel", "don't"]}}],
        ]
        
        # 📋 CUSTOMER INQUIRY patterns (structured data)
        inquiry_patterns = [
            # Lead structure
            [{"LOWER": "name:"}, {"IS_ALPHA": True, "OP": "+"}],
            [{"LOWER": "lead"}, {"LOWER": "created:"}],
            
            # Yelp questions
            [{"LOWER": "what"}, {"LOWER": {"IN": ["kind", "type"]}}, {"LOWER": "of"}],
            [{"LOWER": "how"}, {"LOWER": "many"}, {"LOWER": {"IN": ["stories", "floors"]}}],
            [{"LOWER": "when"}, {"LOWER": "do"}, {"LOWER": "you"}, {"LOWER": "require"}],
            [{"LOWER": "in"}, {"LOWER": "what"}, {"LOWER": "location"}],
            
            # Geographic markers
            [{"LOWER": "ca"}, {"LIKE_NUM": True}],  # CA 91331
            [{"TEXT": {"REGEX": r"^\d{5}$"}}],      # ZIP codes
        ]
        
        # Реєструємо patterns
        self.matcher.add("RESPONSE_PATTERNS", response_patterns)
        self.matcher.add("INQUIRY_PATTERNS", inquiry_patterns)
        
        logger.info(f"[HYBRID-CLASSIFIER] 📝 Registered {len(response_patterns)} response + {len(inquiry_patterns)} inquiry patterns")
    
    def classify_chunk_hybrid(self, text: str) -> ClassificationResult:
        """🎯 Гібридна класифікація за вашим планом"""
        
        logger.info(f"[HYBRID-CLASSIFIER] 🧠 Classifying chunk: {text[:100]}...")
        
        # 🔍 ЕТАП 1: Explicit Markers (найвища впевненість)
        explicit_result = self._check_explicit_markers(text)
        if explicit_result:
            return explicit_result
        
        # 🔍 ЕТАП 2: Rule-based + spaCy Patterns
        rule_result = self._rule_based_classification(text)
        if rule_result.confidence_score >= self.confidence_threshold:
            return rule_result
        
        # 🔍 ЕТАП 3: Zero-shot Classification (для edge cases)
        zero_shot_result = self._zero_shot_classification(text)
        if zero_shot_result:
            return zero_shot_result
        
        # 🔍 ЕТАП 4: ML Fallback
        ml_result = self._ml_fallback_classification(text)
        if ml_result:
            return ml_result
        
        # 🔍 ЕТАП 5: Default fallback
        return ClassificationResult(
            predicted_type='general',
            confidence_score=0.0,
            method_used='default_fallback',
            rule_matches={},
            fallback_used=True
        )
    
    def _check_explicit_markers(self, text: str) -> Optional[ClassificationResult]:
        """Перевірка явних маркерів (highest confidence)"""
        text_lower = text.lower().strip()
        
        # Явні секційні маркери
        if 'response:' in text_lower:
            return ClassificationResult(
                predicted_type='response',
                confidence_score=10.0,
                method_used='explicit_response_marker',
                rule_matches={'response_marker': 1}
            )
        
        if 'inquiry information:' in text_lower:
            return ClassificationResult(
                predicted_type='inquiry',
                confidence_score=10.0,
                method_used='explicit_inquiry_marker',
                rule_matches={'inquiry_marker': 1}
            )
        
        if 'inquiry information:' in text_lower and 'response:' in text_lower:
            return ClassificationResult(
                predicted_type='example',
                confidence_score=10.0,
                method_used='explicit_mixed_marker',
                rule_matches={'mixed_markers': 1}
            )
        
        return None
    
    def _rule_based_classification(self, text: str) -> ClassificationResult:
        """Rule-based класифікація з spaCy patterns та scoring"""
        
        rule_matches = {
            'response': 0,
            'inquiry': 0,
            'example': 0,
            'general': 0
        }
        
        # 💬 BUSINESS RESPONSE indicators
        response_phrases = [
            'good afternoon', 'good morning', 'good evening',
            'thanks for reaching', 'thank you for', 'thanks so much',
            "we'd be glad", "we'd be happy", 'we could set up', 'we can take care',
            'talk soon', 'our team', 'our company', 'our services',
            'please let', 'please feel', 'if you have any',
            'we look forward', 'we understand', 'we appreciate'
        ]
        
        # 📋 CUSTOMER INQUIRY indicators  
        inquiry_phrases = [
            'name:', 'lead created:', 'lead id:',
            'what kind of', 'what type of', 'how many stories',
            'when do you require', 'in what location', 'are there any other details',
            'what structural element', 'do you need the service'
        ]
        
        # 🏢 CUSTOMER DATA patterns (structured data)
        inquiry_patterns = [
            r'\bname:\s*[A-Z][a-z]+ [A-Z]\.?\b',  # Name: John D.
            r'\bca \d{5}\b',                      # CA 91331
            r'\blead created: \d{1,2}/\d{1,2}/\d{4}',  # Lead created: 8/27/2025
            r'\b\d{1,2} story\b',                 # 1 story, 2 story
            r'\bas soon as possible\b',           # Service urgency
        ]
        
        text_lower = text.lower()
        
        # Rule-based scoring
        for phrase in response_phrases:
            if phrase in text_lower:
                rule_matches['response'] += 1
        
        for phrase in inquiry_phrases:
            if phrase in text_lower:
                rule_matches['inquiry'] += 1
        
        # Pattern matching для structured data
        for pattern in inquiry_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                rule_matches['inquiry'] += 1
        
        # spaCy advanced matching (якщо доступно)
        if self.nlp and self.matcher:
            try:
                doc = self.nlp(text)
                matches = self.matcher(doc)
                
                for match_id, start, end in matches:
                    match_label = self.nlp.vocab.strings[match_id]
                    if match_label == "RESPONSE_PATTERNS":
                        rule_matches['response'] += 1
                    elif match_label == "INQUIRY_PATTERNS":
                        rule_matches['inquiry'] += 1
                        
            except Exception as e:
                logger.warning(f"[HYBRID-CLASSIFIER] spaCy matching failed: {e}")
        
        # 📊 Scoring and classification
        max_score = max(rule_matches.values())
        predicted_types = [k for k, v in rule_matches.items() if v == max_score and v > 0]
        
        if not predicted_types or max_score == 0:
            predicted_type = 'general'
            confidence = 0.0
            method = 'no_rule_matches'
        elif len(predicted_types) == 1:
            predicted_type = predicted_types[0]
            confidence = float(max_score)
            method = 'rule_based_clear'
        else:
            # Tie-breaking logic
            if 'response' in predicted_types:
                predicted_type = 'response'  # Prioritize business responses
            elif 'inquiry' in predicted_types:
                predicted_type = 'inquiry'
            else:
                predicted_type = predicted_types[0]
            
            confidence = float(max_score) * 0.8  # Penalty for ties
            method = 'rule_based_tiebreak'
        
        logger.info(f"[HYBRID-CLASSIFIER] 📊 Rule scoring: {rule_matches}")
        logger.info(f"[HYBRID-CLASSIFIER] 🎯 Rule prediction: {predicted_type} (score: {confidence})")
        
        return ClassificationResult(
            predicted_type=predicted_type,
            confidence_score=confidence,
            method_used=method,
            rule_matches=rule_matches
        )
    
    def _zero_shot_classification(self, text: str) -> Optional[ClassificationResult]:
        """Zero-shot classification для невизначених cases"""
        
        if not self.zero_shot_classifier:
            logger.warning("[HYBRID-CLASSIFIER] ⚠️ Zero-shot classifier not available")
            return None
        
        try:
            # Candidate labels для zero-shot
            candidate_labels = [
                "customer inquiry",      # Клієнтські запити та дані
                "business response",     # Відповіді компанії
                "mixed conversation",    # Змішаний контент
                "general information"    # Загальна інформація
            ]
            
            logger.info("[HYBRID-CLASSIFIER] 🔍 Applying zero-shot classification...")
            
            result = self.zero_shot_classifier(text, candidate_labels)
            
            # Mapping zero-shot labels to our types
            label_mapping = {
                "customer inquiry": "inquiry",
                "business response": "response", 
                "mixed conversation": "example",
                "general information": "general"
            }
            
            predicted_label = result['labels'][0]
            confidence = result['scores'][0]
            predicted_type = label_mapping.get(predicted_label, 'general')
            
            logger.info(f"[HYBRID-CLASSIFIER] 🤖 Zero-shot: {predicted_label} → {predicted_type} (conf: {confidence:.3f})")
            
            # Поріг впевненості для zero-shot
            if confidence >= 0.7:  # High confidence
                return ClassificationResult(
                    predicted_type=predicted_type,
                    confidence_score=confidence * 5.0,  # Scale to match rule scoring
                    method_used='zero_shot_high_confidence',
                    rule_matches={'zero_shot_score': confidence}
                )
            elif confidence >= 0.5:  # Medium confidence
                return ClassificationResult(
                    predicted_type=predicted_type,
                    confidence_score=confidence * 3.0,
                    method_used='zero_shot_medium_confidence', 
                    rule_matches={'zero_shot_score': confidence}
                )
            else:
                logger.warning(f"[HYBRID-CLASSIFIER] ⚠️ Zero-shot low confidence: {confidence:.3f}")
                return None
                
        except Exception as e:
            logger.error(f"[HYBRID-CLASSIFIER] ❌ Zero-shot classification failed: {e}")
            return None
    
    def _ml_fallback_classification(self, text: str) -> Optional[ClassificationResult]:
        """🚫 ML fallback відключений до встановлення scikit-learn"""
        logger.warning("[HYBRID-CLASSIFIER] ⚠️ ML fallback not available - using simplified heuristics")
        
        # Простий heuristic fallback на основі довжини та структури
        text_lower = text.lower().strip()
        text_len = len(text)
        
        # Структурні дані зазвичай коротші та містять двокрапки
        colon_count = text_lower.count(':')
        has_structured_data = colon_count >= 2 and text_len < 300
        
        # Довгі тексти з бізнес-мовою
        has_business_language = any(word in text_lower for word in ['we', 'our', 'company', 'service', 'team'])
        is_long_text = text_len > 100
        
        if has_structured_data:
            return ClassificationResult(
                predicted_type='inquiry',
                confidence_score=1.5,  # Medium confidence for heuristics
                method_used='heuristic_structured',
                rule_matches={'colon_count': colon_count, 'text_length': text_len}
            )
        elif has_business_language and is_long_text:
            return ClassificationResult(
                predicted_type='response', 
                confidence_score=1.2,  # Lower confidence for heuristics
                method_used='heuristic_business',
                rule_matches={'text_length': text_len, 'business_indicators': 1}
            )
        
        # Якщо нічого не підходить
        logger.warning("[HYBRID-CLASSIFIER] ⚠️ Heuristic fallback: no clear pattern detected")
        return None
    
    def classify_chunk(self, text: str) -> str:
        """Основний метод класифікації (для сумісності з існуючим кодом)"""
        result = self.classify_chunk_hybrid(text)
        
        logger.info(f"[HYBRID-CLASSIFIER] 🏆 Final classification: {result.predicted_type}")
        logger.info(f"[HYBRID-CLASSIFIER] 📊 Method: {result.method_used}, Confidence: {result.confidence_score:.2f}")
        
        return result.predicted_type
    
    def get_classification_stats(self) -> Dict:
        """Статистика методів класифікації"""
        return {
            'spacy_available': SPACY_AVAILABLE,
            'transformers_available': TRANSFORMERS_AVAILABLE,
            'advanced_pdf_available': ADVANCED_PDF_AVAILABLE,
            'confidence_threshold': self.confidence_threshold,
            'methods': [
                '1. Explicit Markers (highest confidence)',
                '2. Rule-based + spaCy Patterns',
                '3. Zero-shot Classification',
                '4. ML Fallback',
                '5. Default General'
            ]
        }


# Global instance
hybrid_classifier = HybridChunkClassifier()
