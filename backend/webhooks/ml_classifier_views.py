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
