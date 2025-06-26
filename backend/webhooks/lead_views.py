import logging
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
    AutoResponseSettingsTemplate,
    YelpToken,
    LeadEvent,
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
    AutoResponseSettingsTemplateSerializer,
)
from .tasks import reschedule_follow_up_tasks

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
    def _get_default_settings(self):
        obj, _ = AutoResponseSettings.objects.get_or_create(id=1)
        return obj

    def _get_settings_for_business(self, business_id: str | None):
        if business_id:
            obj = AutoResponseSettings.objects.filter(business__business_id=business_id).first()
            if obj:
                return obj
        return self._get_default_settings()

    def get(self, request, *args, **kwargs):
        bid = request.query_params.get('business_id')
        obj = self._get_settings_for_business(bid)
        serializer = AutoResponseSettingsSerializer(obj)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        bid = request.query_params.get('business_id')
        if bid:
            business = YelpBusiness.objects.filter(business_id=bid).first()
            obj, _ = AutoResponseSettings.objects.get_or_create(business=business)
        else:
            obj = self._get_default_settings()
        serializer = AutoResponseSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    post = put


class ProcessedLeadListView(generics.ListAPIView):
    queryset = ProcessedLead.objects.order_by("-processed_at")
    serializer_class = ProcessedLeadSerializer
    pagination_class = FivePerPagePagination


class LeadDetailListAPIView(APIView):
    """Return list of all LeadDetail records"""

    def get(self, request):
        queryset = LeadDetail.objects.all()
        serializer = LeadDetailSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadDetailRetrieveAPIView(APIView):
    """Return single LeadDetail by lead_id"""

    def get_object(self, lead_id: str) -> LeadDetail:
        try:
            return LeadDetail.objects.get(lead_id=lead_id)
        except LeadDetail.DoesNotExist:
            raise NotFound(detail=f"LeadDetail з lead_id={lead_id} не знайдено")

    def get(self, request, lead_id: str):
        obj = self.get_object(lead_id)
        serializer = LeadDetailSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadLastEventAPIView(APIView):
    """Return latest LeadEvent by lead_id"""

    def get(self, request, lead_id: str):
        obj = (
            LeadEvent.objects.filter(lead_id=lead_id)
            .order_by("-time_created")
            .first()
        )
        if not obj:
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
        if bid:
            qs = FollowUpTemplate.objects.filter(business__business_id=bid)
            if qs.exists():
                return qs
        return FollowUpTemplate.objects.filter(business__isnull=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"[FollowUpTemplate] validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        bid = request.query_params.get('business_id')
        business = YelpBusiness.objects.filter(business_id=bid).first() if bid else None
        serializer.save(business=business)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class FollowUpTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FollowUpTemplateSerializer

    def get_queryset(self):
        bid = self.request.query_params.get('business_id')
        if bid:
            qs = FollowUpTemplate.objects.filter(business__business_id=bid)
            if qs.exists():
                return qs
        return FollowUpTemplate.objects.filter(business__isnull=True)

    def perform_update(self, serializer):
        instance = serializer.save()
        reschedule_follow_up_tasks(instance)


class AutoResponseSettingsTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = AutoResponseSettingsTemplateSerializer

    queryset = AutoResponseSettingsTemplate.objects.all().order_by('-id')


class AutoResponseSettingsTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AutoResponseSettingsTemplateSerializer
    queryset = AutoResponseSettingsTemplate.objects.all()


class YelpTokenListView(generics.ListAPIView):
    serializer_class = YelpTokenInfoSerializer

    def get_queryset(self):
        return YelpToken.objects.all().order_by('business_id')
