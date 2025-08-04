from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters
import logging

from .serializers import SendSMSSerializer, SMSLogSerializer
from .twilio_utils import send_sms
from .models import SMSLog

logger = logging.getLogger(__name__)


class SMSLogPagination(PageNumberPagination):
    """Custom pagination for SMS logs - 20 items per page."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class SMSLogFilterSet(FilterSet):
    """Allow filtering SMS logs by multiple criteria."""

    status = filters.CharFilter(method="filter_status")
    purpose = filters.CharFilter(method="filter_purpose")

    class Meta:
        model = SMSLog
        fields = ["status", "purpose", "business_id", "lead_id"]

    def filter_status(self, queryset, name, value):
        """Support comma separated status values."""
        raw_values = self.data.getlist(name)
        statuses: list[str] = []
        for v in raw_values:
            if v:
                statuses.extend(s.strip().lower() for s in v.split(",") if s.strip())
        if statuses:
            return queryset.filter(status__in=statuses)
        return queryset
    
    def filter_purpose(self, queryset, name, value):
        """Support comma separated purpose values."""
        raw_values = self.data.getlist(name)
        purposes: list[str] = []
        for v in raw_values:
            if v:
                purposes.extend(p.strip() for p in v.split(",") if p.strip())
        if purposes:
            return queryset.filter(purpose__in=purposes)
        return queryset


class SendSMSAPIView(APIView):
    """POST endpoint to send an SMS message via Twilio."""

    def post(self, request, *args, **kwargs):
        logger.info(f"[SMS-API] 📱 RECEIVED SMS API REQUEST")
        logger.info(f"[SMS-API] Request details:")
        logger.info(f"[SMS-API] - Method: {request.method}")
        logger.info(f"[SMS-API] - User: {getattr(request.user, 'username', 'Anonymous')}")
        logger.info(f"[SMS-API] - User authenticated: {request.user.is_authenticated}")
        logger.info(f"[SMS-API] - Content type: {request.content_type}")
        logger.info(f"[SMS-API] - Raw data: {request.data}")
        
        # Step 1: Validate request data
        logger.info(f"[SMS-API] 📝 STEP 1: Validating request data")
        try:
            serializer = SendSMSSerializer(data=request.data)
            logger.info(f"[SMS-API] ✅ Serializer created successfully")
            
            is_valid = serializer.is_valid(raise_exception=True)
            logger.info(f"[SMS-API] ✅ Request data validation passed")
            logger.info(f"[SMS-API] Validation result: {is_valid}")
            
        except Exception as validation_error:
            logger.error(f"[SMS-API] ❌ VALIDATION ERROR: {validation_error}")
            logger.error(f"[SMS-API] Validation errors: {getattr(serializer, 'errors', 'No details')}")
            logger.error(f"[SMS-API] Raw request data: {request.data}")
            logger.exception(f"[SMS-API] Validation exception details")
            raise
            
        # Step 2: Extract validated data
        logger.info(f"[SMS-API] 📋 STEP 2: Extracting validated data")
        to = serializer.validated_data["to"]
        body = serializer.validated_data["body"]
        
        logger.info(f"[SMS-API] Validated data:")
        logger.info(f"[SMS-API] - To: {to}")
        logger.info(f"[SMS-API] - Body: {body[:100]}..." + ("" if len(body) <= 100 else " (truncated)"))
        logger.info(f"[SMS-API] - Body length: {len(body)} characters")
        
        # Step 3: Send SMS
        logger.info(f"[SMS-API] 📤 STEP 3: Sending SMS via Twilio")
        logger.info("Sending SMS via Twilio", extra={"to": to, "body": body})
        
        try:
            logger.info(f"[SMS-API] 🚀 Calling send_sms function...")
            sid = send_sms(to, body, purpose="api")
            logger.info(f"[SMS-API] ✅ SMS sent successfully!")
            logger.info(f"[SMS-API] Twilio response SID: {sid}")
            
            # Log success with extra details
            logger.info("SMS sent", extra={"to": to, "sid": sid})
            
            # Step 4: Prepare response
            logger.info(f"[SMS-API] 📋 STEP 4: Preparing API response")
            response_data = {"sid": sid}
            logger.info(f"[SMS-API] Response data: {response_data}")
            logger.info(f"[SMS-API] Response status: {status.HTTP_200_OK}")
            
            logger.info(f"[SMS-API] 🎉 SMS API REQUEST COMPLETED SUCCESSFULLY")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as sms_error:
            logger.error(f"[SMS-API] ❌ SMS SENDING ERROR: {sms_error}")
            logger.error(f"[SMS-API] Error type: {type(sms_error).__name__}")
            logger.error(f"[SMS-API] Error details: {str(sms_error)}")
            logger.error(f"[SMS-API] Target phone: {to}")
            logger.error(f"[SMS-API] Message: {body[:100]}...")
            logger.exception(f"[SMS-API] SMS sending exception details")
            
            # Re-raise the exception to let DRF handle the error response
            raise


class SMSStatsView(APIView):
    """Return SMS statistics without pagination."""

    def get(self, request):
        """Return counts of SMS by status with optional business filtering."""
        logger.info(f"[SMS-STATS] 📊 SMS Stats API request")
        logger.info(f"[SMS-STATS] Query params: {dict(request.query_params)}")
        
        # Base queryset
        qs = SMSLog.objects.all()
        
        # Apply business filtering if provided
        business_id = request.query_params.get("business_id")
        if business_id:
            logger.info(f"[SMS-STATS] Filtering by business_id: {business_id}")
            qs = qs.filter(business_id=business_id)
        
        # Apply purpose filtering if provided
        purpose = request.query_params.get("purpose")
        if purpose:
            logger.info(f"[SMS-STATS] Filtering by purpose: {purpose}")
            qs = qs.filter(purpose=purpose)
        
        # Apply status filtering if provided
        status_param = request.query_params.get("status")
        if status_param:
            logger.info(f"[SMS-STATS] Filtering by status: {status_param}")
            qs = qs.filter(status=status_param)
        
        # Optional date filtering
        sent_after = request.query_params.get("sent_after")
        if sent_after:
            logger.info(f"[SMS-STATS] Filtering by sent_after: {sent_after}")
            qs = qs.filter(sent_at__gte=sent_after)
        
        # Count by status - successful includes: queued, accepted, sending, sent, delivered
        successful_statuses = ['queued', 'accepted', 'sending', 'sent', 'delivered']
        failed_statuses = ['failed', 'undelivered']
        pending_statuses = ['queued', 'accepted', 'sending']
        
        successful_count = qs.filter(status__iregex=r'^(' + '|'.join(successful_statuses) + ')$').count()
        failed_count = qs.filter(status__iregex=r'^(' + '|'.join(failed_statuses) + ')$').count()
        pending_count = qs.filter(status__iregex=r'^(' + '|'.join(pending_statuses) + ')$').count()
        total_count = qs.count()
        
        # Calculate total cost
        total_cost = 0.0
        for sms in qs.exclude(price__isnull=True).exclude(price=''):
            try:
                price = float(sms.price)
                total_cost += price
            except (ValueError, TypeError):
                pass
        
        stats = {
            'successful': successful_count,
            'failed': failed_count,
            'pending': pending_count,
            'total': total_count,
            'total_cost': round(total_cost, 3)
        }
        
        logger.info(f"[SMS-STATS] Returning stats: {stats}")
        return Response(stats)


class SMSLogListView(generics.ListAPIView):
    """Return SMS logs with optional filtering by business, status, purpose, etc."""
    
    serializer_class = SMSLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SMSLogFilterSet
    pagination_class = SMSLogPagination
    
    def get_queryset(self):
        """Return SMS logs ordered by sent_at descending."""
        logger.info(f"[SMS-LOGS] 📋 SMS Logs API request")
        logger.info(f"[SMS-LOGS] Query params: {dict(self.request.query_params)}")
        
        qs = SMSLog.objects.all().order_by("-sent_at")
        
        # Optional date filtering
        sent_after = self.request.query_params.get("sent_after")
        if sent_after:
            logger.info(f"[SMS-LOGS] Filtering by sent_after: {sent_after}")
            qs = qs.filter(sent_at__gte=sent_after)
            
        count = qs.count()
        logger.info(f"[SMS-LOGS] Returning {count} SMS logs")
        
        return qs

