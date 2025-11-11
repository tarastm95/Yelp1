"""
WhatsApp notification views for managing WhatsApp settings and logs.
"""
import logging
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from .models import WhatsAppLog, WhatsAppNotificationSetting, YelpBusiness
from .serializers import WhatsAppLogSerializer, WhatsAppNotificationSettingSerializer
from .twilio_content_api import fetch_content_templates

logger = logging.getLogger(__name__)


class WhatsAppLogFilterSet(filters.FilterSet):
    """Filter for WhatsApp logs."""
    
    business_id = filters.CharFilter(field_name='business_id', lookup_expr='exact')
    lead_id = filters.CharFilter(field_name='lead_id', lookup_expr='exact')
    status = filters.ChoiceFilter(choices=[
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('undelivered', 'Undelivered'),
    ])
    purpose = filters.ChoiceFilter(choices=[
        ('notification', 'Notification'),
        ('customer_reply', 'Customer Reply'),
        ('api', 'API'),
    ])
    
    class Meta:
        model = WhatsAppLog
        fields = ['business_id', 'lead_id', 'status', 'purpose']


class WhatsAppLogListView(generics.ListAPIView):
    """List WhatsApp logs with filtering."""
    serializer_class = WhatsAppLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = WhatsAppLogFilterSet
    
    def get_queryset(self):
        return WhatsAppLog.objects.all().order_by('-sent_at')


class WhatsAppStatsView(APIView):
    """Return WhatsApp statistics."""
    
    def get(self, request):
        total = WhatsAppLog.objects.count()
        by_status = {}
        by_purpose = {}
        
        for status_choice in ['sent', 'delivered', 'failed', 'undelivered']:
            by_status[status_choice] = WhatsAppLog.objects.filter(status=status_choice).count()
        
        for purpose_choice in ['notification', 'customer_reply', 'api']:
            by_purpose[purpose_choice] = WhatsAppLog.objects.filter(purpose=purpose_choice).count()
        
        return Response({
            'total': total,
            'by_status': by_status,
            'by_purpose': by_purpose,
        })


class WhatsAppNotificationSettingListCreateView(generics.ListCreateAPIView):
    """List and create WhatsApp notification settings."""
    serializer_class = WhatsAppNotificationSettingSerializer

    def get_queryset(self):
        bid = self.request.GET.get("business_id")
        qs = WhatsAppNotificationSetting.objects.all().order_by("id")
        if bid:
            return qs.filter(business__business_id=bid)
        return qs.none()

    def create(self, request, *args, **kwargs):
        phone = request.data.get("phone_number", "")
        bid = self.request.GET.get("business_id")
        use_content_template = request.data.get("use_content_template", False)
        content_sid = request.data.get("content_sid", "")
        
        if not bid:
            return Response(
                {"detail": "business_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        business = YelpBusiness.objects.filter(business_id=bid).first()
        if not business:
            return Response(
                {"detail": f"Business with id {bid} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # For Content Templates, check for duplicate content_sid + phone_number
        if use_content_template and content_sid:
            if WhatsAppNotificationSetting.objects.filter(
                content_sid=content_sid, 
                phone_number=phone,
                business=business
            ).exists():
                return Response(
                    {"detail": "This Content Template is already configured for this phone number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # For simple templates, check phone_number
        elif phone and WhatsAppNotificationSetting.objects.filter(
            phone_number=phone, 
            business=business,
            use_content_template=False
        ).exists():
            return Response(
                {"detail": "Phone number already exists for this business."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(business=business)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WhatsAppNotificationSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a WhatsApp notification setting."""
    serializer_class = WhatsAppNotificationSettingSerializer
    queryset = WhatsAppNotificationSetting.objects.all()

class TwilioContentTemplateDetailsView(APIView):
    """
    GET /api/twilio-content-template-details/{content_sid}/
    Get specific Content Template details including variables and suggested mapping.
    """
    
    def get(self, request, content_sid):
        logger.info(f"[TWILIO-CONTENT-API] Getting details for Content Template: {content_sid}")
        
        try:
            from .twilio_content_api import get_content_template_details, get_suggested_variable_mapping
            
            # Get template details
            details = get_content_template_details(content_sid)
            
            # Get suggested variable mapping
            suggested_mapping = get_suggested_variable_mapping(details['variables'])
            
            response_data = {
                'sid': details['sid'],
                'friendly_name': details['friendly_name'],
                'body': details['body'],
                'variables': details['variables'],
                'suggested_mapping': suggested_mapping,
                'types': details['types'],
                'language': details['language'],
                'status': details['status'],
                'date_created': details['date_created'],
                'date_updated': details['date_updated'],
            }
            
            logger.info(f"[TWILIO-CONTENT-API] ✅ Returning template details for {content_sid}")
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"[TWILIO-CONTENT-API] ❌ Error getting template details for {content_sid}: {e}")
            return Response(
                {"error": f"Failed to get template details: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TwilioContentTemplatesView(APIView):
    """
    GET /api/twilio-content-templates/
    Fetch all available Content Templates from Twilio.
    Query params: ?business_id=xxx
    """
    
    def get(self, request):
        logger.info("[TWILIO-CONTENT-API] Received request to fetch Content Templates")
        
        try:
            templates = fetch_content_templates()
            
            # Filter templates that have text content (suitable for WhatsApp)
            whatsapp_templates = []
            for template in templates:
                # Check if template has text content
                if template.get('types'):
                    # Check if template has 'twilio/text' type
                    types_dict = template.get('types', {})
                    if 'twilio/text' in types_dict or any('text' in str(k).lower() for k in types_dict.keys()):
                        whatsapp_templates.append(template)
            
            # If no templates found with text type, return all templates
            if not whatsapp_templates:
                whatsapp_templates = templates
            
            logger.info(f"[TWILIO-CONTENT-API] ✅ Returning {len(whatsapp_templates)} templates")
            return Response({'contents': whatsapp_templates})
            
        except Exception as e:
            logger.error(f"[TWILIO-CONTENT-API] ❌ Error fetching Content Templates: {e}")
            return Response(
                {"error": f"Failed to fetch templates: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TwilioContentTemplatePreviewView(APIView):
    """
    POST /api/twilio-content-templates/{content_sid}/preview/
    Preview a Content Template with sample data.
    """
    
    def post(self, request, content_sid):
        logger.info(f"[TWILIO-CONTENT-API] Preview request for Content Template: {content_sid}")
        
        try:
            from .twilio_content_api import get_content_template_details, build_content_variables
            
            # Get template details
            details = get_content_template_details(content_sid)
            
            # Get sample data from request
            sample_data = request.data.get('sample_data', {})
            variable_mapping = request.data.get('variable_mapping', {})
            
            # Build content variables
            content_variables = build_content_variables(variable_mapping, sample_data)
            
            # Create preview message
            preview_message = details['body']
            for var_num, value in content_variables.items():
                preview_message = preview_message.replace(f"{{{{{var_num}}}}}", str(value))
            
            response_data = {
                'template_body': details['body'],
                'preview_message': preview_message,
                'content_variables': content_variables,
                'variable_mapping': variable_mapping,
            }
            
            logger.info(f"[TWILIO-CONTENT-API] ✅ Returning preview for {content_sid}")
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"[TWILIO-CONTENT-API] ❌ Error creating preview for {content_sid}: {e}")
            return Response(
                {"error": f"Failed to create preview: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
