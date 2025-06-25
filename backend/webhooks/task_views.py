import logging
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics

from .models import CeleryTaskLog
from .serializers import CeleryTaskLogSerializer

logger = logging.getLogger(__name__)


class TaskLogListView(generics.ListAPIView):
    """Return Celery task logs with optional filtering."""

    serializer_class = CeleryTaskLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "business_id"]

    def get_queryset(self):
        qs = CeleryTaskLog.objects.all().order_by("-eta")
        start = self.request.query_params.get("started_after")
        if start:
            qs = qs.filter(finished_at__gte=start)
        return qs

