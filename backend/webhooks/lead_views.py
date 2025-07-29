import logging
from django.db.models import Q
from rest_framework import generics, mixins, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .models import (
    Event,
    ProcessedLead,
    AutoResponseSettings,
    YelpBusiness,
    LeadDetail,
    FollowUpTemplate,
    YelpToken,
    LeadEvent,
    NotificationSetting,
)
from .pagination import FivePerPagePagination
from .serializers import (
    EventSerializer,
    AutoResponseSettingsSerializer,
    ProcessedLeadSerializer,
    LeadDetailSerializer,
    FollowUpTemplateSerializer,
    YelpTokenInfoSerializer,
    LeadEventSerializer,
    NotificationSettingSerializer,
)

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
        qs = ProcessedLead.objects.order_by("-processed_at")
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
        return qs.filter(business__isnull=True)

    def create(self, request, *args, **kwargs):
        phone = request.data.get("phone_number", "")
        bid = request.query_params.get("business_id")
        business = YelpBusiness.objects.filter(business_id=bid).first() if bid else None
        if NotificationSetting.objects.filter(phone_number=phone, business=business).exists():
            return Response(
                {"detail": "Phone number already exists."},
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
        return qs.filter(business__isnull=True)

    def perform_update(self, serializer):
        bid = self.request.query_params.get("business_id")
        business = YelpBusiness.objects.filter(business_id=bid).first() if bid else None
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
            # Отримання параметрів з запиту
            business_name = request.data.get('business_name', 'Your Business')
            customer_name = request.data.get('customer_name', 'John')
            services = request.data.get('services', 'plumbing services')
            response_style = request.data.get('ai_response_style', 'auto')
            include_location = request.data.get('ai_include_location', False)
            mention_response_time = request.data.get('ai_mention_response_time', False)
            custom_prompt = request.data.get('ai_custom_prompt', None)
            
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
            
            # Генерація preview повідомлення
            preview_message = ai_service.generate_preview_message(
                business_name=business_name,
                customer_name=customer_name,
                services=services,
                response_style=response_style,
                include_location=include_location,
                mention_response_time=mention_response_time,
                custom_prompt=custom_prompt,
                business_data_settings=business_data_settings
            )
            
            return Response({
                'preview': preview_message,
                'parameters': {
                    'business_name': business_name,
                    'customer_name': customer_name,
                    'services': services,
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
