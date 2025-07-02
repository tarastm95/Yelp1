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
    def _get_default_settings(self, phone_opt_in: bool, phone_available: bool):
        obj, _ = AutoResponseSettings.objects.get_or_create(
            business=None, phone_opt_in=phone_opt_in, phone_available=phone_available
        )
        return obj

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
                follow_up_template='',
                greeting_delay=0,
                follow_up_delay=0,
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
        instance = serializer.save(business=business, phone_opt_in=phone_opt_in, phone_available=phone_available)
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
