"""
🔗 API Views for Sample Replies Management (Режим 2: AI Generated)
Завантаження та обробка Sample Replies для AI генерації
"""

import logging
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import AutoResponseSettings, YelpBusiness
from .vector_pdf_service import vector_pdf_service
from .vector_search_service import vector_search_service

logger = logging.getLogger(__name__)

class SampleRepliesFileUploadView(APIView):
    """Завантаження PDF/text файлу з Sample Replies (Режим 2: AI Generated)"""
    
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """Завантажити та обробити файл"""
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[SAMPLE-REPLIES-API] ========== FILE UPLOAD STARTED [{timestamp}] ==========")
        logger.info(f"[SAMPLE-REPLIES-API] 🚀 MODE 2: AI Generated - Vector Processing")
        
        try:
            # Валідація обов'язкових полів
            business_id = request.data.get('business_id')
            phone_available = request.data.get('phone_available', 'false').lower() == 'true'
            uploaded_file = request.FILES.get('file')
            
            if not business_id:
                return Response({
                    'error': 'business_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not uploaded_file:
                return Response({
                    'error': 'file is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"[SAMPLE-REPLIES-API] Processing file: {uploaded_file.name}")
            logger.info(f"[SAMPLE-REPLIES-API] File size: {uploaded_file.size} bytes ({uploaded_file.size / (1024*1024):.2f} MB)")
            logger.info(f"[SAMPLE-REPLIES-API] File type: {uploaded_file.content_type}")
            logger.info(f"[SAMPLE-REPLIES-API] Business: {business_id}")
            logger.info(f"[SAMPLE-REPLIES-API] Phone Available: {phone_available}")
            
            # Перевіримо поточні налаштування бізнесу ПЕРЕД обробкою
            existing_settings = AutoResponseSettings.objects.filter(
                business__business_id=business_id,
                phone_available=phone_available
            ).first()
            
            if existing_settings:
                logger.info(f"[SAMPLE-REPLIES-API] 📋 Existing settings found:")
                logger.info(f"[SAMPLE-REPLIES-API]   - AI mode: {existing_settings.use_ai_greeting}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Sample replies: {existing_settings.use_sample_replies}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Current filename: {existing_settings.sample_replies_filename}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Content length: {len(existing_settings.sample_replies_content or '')}")
            else:
                logger.info(f"[SAMPLE-REPLIES-API] 📋 No existing settings found - will create new ones")
            
            # Валідація бізнесу
            try:
                business = YelpBusiness.objects.get(business_id=business_id)
                logger.info(f"[SAMPLE-REPLIES-API] Found business: {business.name}")
            except YelpBusiness.DoesNotExist:
                return Response({
                    'error': f'Business {business_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Перевірка розміру файлу (максимум 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if uploaded_file.size > max_size:
                return Response({
                    'error': 'File too large',
                    'message': f'Maximum file size is {max_size // (1024*1024)}MB'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 🔍 VECTOR PROCESSING: Обробка файлу з семантичним чанкуванням та ембедінгами
            file_content = uploaded_file.read()
            
            # Спроба векторної обробки
            try:
                logger.info(f"[SAMPLE-REPLIES-API] 🔍 Starting vector processing...")
                
                # Асинхронна обробка PDF з векторизацією
                from asgiref.sync import async_to_sync
                process_pdf_sync = async_to_sync(vector_pdf_service.process_pdf_file)
                processing_result = process_pdf_sync(
                    file_content=file_content,
                    filename=uploaded_file.name,
                    business_id=business_id,
                    location_id=None  # TODO: Add location support
                )
                
                logger.info(f"[SAMPLE-REPLIES-API] ✅ Vector processing completed:")
                logger.info(f"[SAMPLE-REPLIES-API] - Document ID: {processing_result['document_id']}")
                logger.info(f"[SAMPLE-REPLIES-API] - Chunks: {processing_result['chunks_count']}")
                logger.info(f"[SAMPLE-REPLIES-API] - Pages: {processing_result['pages_count']}")
                logger.info(f"[SAMPLE-REPLIES-API] - Tokens: {processing_result['total_tokens']}")
                logger.info(f"[SAMPLE-REPLIES-API] - Chunk types: {processing_result['chunk_types']}")
                
                # Оновлення AutoResponseSettings для backward compatibility
                logger.info(f"[SAMPLE-REPLIES-API] 🔧 Creating/updating AutoResponseSettings...")
                auto_settings, created = AutoResponseSettings.objects.get_or_create(
                    business=business,
                    phone_available=phone_available,
                    defaults={
                        'enabled': True,
                        'use_ai_greeting': True  # Автоматично увімкнути AI режим
                    }
                )
                
                logger.info(f"[SAMPLE-REPLIES-API] 📋 AutoResponseSettings result:")
                logger.info(f"[SAMPLE-REPLIES-API]   - Created new: {created}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Settings ID: {auto_settings.id}")
                logger.info(f"[SAMPLE-REPLIES-API]   - AI mode: {auto_settings.use_ai_greeting}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Enabled: {auto_settings.enabled}")
                
                # Переконаємося що AI режим увімкнений для векторної обробки
                if not auto_settings.use_ai_greeting:
                    logger.warning(f"[SAMPLE-REPLIES-API] ⚠️ AI mode was disabled, enabling for vector processing...")
                    auto_settings.use_ai_greeting = True
                
                # Зберігаємо базову інформацію (для fallback)
                auto_settings.sample_replies_filename = uploaded_file.name
                auto_settings.use_sample_replies = True  # Автоматично увімкнути
                # sample_replies_content залишається порожнім - використовуємо векторний пошук
                auto_settings.save()
                
                logger.info(f"[SAMPLE-REPLIES-API] 💾 Settings saved successfully:")
                logger.info(f"[SAMPLE-REPLIES-API]   - Final AI mode: {auto_settings.use_ai_greeting}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Final sample replies: {auto_settings.use_sample_replies}")
                logger.info(f"[SAMPLE-REPLIES-API]   - Filename stored: {auto_settings.sample_replies_filename}")
                
                logger.info(f"[SAMPLE-REPLIES-API] ✅ VECTOR PROCESSING SUCCESS!")
                logger.info(f"[SAMPLE-REPLIES-API] 🎉 File '{uploaded_file.name}' processed with {processing_result['chunks_count']} chunks")
                
                return Response({
                    'message': 'Sample replies uploaded and processed with vector embeddings successfully',
                    'filename': uploaded_file.name,
                    'document_id': processing_result['document_id'],
                    'chunks_count': processing_result['chunks_count'],
                    'pages_count': processing_result['pages_count'],
                    'total_tokens': processing_result['total_tokens'],
                    'chunk_types': processing_result['chunk_types'],
                    'mode': 'AI Generated (Mode 2) - Vector Enhanced',
                    'vector_search_enabled': True,
                    'auto_enabled': True
                }, status=status.HTTP_201_CREATED)
                
            except Exception as vector_error:
                logger.error(f"[SAMPLE-REPLIES-API] ❌ VECTOR PROCESSING FAILED!")
                logger.error(f"[SAMPLE-REPLIES-API] Error type: {type(vector_error).__name__}")
                logger.error(f"[SAMPLE-REPLIES-API] Error message: {vector_error}")
                logger.error(f"[SAMPLE-REPLIES-API] File details: {uploaded_file.name}, {uploaded_file.size} bytes")
                logger.exception("[SAMPLE-REPLIES-API] Full error traceback:")
                logger.warning("[SAMPLE-REPLIES-API] 🔄 Falling back to simple text processing...")
                
                # 📄 FALLBACK: Простий парсинг якщо векторна обробка не вдалася
                extracted_text = vector_pdf_service.extract_text_from_uploaded_file(
                    file_content, uploaded_file.name
                )
                
                # Обробка помилок парсингу
                if extracted_text in ["PDF_BINARY_DETECTED", "PDF_BINARY_DETECTED_NO_PARSER"]:
                    return Response({
                        'error': 'PDF binary detected',
                        'message': 'Binary PDF files require additional libraries. Please copy text from PDF and use "Paste Text" option instead.',
                        'instruction': 'Open your PDF, select all text (Ctrl+A), copy (Ctrl+C), and paste into the text area.',
                        'vector_processing_failed': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if extracted_text == "EMPTY_FILE":
                    return Response({
                        'error': 'Empty file',
                        'message': 'The uploaded file appears to be empty.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if extracted_text in ["ENCODING_ERROR", "PROCESSING_ERROR"]:
                    return Response({
                        'error': 'Processing error',
                        'message': 'Failed to process file. Please try copying and pasting the text content instead.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Форматування та валідація контенту
                formatted_content = vector_pdf_service.format_sample_replies(extracted_text)
                
                if formatted_content == "EMPTY_CONTENT":
                    return Response({
                        'error': 'Empty content',
                        'message': 'File content is empty after processing.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Валідація Sample Replies контенту
                is_valid, validation_error = vector_pdf_service.validate_sample_replies_content(formatted_content)
                
                if not is_valid:
                    return Response({
                        'error': 'Invalid content',
                        'message': validation_error
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Збереження як fallback метод
                auto_settings, created = AutoResponseSettings.objects.get_or_create(
                    business=business,
                    phone_available=phone_available,
                    defaults={
                        'enabled': True,
                        'use_ai_greeting': True
                    }
                )
                
                auto_settings.sample_replies_content = formatted_content  # Legacy fallback
                auto_settings.sample_replies_filename = uploaded_file.name
                auto_settings.use_sample_replies = True
                auto_settings.save()
                
                logger.warning(f"[SAMPLE-REPLIES-API] ⚠️ FALLBACK MODE SUCCESS:")
                logger.warning(f"[SAMPLE-REPLIES-API]   - File stored in legacy mode: {uploaded_file.name}")
                logger.warning(f"[SAMPLE-REPLIES-API]   - Content length: {len(formatted_content)} characters")
                logger.warning(f"[SAMPLE-REPLIES-API]   - AI mode: {auto_settings.use_ai_greeting}")
                logger.warning(f"[SAMPLE-REPLIES-API]   - Vector search: DISABLED due to processing failure")
                
                return Response({
                    'message': 'Sample replies uploaded (fallback mode - vector processing failed)',
                    'filename': uploaded_file.name,
                    'content_length': len(formatted_content),
                    'preview': formatted_content[:300] + '...' if len(formatted_content) > 300 else formatted_content,
                    'mode': 'AI Generated (Mode 2) - Legacy Fallback',
                    'vector_search_enabled': False,
                    'vector_error': str(vector_error)
                }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"[SAMPLE-REPLIES-API] 🔥 CRITICAL UPLOAD ERROR!")
            logger.error(f"[SAMPLE-REPLIES-API] Error type: {type(e).__name__}")
            logger.error(f"[SAMPLE-REPLIES-API] Error message: {e}")
            if 'uploaded_file' in locals():
                logger.error(f"[SAMPLE-REPLIES-API] File context: {uploaded_file.name if uploaded_file else 'N/A'}")
            if 'business_id' in locals():
                logger.error(f"[SAMPLE-REPLIES-API] Business context: {business_id}")
            logger.exception("[SAMPLE-REPLIES-API] Full error traceback:")
            
            return Response({
                'error': 'Upload failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SampleRepliesTextSaveView(APIView):
    """Збереження Sample Replies як текст (ручний ввід) для режиму AI Generated"""
    
    def post(self, request):
        """Зберегти Sample Replies текст"""
        
        logger.info("[SAMPLE-REPLIES-API] ========== TEXT SAVE (Mode 2: AI Generated) ==========")
        
        try:
            business_id = request.data.get('business_id')
            phone_available = request.data.get('phone_available', 'false').lower() == 'true'
            sample_text = request.data.get('sample_text', '').strip()
            
            logger.info(f"[SAMPLE-REPLIES-API] Business: {business_id}")
            logger.info(f"[SAMPLE-REPLIES-API] Phone Available: {phone_available}")
            logger.info(f"[SAMPLE-REPLIES-API] Text length: {len(sample_text)} chars")
            
            if not business_id or not sample_text:
                return Response({
                    'error': 'business_id and sample_text are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Валідація бізнесу
            try:
                business = YelpBusiness.objects.get(business_id=business_id)
                logger.info(f"[SAMPLE-REPLIES-API] Found business: {business.name}")
            except YelpBusiness.DoesNotExist:
                return Response({
                    'error': f'Business {business_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 🔍 VECTOR PROCESSING: Обробка тексту з семантичним чанкуванням та ембедінгами
            
            # Спроба векторної обробки
            try:
                logger.info(f"[SAMPLE-REPLIES-API] 🔍 Starting vector processing for text input...")
                
                # Асинхронна обробка тексту з векторизацією
                from asgiref.sync import async_to_sync
                process_pdf_sync = async_to_sync(vector_pdf_service.process_pdf_file)
                processing_result = process_pdf_sync(
                    file_content=sample_text.encode('utf-8'),
                    filename="Manual_Text_Input.txt",
                    business_id=business_id,
                    location_id=None
                )
                
                logger.info(f"[SAMPLE-REPLIES-API] ✅ Vector processing completed for text input:")
                logger.info(f"[SAMPLE-REPLIES-API] - Document ID: {processing_result['document_id']}")
                logger.info(f"[SAMPLE-REPLIES-API] - Chunks: {processing_result['chunks_count']}")
                logger.info(f"[SAMPLE-REPLIES-API] - Tokens: {processing_result['total_tokens']}")
                
                # Оновлення AutoResponseSettings
                auto_settings, created = AutoResponseSettings.objects.get_or_create(
                    business=business,
                    phone_available=phone_available,
                    defaults={
                        'enabled': True,
                        'use_ai_greeting': True
                    }
                )
                
                auto_settings.sample_replies_filename = "Manual Text Input (Vector Enhanced)"
                auto_settings.use_sample_replies = True
                # sample_replies_content залишається порожнім - використовуємо векторний пошук
                auto_settings.save()
                
                return Response({
                    'message': 'Sample replies text processed with vector embeddings successfully',
                    'document_id': processing_result['document_id'],
                    'chunks_count': processing_result['chunks_count'],
                    'total_tokens': processing_result['total_tokens'],
                    'chunk_types': processing_result['chunk_types'],
                    'mode': 'AI Generated (Mode 2) - Vector Enhanced',
                    'vector_search_enabled': True,
                    'source': 'Manual Input'
                })
                
            except Exception as vector_error:
                logger.error(f"[SAMPLE-REPLIES-API] Vector processing failed for text: {vector_error}")
                logger.warning("[SAMPLE-REPLIES-API] Falling back to simple text processing...")
                
                # 📄 FALLBACK: Простий парсинг якщо векторна обробка не вдалася
                formatted_content = vector_pdf_service.format_sample_replies(sample_text)
                
                if formatted_content == "EMPTY_CONTENT":
                    return Response({
                        'error': 'Empty content',
                        'message': 'Text content is empty after processing.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Валідація контенту
                is_valid, validation_error = vector_pdf_service.validate_sample_replies_content(formatted_content)
                
                if not is_valid:
                    return Response({
                        'error': 'Invalid content',
                        'message': validation_error
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Збереження як fallback метод
                auto_settings, created = AutoResponseSettings.objects.get_or_create(
                    business=business,
                    phone_available=phone_available,
                    defaults={
                        'enabled': True,
                        'use_ai_greeting': True
                    }
                )
                
                auto_settings.sample_replies_content = formatted_content  # Legacy fallback
                auto_settings.sample_replies_filename = "Manual Text Input (Legacy)"
                auto_settings.use_sample_replies = True
                auto_settings.save()
                
                return Response({
                    'message': 'Sample replies text saved (fallback mode - vector processing failed)',
                    'content_length': len(formatted_content),
                    'preview': formatted_content[:300] + '...' if len(formatted_content) > 300 else formatted_content,
                    'mode': 'AI Generated (Mode 2) - Legacy Fallback',
                    'vector_search_enabled': False,
                    'vector_error': str(vector_error),
                    'source': 'Manual Input'
                })
            
        except Exception as e:
            logger.error(f"[SAMPLE-REPLIES-API] Text save error: {e}")
            logger.exception("Text save error details")
            return Response({
                'error': 'Save failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SampleRepliesStatusView(APIView):
    """Перевірити статус Sample Replies для бізнесу"""
    
    def get(self, request):
        """Отримати статус Sample Replies"""
        
        logger.info(f"[SAMPLE-REPLIES-STATUS] ========== STATUS CHECK REQUEST ==========")
        
        business_id = request.GET.get('business_id')
        phone_available = request.GET.get('phone_available', 'false').lower() == 'true'
        
        logger.info(f"[SAMPLE-REPLIES-STATUS] Business ID: {business_id}")
        logger.info(f"[SAMPLE-REPLIES-STATUS] Phone Available: {phone_available}")
        
        if not business_id:
            logger.error(f"[SAMPLE-REPLIES-STATUS] ❌ Missing business_id parameter")
            return Response({
                'error': 'business_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            business = YelpBusiness.objects.get(business_id=business_id)
            logger.info(f"[SAMPLE-REPLIES-STATUS] ✅ Business found: {business.name}")
        except YelpBusiness.DoesNotExist:
            logger.error(f"[SAMPLE-REPLIES-STATUS] ❌ Business not found: {business_id}")
            return Response({
                'error': f'Business {business_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            auto_settings = AutoResponseSettings.objects.get(
                business=business,
                phone_available=phone_available
            )
            
            logger.info(f"[SAMPLE-REPLIES-STATUS] 📋 AutoResponseSettings found:")
            logger.info(f"[SAMPLE-REPLIES-STATUS]   - AI mode: {auto_settings.use_ai_greeting}")
            logger.info(f"[SAMPLE-REPLIES-STATUS]   - Use sample replies: {auto_settings.use_sample_replies}")
            logger.info(f"[SAMPLE-REPLIES-STATUS]   - Filename: {auto_settings.sample_replies_filename}")
            logger.info(f"[SAMPLE-REPLIES-STATUS]   - Content length: {len(auto_settings.sample_replies_content or '')}")
            
            has_sample_replies = bool(
                auto_settings.use_sample_replies and 
                auto_settings.sample_replies_content
            )
            
            # 🔍 Перевіряємо vector документи для детального статусу
            logger.info(f"[SAMPLE-REPLIES-STATUS] 🔍 Checking vector documents...")
            from .vector_models import VectorDocument, VectorChunk
            
            vector_documents = VectorDocument.objects.filter(
                business_id=business_id
            ).order_by('-created_at')
            
            vector_status = {
                'total_documents': vector_documents.count(),
                'completed_documents': vector_documents.filter(processing_status='completed').count(),
                'processing_documents': vector_documents.filter(processing_status='processing').count(),
                'error_documents': vector_documents.filter(processing_status='error').count(),
                'total_chunks': VectorChunk.objects.filter(document__business_id=business_id).count(),
                'documents': []
            }
            
            # Детальна інформація про кожен документ
            for doc in vector_documents[:10]:  # Останні 10 документів
                chunks_count = doc.chunks.count()
                vector_status['documents'].append({
                    'id': doc.id,
                    'filename': doc.filename,
                    'status': doc.processing_status,
                    'chunks_count': chunks_count,
                    'page_count': doc.page_count,
                    'total_tokens': doc.total_tokens,
                    'file_size': doc.file_size,
                    'created_at': doc.created_at.isoformat(),
                    'updated_at': doc.updated_at.isoformat(),
                    'error_message': doc.error_message,
                    'embedding_model': doc.embedding_model,
                    'has_vector_data': chunks_count > 0
                })
            
            return Response({
                'business_name': business.name,
                'has_sample_replies': has_sample_replies,
                'use_sample_replies': auto_settings.use_sample_replies,
                'filename': auto_settings.sample_replies_filename,
                'content_length': len(auto_settings.sample_replies_content) if auto_settings.sample_replies_content else 0,
                'priority': auto_settings.sample_replies_priority,
                'ai_mode_enabled': auto_settings.use_ai_greeting,
                'mode': 'AI Generated (Mode 2)' if auto_settings.use_ai_greeting else 'Template (Mode 1)',
                'vector_status': vector_status,
                'vector_search_available': vector_status['total_chunks'] > 0
            })
            
        except AutoResponseSettings.DoesNotExist:
            # 🔍 Навіть якщо немає налаштувань, перевіряємо vector документи
            from .vector_models import VectorDocument, VectorChunk
            
            vector_documents = VectorDocument.objects.filter(
                business_id=business_id
            ).order_by('-created_at')
            
            vector_status = {
                'total_documents': vector_documents.count(),
                'completed_documents': vector_documents.filter(processing_status='completed').count(),
                'processing_documents': vector_documents.filter(processing_status='processing').count(),
                'error_documents': vector_documents.filter(processing_status='error').count(),
                'total_chunks': VectorChunk.objects.filter(document__business_id=business_id).count(),
                'documents': []
            }
            
            # Детальна інформація про кожен документ
            for doc in vector_documents[:10]:
                chunks_count = doc.chunks.count()
                vector_status['documents'].append({
                    'id': doc.id,
                    'filename': doc.filename,
                    'status': doc.processing_status,
                    'chunks_count': chunks_count,
                    'page_count': doc.page_count,
                    'total_tokens': doc.total_tokens,
                    'file_size': doc.file_size,
                    'created_at': doc.created_at.isoformat(),
                    'updated_at': doc.updated_at.isoformat(),
                    'error_message': doc.error_message,
                    'embedding_model': doc.embedding_model,
                    'has_vector_data': chunks_count > 0
                })
            
            return Response({
                'business_name': business.name,
                'has_sample_replies': False,
                'use_sample_replies': False,
                'filename': None,
                'content_length': 0,
                'priority': True,
                'ai_mode_enabled': False,
                'mode': 'Not configured',
                'vector_status': vector_status,
                'vector_search_available': vector_status['total_chunks'] > 0
            })


class VectorSearchTestView(APIView):
    """Тестування векторного пошуку для діагностики"""
    
    def post(self, request):
        """Виконати тестовий векторний пошук"""
        
        try:
            business_id = request.data.get('business_id')
            test_query = request.data.get('test_query', 'roof repair service inquiry')
            location_id = request.data.get('location_id', None)
            
            if not business_id:
                return Response({
                    'error': 'business_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"[VECTOR-TEST-API] Testing vector search for business {business_id}")
            
            # Виконання тестового пошуку
            test_result = vector_search_service.test_vector_search(
                business_id=business_id,
                test_query=test_query,
                location_id=location_id
            )
            
            return Response(test_result)
            
        except Exception as e:
            logger.error(f"[VECTOR-TEST-API] Test error: {e}")
            return Response({
                'success': False,
                'error': 'Test failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VectorChunkListView(APIView):
    """Список векторних чанків для діагностики"""
    
    def get(self, request):
        """Отримати список чанків"""
        
        business_id = request.GET.get('business_id')
        location_id = request.GET.get('location_id', None)
        chunk_type = request.GET.get('chunk_type', None)
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        if not business_id:
            return Response({
                'error': 'business_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .vector_models import VectorDocument, VectorChunk
            from django.db.models import Q
            
            # Фільтри документів
            doc_filter = Q(business_id=business_id, processing_status='completed')
            if location_id:
                doc_filter &= Q(location_id=location_id)
            
            documents = VectorDocument.objects.filter(doc_filter)
            
            if not documents.exists():
                return Response({
                    'chunks': [],
                    'total': 0,
                    'message': 'No vector documents found for this business'
                })
            
            # Фільтри чанків
            chunk_filter = Q(document__in=documents)
            if chunk_type:
                chunk_filter &= Q(chunk_type=chunk_type)
            
            chunks = VectorChunk.objects.filter(chunk_filter).select_related('document')[:limit]
            
            chunks_data = []
            for chunk in chunks:
                chunks_data.append({
                    'id': chunk.id,
                    'content': chunk.get_preview(200),
                    'full_content': chunk.content,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    'token_count': chunk.token_count,
                    'chunk_type': chunk.chunk_type,
                    'metadata': chunk.metadata,
                    'document_filename': chunk.document.filename,
                    'created_at': chunk.created_at.isoformat(),
                    'has_embedding': chunk.similarity_search_ready
                })
            
            # Статистика
            stats = vector_search_service.get_chunk_statistics(business_id, location_id)
            
            return Response({
                'chunks': chunks_data,
                'total': len(chunks_data),
                'limit': limit,
                'statistics': stats,
                'filters': {
                    'business_id': business_id,
                    'location_id': location_id,
                    'chunk_type': chunk_type
                }
            })
            
        except Exception as e:
            logger.error(f"[VECTOR-CHUNKS-API] Error: {e}")
            return Response({
                'error': 'Failed to load chunks',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
