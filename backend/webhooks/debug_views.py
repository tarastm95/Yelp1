"""
🔍 Debug Views для діагностики Vector Search проблем
"""

import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

logger = logging.getLogger(__name__)

class VectorDebugView(APIView):
    """🔍 Детальна діагностика Vector Search системи"""
    
    def get(self, request):
        """Повна діагностика vector search для business"""
        try:
            business_id = request.GET.get('business_id')
            if not business_id:
                return Response({'error': 'business_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .vector_models import VectorDocument, VectorChunk
            from .models import AutoResponseSettings
            from .hybrid_chunk_classifier import hybrid_classifier
            
            debug_info = {
                'business_id': business_id,
                'timestamp': str(timezone.now()),
                'diagnostics': {}
            }
            
            # 1. Перевірка документів
            documents = VectorDocument.objects.filter(business_id=business_id)
            debug_info['diagnostics']['documents'] = {
                'count': documents.count(),
                'details': []
            }
            
            for doc in documents:
                debug_info['diagnostics']['documents']['details'].append({
                    'id': doc.id,
                    'filename': doc.filename,
                    'status': doc.processing_status,
                    'chunks_count': doc.chunk_count,
                    'total_tokens': doc.total_tokens,
                    'metadata': doc.metadata
                })
            
            # 2. Перевірка chunks по типах
            chunks = VectorChunk.objects.filter(document__business_id=business_id)
            chunk_types_stats = {}
            for chunk_type in ['inquiry', 'response', 'example', 'general']:
                count = chunks.filter(chunk_type=chunk_type).count()
                chunk_types_stats[chunk_type] = count
            
            debug_info['diagnostics']['chunks'] = {
                'total_count': chunks.count(),
                'by_type': chunk_types_stats,
                'sample_chunks': []
            }
            
            # 3. Аналіз sample chunks
            for chunk in chunks[:5]:  # Перші 5 chunks
                chunk_analysis = {
                    'id': chunk.id,
                    'type': chunk.chunk_type,
                    'content_length': len(chunk.content),
                    'content_preview': chunk.content[:200],
                    'metadata': chunk.metadata,
                    'markers_detected': {
                        'inquiry_information': 'inquiry information:' in chunk.content.lower(),
                        'response_marker': 'response:' in chunk.content.lower(),
                        'name_marker': 'name:' in chunk.content.lower(),
                        'good_afternoon': 'good afternoon' in chunk.content.lower(),
                        'good_morning': 'good morning' in chunk.content.lower(),
                        'thanks_reaching': 'thanks for reaching' in chunk.content.lower(),
                        'talk_soon': 'talk soon' in chunk.content.lower()
                    }
                }
                
                # Тест класифікації цього chunk
                try:
                    classification_result = hybrid_classifier.classify_chunk_hybrid(chunk.content)
                    chunk_analysis['reclassification'] = {
                        'predicted_type': classification_result.predicted_type,
                        'confidence': classification_result.confidence_score,
                        'method_used': classification_result.method_used,
                        'rule_matches': classification_result.rule_matches
                    }
                except Exception as e:
                    chunk_analysis['reclassification'] = {'error': str(e)}
                
                debug_info['diagnostics']['chunks']['sample_chunks'].append(chunk_analysis)
            
            # 4. Перевірка settings
            try:
                settings = AutoResponseSettings.objects.filter(
                    business__business_id=business_id,
                    phone_available=False
                ).first()
                
                if settings:
                    debug_info['diagnostics']['settings'] = {
                        'use_sample_replies': settings.use_sample_replies,
                        'vector_similarity_threshold': settings.vector_similarity_threshold,
                        'vector_search_limit': settings.vector_search_limit,
                        'vector_chunk_types': settings.vector_chunk_types
                    }
                else:
                    debug_info['diagnostics']['settings'] = {'error': 'No settings found'}
                    
            except Exception as e:
                debug_info['diagnostics']['settings'] = {'error': str(e)}
            
            # 5. Тест vector search
            test_query = "Name: Beau S. Roof replacement San Fernando Valley, CA 91331"
            try:
                from .vector_search_service import vector_search_service
                
                search_results = vector_search_service.search_similar_chunks(
                    query_text=test_query,
                    business_id=business_id,
                    phone_available=False,  # Default to no phone mode for debug
                    similarity_threshold=0.4,
                    chunk_types=['response', 'example'],
                    limit=5
                )
                
                debug_info['diagnostics']['vector_search_test'] = {
                    'query': test_query,
                    'threshold': 0.4,
                    'results_count': len(search_results) if search_results else 0,
                    'results': []
                }
                
                if search_results:
                    for result in search_results[:3]:
                        debug_info['diagnostics']['vector_search_test']['results'].append({
                            'similarity_score': result['similarity_score'],
                            'chunk_type': result['chunk_type'],
                            'content_preview': result['content'][:150]
                        })
                        
            except Exception as e:
                debug_info['diagnostics']['vector_search_test'] = {'error': str(e)}
            
            # 6. Classifier info
            try:
                debug_info['diagnostics']['classifier'] = hybrid_classifier.get_classification_stats()
            except Exception as e:
                debug_info['diagnostics']['classifier'] = {'error': str(e)}
            
            return Response(debug_info)
            
        except Exception as e:
            logger.error(f"[DEBUG-VIEW] Error in vector debug: {e}")
            return Response({
                'error': 'Debug failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChunkAnalysisView(APIView):
    """🔬 Детальний аналіз конкретного chunk"""
    
    def post(self, request):
        """Аналізує текст так само як система"""
        try:
            text = request.data.get('text')
            if not text:
                return Response({'error': 'text parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .hybrid_chunk_classifier import hybrid_classifier
            
            # 1. Базовий аналіз
            analysis = {
                'input_text': text,
                'text_length': len(text),
                'text_preview': text[:200],
                'basic_markers': {
                    'inquiry_information': 'inquiry information:' in text.lower(),
                    'response_marker': 'response:' in text.lower(),
                    'name_marker': 'name:' in text.lower(),
                    'good_afternoon': 'good afternoon' in text.lower(),
                    'good_morning': 'good morning' in text.lower(),
                    'thanks_reaching': 'thanks for reaching' in text.lower(),
                    'talk_soon': 'talk soon' in text.lower(),
                    'lead_created': 'lead created:' in text.lower()
                }
            }
            
            # 2. Гібридна класифікація
            try:
                classification_result = hybrid_classifier.classify_chunk_hybrid(text)
                analysis['hybrid_classification'] = {
                    'predicted_type': classification_result.predicted_type,
                    'confidence_score': classification_result.confidence_score,
                    'method_used': classification_result.method_used,
                    'rule_matches': classification_result.rule_matches,
                    'fallback_used': classification_result.fallback_used
                }
            except Exception as e:
                analysis['hybrid_classification'] = {'error': str(e)}
            
            # 3. Симуляція PDF parsing
            try:
                from .vector_pdf_service import VectorPDFService
                service = VectorPDFService()
                
                # Симулюємо розбиття на секції
                sections = service._split_by_sections(text)
                analysis['pdf_parsing_simulation'] = {
                    'sections_count': len(sections),
                    'sections': []
                }
                
                for i, section in enumerate(sections[:3]):  # Перші 3 секції
                    section_analysis = {
                        'section_index': i,
                        'length': len(section),
                        'content_preview': section[:150],
                        'would_classify_as': service._identify_chunk_type(section)
                    }
                    analysis['pdf_parsing_simulation']['sections'].append(section_analysis)
                    
            except Exception as e:
                analysis['pdf_parsing_simulation'] = {'error': str(e)}
            
            return Response(analysis)
            
        except Exception as e:
            return Response({
                'error': 'Analysis failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
