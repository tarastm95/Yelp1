"""
🤖 API Views для управління ML Chunk Classifier
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class MLClassifierStatusView(APIView):
    """Статус ML classifier та модель інформація"""
    
    def get(self, request):
        """Отримати інформацію про ML classifier"""
        try:
            from .chunk_classifier_ml import ml_chunk_classifier
            
            model_info = ml_chunk_classifier.get_model_info()
            
            # Додаткова статистика по chunks
            from .vector_models import VectorChunk
            
            chunk_stats = {}
            for chunk_type in ['inquiry', 'response', 'example', 'general']:
                chunk_stats[chunk_type] = VectorChunk.objects.filter(chunk_type=chunk_type).count()
            
            return Response({
                'ml_classifier': model_info,
                'chunk_statistics': chunk_stats,
                'total_chunks': sum(chunk_stats.values())
            })
            
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER-API] Error getting status: {e}")
            return Response({
                'error': 'Failed to get ML classifier status',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MLClassifierRetrainView(APIView):
    """Перетренування ML classifier"""
    
    def post(self, request):
        """Перетренувати ML модель"""
        try:
            from .chunk_classifier_ml import ml_chunk_classifier
            
            retrain_success = ml_chunk_classifier.retrain_on_existing_data()
            
            if retrain_success:
                return Response({
                    'message': 'ML classifier retrained successfully',
                    'model_info': ml_chunk_classifier.get_model_info()
                })
            else:
                return Response({
                    'message': 'Retraining failed or used synthetic data',
                    'model_info': ml_chunk_classifier.get_model_info()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER-API] Error retraining: {e}")
            return Response({
                'error': 'Failed to retrain ML classifier',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MLClassifierTestView(APIView):
    """Тестування ML classifier на довільному тексті"""
    
    def post(self, request):
        """Класифікувати тестовий текст"""
        try:
            test_text = request.data.get('text')
            if not test_text:
                return Response({
                    'error': 'text parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from .chunk_classifier_ml import ml_chunk_classifier
            
            # Класифікація
            predicted_type = ml_chunk_classifier.classify_chunk(test_text)
            
            # Детальний аналіз confidence (якщо ML доступний)
            confidence_analysis = ml_chunk_classifier.analyze_chunk_confidence(test_text)
            
            return Response({
                'text': test_text[:200] + '...' if len(test_text) > 200 else test_text,
                'predicted_type': predicted_type,
                'confidence_analysis': confidence_analysis,
                'model_info': ml_chunk_classifier.get_model_info()
            })
            
        except Exception as e:
            logger.error(f"[ML-CLASSIFIER-API] Error in test classification: {e}")
            return Response({
                'error': 'Failed to classify test text',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HybridClassifierTestView(APIView):
    """🚀 Тестування Enterprise Hybrid Classifier"""
    
    def post(self, request):
        """Тестувати hybrid classification з повною діагностикою"""
        try:
            test_text = request.data.get('text')
            if not test_text:
                return Response({
                    'error': 'text parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from .hybrid_chunk_classifier import hybrid_classifier
            
            # Повна гібридна класифікація
            result = hybrid_classifier.classify_chunk_hybrid(test_text)
            
            return Response({
                'text_preview': test_text[:200] + '...' if len(test_text) > 200 else test_text,
                'classification': {
                    'predicted_type': result.predicted_type,
                    'confidence_score': result.confidence_score,
                    'method_used': result.method_used,
                    'rule_matches': result.rule_matches,
                    'fallback_used': result.fallback_used
                },
                'pipeline_info': hybrid_classifier.get_classification_stats()
            })
            
        except Exception as e:
            logger.error(f"[HYBRID-TEST-API] Error: {e}")
            return Response({
                'error': 'Failed to test hybrid classification',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReclassifyChunksView(APIView):
    """🔄 Перекласифікація існуючих chunks з Hybrid Classifier"""
    
    def post(self, request):
        """Перекласифікувати всі chunks для бізнесу"""
        try:
            business_id = request.data.get('business_id')
            if not business_id:
                return Response({
                    'error': 'business_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from .hybrid_chunk_classifier import hybrid_classifier
            from .vector_models import VectorChunk
            
            chunks = VectorChunk.objects.filter(document__business_id=business_id)
            
            # Статистика до
            before = {}
            for t in ['inquiry', 'response', 'example', 'general']:
                before[t] = chunks.filter(chunk_type=t).count()
            
            # Рекласифікація
            updated = 0
            methods = {}
            
            for chunk in chunks:
                old = chunk.chunk_type
                result = hybrid_classifier.classify_chunk_hybrid(chunk.content)
                new = result.predicted_type
                
                methods[result.method_used] = methods.get(result.method_used, 0) + 1
                
                if old != new:
                    chunk.chunk_type = new
                    chunk.save()
                    updated += 1
            
            # Статистика після
            after = {}
            for t in ['inquiry', 'response', 'example', 'general']:
                after[t] = chunks.filter(chunk_type=t).count()
            
            return Response({
                'message': f'Reclassified {chunks.count()} chunks',
                'updated_count': updated,
                'before': before,
                'after': after,
                'methods_used': methods
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
