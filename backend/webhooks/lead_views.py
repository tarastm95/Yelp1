import logging
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import generics, mixins, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from .models import (
    Event,
    ProcessedLead,
    AutoResponseSettings,
    YelpBusiness,
    LeadDetail,
    FollowUpTemplate,
    JobMapping,
    YelpToken,
    LeadEvent,
    NotificationSetting,
    AISettings,
    TimeBasedGreeting,
)
from .pagination import FivePerPagePagination
from .serializers import (
    EventSerializer,
    AutoResponseSettingsSerializer,
    ProcessedLeadSerializer,
    LeadDetailSerializer,
    FollowUpTemplateSerializer,
    JobMappingSerializer,
    YelpTokenInfoSerializer,
    LeadEventSerializer,
    NotificationSettingSerializer,
    AISettingsSerializer,
    AIGlobalSettingsSerializer,
    TimeBasedGreetingSerializer,
)
from .ai_service import OpenAIService

logger = logging.getLogger(__name__)


class EventListView(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = Event.objects.all().order_by("-id")
    serializer_class = EventSerializer
    pagination_class = FivePerPagePagination

    def get(self, request, *args, **kwargs):
        after_id = request.query_params.get("after_id")
        logger.info(
            f"[EVENT LIST] GET after_id={after_id} path={request.path}"
        )
        if after_id is not None:
            qs = self.get_queryset().filter(id__gt=after_id).order_by("id")
            serializer = self.get_serializer(qs, many=True)
            logger.info(
                f"[EVENT LIST] returning {len(serializer.data)} events after_id={after_id}"
            )
            return Response(serializer.data)
        response = self.list(request, *args, **kwargs)
        logger.info(
            f"[EVENT LIST] paginated response with {len(response.data.get('results', []))} events"
        )
        return response


class EventRetrieveView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class AutoResponseSettingsView(APIView):
    def _get_default_settings(self, phone_opt_in: bool, phone_available: bool):
        obj = AutoResponseSettings.objects.filter(
            business=None,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available,
        ).first()
        if obj:
            return obj
        return AutoResponseSettings.objects.create(
            business=None,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available,
        )

    def _get_settings_for_business(self, business_id: str | None, phone_opt_in: bool, phone_available: bool):
        qs = AutoResponseSettings.objects.filter(phone_opt_in=phone_opt_in, phone_available=phone_available)
        if business_id:
            obj = qs.filter(business__business_id=business_id).first()
            if obj:
                return obj
            biz = YelpBusiness.objects.filter(business_id=business_id).first()
            return AutoResponseSettings(
                business=biz,
                phone_opt_in=phone_opt_in,
                phone_available=phone_available,
                enabled=False,
                greeting_template='',
                greeting_off_hours_template='',
                greeting_delay=0,
                # 🤖 AI Settings with proper defaults
                use_ai_greeting=False,
                ai_response_style='auto',
                ai_include_location=False,
                ai_mention_response_time=False,
                ai_custom_prompt='',
                # 📊 AI Business Data Settings
                ai_include_rating=True,
                ai_include_categories=True,
                ai_include_phone=True,
                ai_include_website=False,
                ai_include_price_range=True,
                ai_include_hours=True,
                ai_include_reviews_count=True,
                ai_include_address=False,
                ai_include_transactions=False,
                ai_max_message_length=160,  # 🎯 Ось тут проблема!
                # 🤖 Business-specific AI Model Settings
                ai_model='',  # Empty = use global
                ai_temperature=None,  # None = use global
                # 📱 SMS Settings
                sms_on_phone_found=True,
                sms_on_customer_reply=True,
                sms_on_phone_opt_in=True,
            )
        return self._get_default_settings(phone_opt_in, phone_available)

    def get(self, request, *args, **kwargs):
        bid = request.query_params.get('business_id')
        phone_opt_in = request.query_params.get('phone_opt_in') == 'true'
        phone_available = request.query_params.get('phone_available') == 'true'
        obj = self._get_settings_for_business(bid, phone_opt_in, phone_available)
        serializer = AutoResponseSettingsSerializer(obj)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        bid = request.query_params.get('business_id')
        phone_opt_in = request.query_params.get('phone_opt_in') == 'true'
        phone_available = request.query_params.get('phone_available') == 'true'
        if bid:
            business = YelpBusiness.objects.filter(business_id=bid).first()
            obj, _ = AutoResponseSettings.objects.get_or_create(
                business=business, phone_opt_in=phone_opt_in, phone_available=phone_available
            )
        else:
            obj = self._get_default_settings(phone_opt_in, phone_available)
        serializer = AutoResponseSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    post = put


class ProcessedLeadListView(generics.ListAPIView):
    serializer_class = ProcessedLeadSerializer
    pagination_class = FivePerPagePagination

    def get_queryset(self):
        qs = ProcessedLead.objects.select_related().order_by("-processed_at")
        bid = self.request.query_params.get("business_id")
        if bid:
            qs = qs.filter(business_id=bid)
        return qs


class LeadEventListAPIView(mixins.ListModelMixin, generics.GenericAPIView):
    serializer_class = LeadEventSerializer
    pagination_class = FivePerPagePagination

    def get_queryset(self):
        qs = LeadEvent.objects.all().order_by("-id")
        bid = self.request.query_params.get("business_id")
        if bid:
            lead_ids = (
                LeadDetail.objects
                .filter(business_id=bid)
                .values_list("lead_id", flat=True)
            )
            qs = qs.filter(lead_id__in=lead_ids)
        return qs

    def get(self, request, *args, **kwargs):
        after_id = request.query_params.get("after_id")
        logger.info(
            f"[LEAD EVENT LIST] GET after_id={after_id} path={request.path}"
        )
        if after_id is not None:
            qs = self.get_queryset().filter(id__gt=after_id).order_by("id")
            serializer = self.get_serializer(qs, many=True)
            logger.info(
                f"[LEAD EVENT LIST] returning {len(serializer.data)} events after_id={after_id}"
            )
            return Response(serializer.data)
        response = self.list(request, *args, **kwargs)
        logger.info(
            f"[LEAD EVENT LIST] paginated response with {len(response.data.get('results', []))} events"
        )
        return response


class LeadDetailListAPIView(APIView):
    """Return list of all LeadDetail records"""

    def get(self, request):
        queryset = LeadDetail.objects.all()
        serializer = LeadDetailSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadDetailRetrieveAPIView(APIView):
    """Return single LeadDetail by lead_id"""

    def get_object(self, lead_id: str) -> LeadDetail:
        logger.info(f"[LEAD DETAIL] Fetching lead_id={lead_id}")
        try:
            obj = LeadDetail.objects.get(lead_id=lead_id)
            logger.info(f"[LEAD DETAIL] Found LeadDetail pk={obj.pk}")
            return obj
        except LeadDetail.DoesNotExist:
            logger.info(f"[LEAD DETAIL] LeadDetail with lead_id={lead_id} not found")
            raise NotFound(detail=f"LeadDetail з lead_id={lead_id} не знайдено")

    def get(self, request, lead_id: str):
        obj = self.get_object(lead_id)
        serializer = LeadDetailSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadLastEventAPIView(APIView):
    """Return latest LeadEvent by lead_id"""

    def get(self, request, lead_id: str):
        logger.info(
            f"[LEAD LAST EVENT] Fetching latest event for lead_id={lead_id} path={request.path}"
        )
        obj = (
            LeadEvent.objects.filter(lead_id=lead_id)
            .order_by("-time_created")
            .first()
        )
        if not obj:
            logger.info(
                f"[LEAD LAST EVENT] LeadEvent with lead_id={lead_id} not found"
            )
            raise NotFound(detail=f"LeadEvent з lead_id={lead_id} не знайдено")
        serializer = LeadEventSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadEventRetrieveAPIView(APIView):
    """Return LeadEvent by event_id"""

    def get(self, request, event_id: str):
        obj = LeadEvent.objects.filter(event_id=event_id).first()
        if not obj:
            raise NotFound(detail=f"LeadEvent з event_id={event_id} не знайдено")
        serializer = LeadEventSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowUpTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = FollowUpTemplateSerializer

    def get_queryset(self):
        bid = self.request.query_params.get('business_id')
        phone_opt_in = self.request.query_params.get('phone_opt_in') == 'true'
        phone_available = self.request.query_params.get('phone_available') == 'true'
        qs = FollowUpTemplate.objects.filter(phone_opt_in=phone_opt_in, phone_available=phone_available)
        if bid:
            return qs.filter(Q(business__business_id=bid) | Q(business__isnull=True))
        return qs.filter(business__isnull=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"[FollowUpTemplate] validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        bid = request.query_params.get('business_id')
        phone_opt_in = request.query_params.get('phone_opt_in') == 'true'
        phone_available = request.query_params.get('phone_available') == 'true'
        business = YelpBusiness.objects.filter(business_id=bid).first() if bid else None
        serializer.save(business=business, phone_opt_in=phone_opt_in, phone_available=phone_available)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class FollowUpTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FollowUpTemplateSerializer

    def get_queryset(self):
        bid = self.request.query_params.get('business_id')
        phone_opt_in = self.request.query_params.get('phone_opt_in') == 'true'
        phone_available = self.request.query_params.get('phone_available') == 'true'
        qs = FollowUpTemplate.objects.filter(phone_opt_in=phone_opt_in, phone_available=phone_available)
        if bid:
            return qs.filter(Q(business__business_id=bid) | Q(business__isnull=True))
        return qs.filter(business__isnull=True)

    def perform_update(self, serializer):
        bid = self.request.query_params.get('business_id')
        phone_opt_in = self.request.query_params.get('phone_opt_in') == 'true'
        phone_available = self.request.query_params.get('phone_available') == 'true'
        business = YelpBusiness.objects.filter(business_id=bid).first() if bid else None
        serializer.save(business=business, phone_opt_in=phone_opt_in, phone_available=phone_available)


class YelpTokenListView(generics.ListAPIView):
    serializer_class = YelpTokenInfoSerializer

    def get_queryset(self):
        return YelpToken.objects.all().order_by('business_id')


class NotificationSettingListCreateView(generics.ListCreateAPIView):
    """List all notification settings or create a new one."""

    serializer_class = NotificationSettingSerializer

    def get_queryset(self):
        bid = self.request.query_params.get("business_id")
        qs = NotificationSetting.objects.all().order_by("id")
        if bid:
            return qs.filter(business__business_id=bid)
        # No global settings support - return empty queryset
        return qs.none()

    def create(self, request, *args, **kwargs):
        phone = request.data.get("phone_number", "")
        bid = request.query_params.get("business_id")
        
        # Require business_id for all SMS notifications
        if not bid:
            return Response(
                {"detail": "business_id parameter is required. Global SMS settings are not supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        business = YelpBusiness.objects.filter(business_id=bid).first()
        if not business:
            return Response(
                {"detail": f"Business with id {bid} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
            
        if NotificationSetting.objects.filter(phone_number=phone, business=business).exists():
            return Response(
                {"detail": "Phone number already exists for this business."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(business=business)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class NotificationSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific notification setting."""

    serializer_class = NotificationSettingSerializer

    def get_queryset(self):
        bid = self.request.query_params.get("business_id")
        qs = NotificationSetting.objects.all()
        if bid:
            return qs.filter(business__business_id=bid)
        # No global settings support - return empty queryset
        return qs.none()

    def perform_update(self, serializer):
        bid = self.request.query_params.get("business_id")
        if not bid:
            raise ValidationError("business_id parameter is required. Global SMS settings are not supported.")
        business = YelpBusiness.objects.filter(business_id=bid).first()
        if not business:
            raise ValidationError(f"Business with id {bid} not found")
        serializer.save(business=business)


class BusinessSMSSettingsView(APIView):
    """Get and update SMS notification settings for a specific business."""

    def get(self, request, *args, **kwargs):
        """Get SMS notification status for a business."""
        logger.info(f"[NOTIFICATION-SETTINGS] 📋 GET SMS settings request")
        logger.info(f"[NOTIFICATION-SETTINGS] Query params: {request.query_params}")
        
        bid = request.query_params.get('business_id')
        logger.info(f"[NOTIFICATION-SETTINGS] Business ID: {bid}")
        
        if not bid:
            logger.error(f"[NOTIFICATION-SETTINGS] ❌ Missing business_id parameter")
            return Response(
                {"detail": "business_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"[NOTIFICATION-SETTINGS] 🔍 Looking up business: {bid}")
        business = YelpBusiness.objects.filter(business_id=bid).first()
        
        if not business:
            logger.error(f"[NOTIFICATION-SETTINGS] ❌ Business not found: {bid}")
            return Response(
                {"detail": f"Business with id {bid} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"[NOTIFICATION-SETTINGS] ✅ Business found: {business.name}")
        logger.info(f"[NOTIFICATION-SETTINGS] SMS notifications enabled: {business.sms_notifications_enabled}")
        
        data = {
            "business_id": business.business_id,
            "business_name": business.name,
            "sms_notifications_enabled": business.sms_notifications_enabled
        }
        
        logger.info(f"[NOTIFICATION-SETTINGS] 📤 Returning data: {data}")
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """Update SMS notification status for a business."""
        logger.info(f"[NOTIFICATION-SETTINGS] 🔄 PUT SMS settings request")
        logger.info(f"[NOTIFICATION-SETTINGS] Query params: {request.query_params}")
        logger.info(f"[NOTIFICATION-SETTINGS] Request data: {request.data}")
        
        bid = request.query_params.get('business_id')
        logger.info(f"[NOTIFICATION-SETTINGS] Business ID: {bid}")
        
        if not bid:
            logger.error(f"[NOTIFICATION-SETTINGS] ❌ Missing business_id parameter")
            return Response(
                {"detail": "business_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"[NOTIFICATION-SETTINGS] 🔍 Looking up business: {bid}")
        business = YelpBusiness.objects.filter(business_id=bid).first()
        
        if not business:
            logger.error(f"[NOTIFICATION-SETTINGS] ❌ Business not found: {bid}")
            return Response(
                {"detail": f"Business with id {bid} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"[NOTIFICATION-SETTINGS] ✅ Business found: {business.name}")
        logger.info(f"[NOTIFICATION-SETTINGS] Current SMS status: {business.sms_notifications_enabled}")
        
        # Extract new status from request
        new_status = request.data.get('sms_notifications_enabled')
        logger.info(f"[NOTIFICATION-SETTINGS] 📝 New SMS status from request: {new_status}")
        
        if new_status is None:
            logger.error(f"[NOTIFICATION-SETTINGS] ❌ Missing sms_notifications_enabled in request data")
            return Response(
                {"detail": "sms_notifications_enabled field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(new_status, bool):
            logger.error(f"[NOTIFICATION-SETTINGS] ❌ Invalid sms_notifications_enabled value: {new_status} (type: {type(new_status)})")
            return Response(
                {"detail": "sms_notifications_enabled must be a boolean value"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"[NOTIFICATION-SETTINGS] 💾 Updating SMS status: {business.sms_notifications_enabled} → {new_status}")
        
        # Update the business
        business.sms_notifications_enabled = new_status
        business.save(update_fields=['sms_notifications_enabled', 'updated_at'])
        
        logger.info(f"[NOTIFICATION-SETTINGS] ✅ SMS status updated successfully")
        logger.info(f"[NOTIFICATION-SETTINGS] Business: {business.name}")
        logger.info(f"[NOTIFICATION-SETTINGS] New status: {business.sms_notifications_enabled}")
        
        data = {
            "business_id": business.business_id,
            "business_name": business.name,
            "sms_notifications_enabled": business.sms_notifications_enabled
        }
        
        logger.info(f"[NOTIFICATION-SETTINGS] 📤 Returning updated data: {data}")
        return Response(data, status=status.HTTP_200_OK)


class AIPreviewView(APIView):
    """Endpoint для генерації preview AI повідомлень"""
    
    def post(self, request, *args, **kwargs):
        """Генерує preview AI повідомлення на основі наданих параметрів"""
        from .ai_service import OpenAIService
        from rest_framework import status
        from rest_framework.response import Response
        
        try:
            # Отримання business_id для отримання реальних даних
            business_id = request.data.get('business_id')
            if not business_id:
                return Response({
                    'success': False,
                    'error': 'business_id is required for generating realistic preview'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Отримуємо реальний бізнес з бази даних
            business = YelpBusiness.objects.filter(business_id=business_id).first()
            if not business:
                return Response({
                    'success': False,
                    'error': f'Business with id {business_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Отримуємо AutoResponseSettings для бізнесу (для AI налаштувань)
            business_ai_settings = AutoResponseSettings.objects.filter(
                business=business,
                phone_opt_in=False,
                phone_available=False
            ).first()
            
            # Параметри з запиту
            response_style = request.data.get('ai_response_style', 'auto')
            include_location = request.data.get('ai_include_location', False)
            mention_response_time = request.data.get('ai_mention_response_time', False)
            custom_prompt = request.data.get('ai_custom_prompt', None)
            custom_preview_text = request.data.get('custom_preview_text', None)  # 🎯 Додаємо custom preview text
            max_length = request.data.get('ai_max_message_length', None)
            
            # Отримання налаштувань бізнес-даних
            business_data_settings = {
                "include_rating": request.data.get('ai_include_rating', True),
                "include_categories": request.data.get('ai_include_categories', True),
                "include_phone": request.data.get('ai_include_phone', True),
                "include_website": request.data.get('ai_include_website', False),
                "include_price_range": request.data.get('ai_include_price_range', True),
                "include_hours": request.data.get('ai_include_hours', True),
                "include_reviews_count": request.data.get('ai_include_reviews_count', True),
                "include_address": request.data.get('ai_include_address', False),
                "include_transactions": request.data.get('ai_include_transactions', False)
            }
            
            # Ініціалізація AI сервісу
            ai_service = OpenAIService()
            
            if not ai_service.is_available():
                return Response({
                    'error': 'AI service is not available. Please check your OpenAI configuration.',
                    'preview': 'AI service unavailable - would fallback to template message.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Генерація preview повідомлення з реальними даними бізнесу
            preview_message = ai_service.generate_preview_message(
                business=business,
                response_style=response_style,
                include_location=include_location,
                mention_response_time=mention_response_time,
                custom_prompt=custom_prompt,
                business_data_settings=business_data_settings,
                max_length=max_length,
                custom_preview_text=custom_preview_text,  # 🎯 Додаємо параметр
                business_ai_settings=business_ai_settings  # 🤖 Додаємо business AI налаштування
            )
            
            return Response({
                'preview': preview_message,
                'parameters': {
                    'business_name': business.name,
                    'customer_name': '{CLIENT_NAME}',
                    'services': '{SERVICES}',
                    'ai_response_style': response_style,
                    'ai_include_location': include_location,
                    'ai_mention_response_time': mention_response_time,
                    'has_custom_prompt': bool(custom_prompt)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"[AI-PREVIEW] Error generating preview: {e}")
            return Response({
                'error': f'Error generating preview: {str(e)}',
                'preview': 'Error occurred - would fallback to template message.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIGlobalSettingsView(APIView):
    """
    Global AI Settings management endpoint
    Allows viewing and updating global AI configuration
    """
    
    def get(self, request, *args, **kwargs):
        """Отримати глобальні AI налаштування"""
        try:
            ai_settings = AISettings.objects.first()
            if not ai_settings:
                # Створити з default значеннями якщо не існує
                ai_settings = AISettings.objects.create()
            
            serializer = AIGlobalSettingsSerializer(ai_settings)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching global AI settings: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to fetch global AI settings'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, *args, **kwargs):
        """Оновити глобальні AI налаштування"""
        try:
            ai_settings = AISettings.objects.first()
            if not ai_settings:
                # Створити новий запис якщо не існує
                serializer = AIGlobalSettingsSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                ai_settings = serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Global AI settings created successfully',
                    'data': AIGlobalSettingsSerializer(ai_settings).data
                }, status=status.HTTP_201_CREATED)
            else:
                # Оновити існуючий запис
                serializer = AIGlobalSettingsSerializer(ai_settings, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                ai_settings = serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Global AI settings updated successfully',
                    'data': AIGlobalSettingsSerializer(ai_settings).data
                }, status=status.HTTP_200_OK)
                
        except ValidationError as e:
            return Response({
                'success': False,
                'error': 'Validation error',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating global AI settings: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to update global AI settings'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AITestPreviewView(APIView):
    """
    Test AI with custom global settings before saving
    """
    
    def post(self, request, *args, **kwargs):
        """Тестовий preview з глобальними налаштуваннями"""
        try:
            # Отримуємо тестові дані з request
            test_business_name = request.data.get('test_business_name', 'Test Business')
            test_customer_name = request.data.get('test_customer_name', 'John')
            test_services = request.data.get('test_services', 'kitchen remodeling')
            
            # Глобальні налаштування для тесту
            base_system_prompt = request.data.get('base_system_prompt', '')
            openai_model = request.data.get('openai_model', 'gpt-4o')
            default_temperature = request.data.get('default_temperature', 0.7)
            max_message_length = request.data.get('max_message_length', 160)
            
            # Ініціалізуємо AI service
            ai_service = OpenAIService()
            if not ai_service.is_available():
                return Response({
                    'success': False,
                    'error': 'AI service is not available. Check OpenAI API key configuration.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Тимчасово змінюємо глобальні налаштування для тесту
            original_settings = AISettings.objects.first()
            
            # Створюємо mock business object для тестування
            class MockBusiness:
                def __init__(self, name):
                    self.name = name
                    self.location = "Test Location, Test City"
                    self.time_zone = "America/New_York"
                    self.open_days = "Monday-Friday"
                    self.open_hours = "9:00 AM - 6:00 PM"
                    self.details = {
                        "rating": 4.5,
                        "review_count": 123,
                        "categories": [
                            {"title": "Home Services", "alias": "homeservices"},
                            {"title": "Contractors", "alias": "contractors"}
                        ],
                        "display_phone": "(555) 123-4567",
                        "phone": "+15551234567",
                        "url": "https://www.yelp.com/biz/test-business",
                        "price": "$$",
                        "location": {
                            "display_address": ["123 Test St", "Test City, TC 12345"],
                            "city": "Test City",
                            "state": "TC",
                            "zip_code": "12345"
                        },
                        "transactions": ["delivery", "pickup"]
                    }
            
            mock_business = MockBusiness(test_business_name)
            
            # Створюємо тестове повідомлення
            preview_message = ai_service.generate_preview_message(
                business=mock_business,
                response_style='auto',
                include_location=True,
                mention_response_time=True,
                custom_prompt=base_system_prompt if base_system_prompt else None,
                business_data_settings={
                    "include_rating": True,
                    "include_categories": True,
                    "include_phone": True,
                    "include_website": False,
                    "include_price_range": True,
                    "include_hours": True,
                    "include_reviews_count": True,
                    "include_address": False,
                    "include_transactions": False
                },
                max_length=max_message_length,
                business_ai_settings=None  # 🧪 Mock test - використовуємо global fallback
            )
            
            return Response({
                'success': True,
                'preview_message': preview_message,
                'test_data': {
                    'business_name': test_business_name,
                    'customer_name': test_customer_name,
                    'services': test_services
                },
                'settings_used': {
                    'model': openai_model,
                    'temperature': default_temperature,
                    'max_length': max_message_length,
                    'custom_prompt': bool(base_system_prompt)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating AI test preview: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to generate preview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TimeBasedGreetingView(APIView):
    """Manage time-based greetings for businesses"""

    def get(self, request):
        business_id = request.query_params.get('business_id')
        
        if business_id:
            # Get business-specific greetings
            try:
                business = YelpBusiness.objects.get(business_id=business_id)
                greeting = TimeBasedGreeting.objects.filter(business=business).first()
            except YelpBusiness.DoesNotExist:
                return Response({'error': 'Business not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get global default greetings
            greeting = TimeBasedGreeting.objects.filter(business__isnull=True).first()
        
        if greeting:
            serializer = TimeBasedGreetingSerializer(greeting)
            return Response(serializer.data)
        else:
            # Return default values if no greeting settings exist
            return Response({
                'morning_start': '05:00',
                'morning_end': '12:00',
                'afternoon_start': '12:00', 
                'afternoon_end': '17:00',
                'evening_start': '17:00',
                'evening_end': '21:00',
                'morning_greeting': 'Good morning',
                'afternoon_greeting': 'Good afternoon',
                'evening_greeting': 'Good evening',
                'night_greeting': 'Hello'
            })

    def post(self, request):
        business_id = request.data.get('business_id')
        
        if business_id:
            try:
                business = YelpBusiness.objects.get(business_id=business_id)
                greeting, created = TimeBasedGreeting.objects.get_or_create(
                    business=business,
                    defaults=request.data
                )
            except YelpBusiness.DoesNotExist:
                return Response({'error': 'Business not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Global default greetings
            greeting, created = TimeBasedGreeting.objects.get_or_create(
                business=None,
                defaults=request.data
            )
        
        if not created:
            # Update existing greeting
            serializer = TimeBasedGreetingSerializer(greeting, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = TimeBasedGreetingSerializer(greeting)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request):
        return self.post(request)


class JobMappingListCreateView(generics.ListCreateAPIView):
    """API для перегляду та створення відповідностей назв послуг"""
    serializer_class = JobMappingSerializer
    queryset = JobMapping.objects.all()

    def get_queryset(self):
        return JobMapping.objects.filter(active=True).order_by('original_name')


class JobMappingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API для перегляду, оновлення та видалення конкретної відповідності"""
    serializer_class = JobMappingSerializer
    queryset = JobMapping.objects.all()
    lookup_field = 'id'


class LeadTimeSeriesView(APIView):
    """Return Lead time-series data grouped by date."""

    def get(self, request):
        """Return Lead counts and events grouped by date."""
        logger.info(f"[LEAD-TIMESERIES] 📊 Lead Time Series API request")
        logger.info(f"[LEAD-TIMESERIES] Query params: {dict(request.query_params)}")
        
        # Parse date range
        days = int(request.query_params.get("days", 30))
        business_id = request.query_params.get("business_id")
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        logger.info(f"[LEAD-TIMESERIES] Date range: {start_date} to {end_date} ({days} days)")
        
        # Query ProcessedLeads (leads processed by date)
        processed_leads_qs = ProcessedLead.objects.filter(
            processed_at__date__gte=start_date,
            processed_at__date__lte=end_date
        )
        
        if business_id:
            logger.info(f"[LEAD-TIMESERIES] Filtering by business_id: {business_id}")
            processed_leads_qs = processed_leads_qs.filter(business_id=business_id)
        
        # Group processed leads by date
        processed_leads_stats = processed_leads_qs.annotate(
            date=TruncDate('processed_at')
        ).values('date').annotate(
            lead_count=Count('id')
        ).order_by('date')
        
        # Query LeadEvents (customer interactions by date)
        events_qs = LeadEvent.objects.filter(
            time_created__date__gte=start_date,
            time_created__date__lte=end_date
        )
        
        if business_id:
            # Filter events by business through LeadDetail
            lead_ids = (
                LeadDetail.objects
                .filter(business_id=business_id)
                .values_list("lead_id", flat=True)
            )
            events_qs = events_qs.filter(lead_id__in=lead_ids)
        
        # Group events by date and count different types
        events_stats = events_qs.annotate(
            date=TruncDate('time_created')
        ).values('date').annotate(
            event_count=Count('id'),
            customer_events=Count('id', filter=Q(user_type='USER')),
            business_events=Count('id', filter=Q(user_type='BUSINESS'))
        ).order_by('date')
        
        # Combine results
        result_dict = {}
        
        # Add processed leads stats
        for stat in processed_leads_stats:
            date_str = stat['date'].isoformat()
            result_dict[date_str] = {
                'date': date_str,
                'lead_count': stat['lead_count'],
                'event_count': 0,
                'customer_events': 0,
                'business_events': 0
            }
        
        # Add events stats
        for stat in events_stats:
            date_str = stat['date'].isoformat()
            if date_str in result_dict:
                result_dict[date_str]['event_count'] = stat['event_count']
                result_dict[date_str]['customer_events'] = stat['customer_events']
                result_dict[date_str]['business_events'] = stat['business_events']
            else:
                result_dict[date_str] = {
                    'date': date_str,
                    'lead_count': 0,
                    'event_count': stat['event_count'],
                    'customer_events': stat['customer_events'],
                    'business_events': stat['business_events']
                }
        
        # Fill in missing dates with zero values
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Build final result with all dates
        final_result = []
        for date in all_dates:
            date_str = date.isoformat()
            if date_str in result_dict:
                final_result.append(result_dict[date_str])
            else:
                final_result.append({
                    'date': date_str,
                    'lead_count': 0,
                    'event_count': 0,
                    'customer_events': 0,
                    'business_events': 0
                })
        
        logger.info(f"[LEAD-TIMESERIES] Returning {len(final_result)} daily records")
        return Response(final_result)
