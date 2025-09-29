"""
🤖 Machine Learning Chunk Classifier for Sample Replies
Професійний ML/NLP підхід для класифікації типів chunks з використанням scikit-learn
"""

import logging
import os
import pickle
from typing import List, Tuple, Optional
import numpy as np

# ML dependencies (with fallback handling)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    import pandas as pd
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

class MLChunkClassifier:
    """🧠 Machine Learning classifier для автоматичного визначення типів chunks"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.model_path = '/app/ml_models/chunk_classifier.pkl'
        self.feature_names = None
        
        if ML_AVAILABLE:
            self._init_model()
            self._load_or_train_model()
        else:
            logger.warning("[ML-CLASSIFIER] ⚠️ scikit-learn not available, falling back to pattern matching")
    
    def _init_model(self):
        """Ініціалізація ML pipeline"""
        try:
            # TF-IDF Vectorizer для text features
            self.model = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=1000,          # Топ 1000 важливих слів
                    stop_words='english',       # Видаляємо stop words
                    ngram_range=(1, 2),         # Unigrams + bigrams  
                    min_df=2,                   # Слова що з'являються ≥ 2 рази
                    max_df=0.95,                # Не більше ніж 95% документів
                    lowercase=True,
                    strip_accents='ascii'
                )),
                ('classifier', LogisticRegression(
                    random_state=42,
                    max_iter=1000,
                    class_weight='balanced'     # Балансуємо несбалансовані класи
                ))
            ])
            
            logger.info("[ML-CLASSIFIER] ✅ ML Pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] Failed to initialize ML pipeline: {e}")
            self.model = None
    
    def _load_or_train_model(self):
        """Завантажує збережену модель або тренує нову"""
        if self._load_saved_model():
            logger.info("[ML-CLASSIFIER] ✅ Loaded pre-trained model")
            return
        
        logger.info("[ML-CLASSIFIER] 🎓 No saved model found, training new model...")
        self._train_on_synthetic_data()
    
    def _load_saved_model(self) -> bool:
        """Завантажує збережену модель з диску"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.model = saved_data['model']
                    self.feature_names = saved_data.get('feature_names', None)
                    self.is_trained = True
                return True
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] Error loading saved model: {e}")
        return False
    
    def _save_model(self):
        """Зберігає натреновану модель на диск"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'feature_names': self.feature_names
                }, f)
            logger.info(f"[ML-CLASSIFIER] ✅ Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] Error saving model: {e}")
    
    def _create_training_data(self) -> Tuple[List[str], List[str]]:
        """Створює синтетичні training data для класифікації"""
        
        # 📋 INQUIRY examples (customer data)
        inquiry_samples = [
            "Name: John D.\nRoof replacement\nLos Angeles, CA 90210\nLead created: 8/15/2025, 2:30 PM",
            "What kind of roof covering do you want?\nAsphalt shingles\nHow many stories tall is your building?\n2 story",
            "When do you require this service?\nAs soon as possible\nIn what location do you need the service?\n91331",
            "Name: Sarah M.\nNew roof installation\nBurbank, CA 91505\nWhat type of contracting service do you need?\nRoofing",
            "Are there any other details you'd like to share?\nI need a full roof replacement with gutters",
            "Lead created: 8/20/2025, 9:15 AM\nWhat kind of roof covering do you want?\nTile\nHow many stories?\n1 story",
            "Name: Mike R.\nRoof repair\nGlendale, CA 91201\nWhen do you require this service?\nI'm flexible",
            "In what location do you need the service?\n90210\nWhat structural element(s) need repair?\nRoof"
        ]
        
        # 💬 RESPONSE examples (business communication - Norma's style)
        response_samples = [
            "Good afternoon Beau,\nThanks for reaching out! I see you're looking to replace your 1-story roof with asphalt shingles as soon as possible. We'd be glad to help with that.",
            "Do you happen to know the approximate square footage of your roof, or would you like us to come out and take a look to measure?",
            "We could set up a time to meet — we're available Monday to Friday between 9am and 6pm, but if another time works better for you, just let me know.\nTalk soon,\nNorma",
            "Good morning!\nThanks so much for sharing all the details and photos — that's really helpful. A full roof replacement with gutters and eave repairs is definitely something we can take care of.",
            "To give you accurate pricing, it helps to know: do you prefer a standard architectural asphalt shingle, or are you considering any upgraded styles?",
            "We could also set up a time to meet and take a closer look at your roof and eaves in person.",
            "Thank you for your inquiry about our roofing services. We'd be happy to provide you with a detailed estimate for your project.",
            "Our team specializes in both residential and commercial roofing. We can schedule a convenient time to assess your needs.",
            "We understand the urgency of roof repairs and strive to respond quickly to all inquiries. Please let us know your preferred contact method.",
            "If you have any questions about our services or would like to discuss your project in detail, please don't hesitate to reach out."
        ]
        
        # 📝 EXAMPLE samples (mixed content)
        example_samples = [
            "Inquiry information:\nName: Alex P.\nResponse:\nGood afternoon Alex,\nThanks for your inquiry about roofing services.",
            "Customer: I need roof repair\nBusiness Response: We'd be glad to help with your roof repair needs. Our team can assess the damage and provide recommendations.",
            "Lead: Emergency roof leak\nOur Response: We understand roof leaks require immediate attention. Our emergency team can be on-site within 2 hours."
        ]
        
        # 🔍 GENERAL samples (mixed/unclear content)
        general_samples = [
            "Roofing services include installation, repair, and maintenance of various roof types including asphalt, tile, and metal.",
            "Our company has been serving the greater Los Angeles area for over 15 years with quality roofing solutions.",
            "Standard roofing materials and their typical lifespans: Asphalt shingles 15-30 years, Tile 30-50 years, Metal 40-70 years.",
            "Roof inspection checklist: gutters, flashing, shingles, ventilation, insulation, structural integrity."
        ]
        
        # Об'єднуємо всі samples
        texts = inquiry_samples + response_samples + example_samples + general_samples
        labels = (['inquiry'] * len(inquiry_samples) + 
                 ['response'] * len(response_samples) + 
                 ['example'] * len(example_samples) + 
                 ['general'] * len(general_samples))
        
        logger.info(f"[ML-CLASSIFIER] 📊 Created training data: {len(texts)} samples")
        logger.info(f"[ML-CLASSIFIER] - inquiry: {len(inquiry_samples)} samples")
        logger.info(f"[ML-CLASSIFIER] - response: {len(response_samples)} samples") 
        logger.info(f"[ML-CLASSIFIER] - example: {len(example_samples)} samples")
        logger.info(f"[ML-CLASSIFIER] - general: {len(general_samples)} samples")
        
        return texts, labels
    
    def _train_on_synthetic_data(self):
        """Тренує модель на синтетичних даних"""
        if not self.model:
            logger.error("[ML-CLASSIFIER] ❌ Model not initialized")
            return
        
        try:
            # Створюємо training data
            texts, labels = self._create_training_data()
            
            # Розділяємо на train/test
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=0.3, random_state=42, stratify=labels
            )
            
            logger.info(f"[ML-CLASSIFIER] 🎓 Training on {len(X_train)} samples, testing on {len(X_test)} samples")
            
            # Тренуємо модель
            self.model.fit(X_train, y_train)
            
            # Тестуємо accuracy
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"[ML-CLASSIFIER] ✅ Model trained successfully!")
            logger.info(f"[ML-CLASSIFIER] 📊 Test accuracy: {accuracy:.3f}")
            
            # Детальний звіт по класах
            report = classification_report(y_test, y_pred, output_dict=True)
            for class_name, metrics in report.items():
                if isinstance(metrics, dict) and 'precision' in metrics:
                    logger.info(f"[ML-CLASSIFIER] {class_name}: precision={metrics['precision']:.3f}, recall={metrics['recall']:.3f}")
            
            self.is_trained = True
            self._save_model()
            
            # Отримуємо feature names для interpretability
            try:
                self.feature_names = self.model.named_steps['tfidf'].get_feature_names_out()
                logger.info(f"[ML-CLASSIFIER] 📝 Extracted {len(self.feature_names)} features")
            except:
                pass
                
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] ❌ Training failed: {e}")
            logger.exception("ML training error details:")
    
    def _train_on_existing_chunks(self):
        """Тренує модель на існуючих chunks з database (якщо є достатньо даних)"""
        try:
            from .vector_models import VectorChunk
            
            chunks = VectorChunk.objects.all()
            if chunks.count() < 20:  # Мінімум для тренування
                logger.warning(f"[ML-CLASSIFIER] ⚠️ Not enough existing chunks ({chunks.count()}) for training, using synthetic data")
                return False
            
            texts = []
            labels = []
            
            for chunk in chunks:
                if chunk.chunk_type != 'general':  # Використовуємо тільки класифіковані chunks
                    texts.append(chunk.content)
                    labels.append(chunk.chunk_type)
            
            if len(texts) < 10:
                logger.warning(f"[ML-CLASSIFIER] ⚠️ Not enough classified chunks ({len(texts)}) for training")
                return False
            
            logger.info(f"[ML-CLASSIFIER] 🎓 Training on {len(texts)} existing chunks")
            
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=0.3, random_state=42, stratify=labels
            )
            
            self.model.fit(X_train, y_train)
            
            accuracy = accuracy_score(y_test, self.model.predict(X_test))
            logger.info(f"[ML-CLASSIFIER] ✅ Trained on existing data, accuracy: {accuracy:.3f}")
            
            self.is_trained = True
            self._save_model()
            return True
            
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] ❌ Training on existing chunks failed: {e}")
            return False
    
    def classify_chunk(self, text: str) -> str:
        """Класифікує chunk text використовуючи ML model"""
        
        if not ML_AVAILABLE:
            return self._fallback_classify(text)
        
        if not self.is_trained or not self.model:
            logger.warning("[ML-CLASSIFIER] ⚠️ Model not trained, using fallback classification")
            return self._fallback_classify(text)
        
        try:
            # ML prediction
            prediction = self.model.predict([text])[0]
            confidence = self.model.predict_proba([text]).max()
            
            logger.info(f"[ML-CLASSIFIER] 🧠 ML Classification: {prediction} (confidence: {confidence:.3f})")
            
            # Якщо confidence низький, використовуємо fallback
            if confidence < 0.6:
                logger.warning(f"[ML-CLASSIFIER] ⚠️ Low confidence ({confidence:.3f}), using fallback")
                return self._fallback_classify(text)
            
            return prediction
            
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] ❌ ML classification failed: {e}")
            return self._fallback_classify(text)
    
    def _fallback_classify(self, text: str) -> str:
        """Fallback classification використовуючи pattern matching"""
        text_lower = text.lower().strip()
        
        # Business response patterns
        response_patterns = [
            'good afternoon', 'good morning', 'thanks for reaching out', 
            'thank you for', "we'd be glad", 'we could set up', 'talk soon',
            'thanks so much', 'we can take care of', 'we understand that',
            'our team', 'please let', 'if you have any', 'we look forward'
        ]
        
        # Customer inquiry patterns
        inquiry_patterns = [
            'name:', 'lead created:', 'what kind of', 'how many stories',
            'when do you require', 'in what location', 'are there any other details'
        ]
        
        # Pattern matching
        response_matches = sum(1 for pattern in response_patterns if pattern in text_lower)
        inquiry_matches = sum(1 for pattern in inquiry_patterns if pattern in text_lower)
        
        # Classification logic
        if 'response:' in text_lower:
            return 'response'
        elif 'inquiry information:' in text_lower:
            return 'inquiry'
        elif ('inquiry information:' in text_lower and 'response:' in text_lower):
            return 'example'
        elif response_matches >= 2:
            return 'response'
        elif inquiry_matches >= 3:
            return 'inquiry'
        elif response_matches > 0 and inquiry_matches > 0:
            return 'example'
        elif len(text_lower) > 200 and any(greeting in text_lower for greeting in ['good ', 'thank', 'we ', 'our ']):
            return 'response'
        elif any(marker in text_lower for marker in ['name:', 'lead created:', 'ca 9']):
            return 'inquiry'
        else:
            return 'general'
    
    def retrain_on_existing_data(self):
        """Перетренує модель на актуальних chunks з database"""
        if not ML_AVAILABLE:
            logger.warning("[ML-CLASSIFIER] ⚠️ ML not available for retraining")
            return False
        
        logger.info("[ML-CLASSIFIER] 🔄 Retraining model on existing database chunks...")
        
        # Спочатку намагаємося на existing data
        if self._train_on_existing_chunks():
            return True
        
        # Fallback на synthetic data
        logger.info("[ML-CLASSIFIER] 🎓 Using synthetic data for training...")
        self._train_on_synthetic_data()
        return True
    
    def get_model_info(self) -> dict:
        """Повертає інформацію про поточну модель"""
        if not ML_AVAILABLE:
            return {
                'ml_available': False,
                'method': 'Pattern Matching Fallback',
                'is_trained': False
            }
        
        return {
            'ml_available': True,
            'method': 'Scikit-learn TF-IDF + Logistic Regression',
            'is_trained': self.is_trained,
            'model_saved': os.path.exists(self.model_path),
            'feature_count': len(self.feature_names) if self.feature_names is not None else 0
        }
    
    def analyze_chunk_confidence(self, text: str) -> dict:
        """Аналізує confidence для всіх можливих класів"""
        if not self.is_trained or not self.model:
            return {'error': 'Model not trained'}
        
        try:
            prediction = self.model.predict([text])[0]
            probabilities = self.model.predict_proba([text])[0]
            classes = self.model.classes_
            
            confidence_by_class = {}
            for class_name, prob in zip(classes, probabilities):
                confidence_by_class[class_name] = float(prob)
            
            return {
                'predicted_class': prediction,
                'confidence_by_class': confidence_by_class,
                'max_confidence': float(max(probabilities))
            }
            
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER] Error in confidence analysis: {e}")
            return {'error': str(e)}


# Global instance
ml_chunk_classifier = MLChunkClassifier()
