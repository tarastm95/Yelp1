import logging
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters
from rest_framework import generics

from .models import CeleryTaskLog
from .serializers import CeleryTaskLogSerializer, MessageTaskSerializer

logger = logging.getLogger(__name__)


class TaskLogFilterSet(FilterSet):
    """Allow filtering by multiple status values."""

    status = filters.CharFilter(method="filter_status")

    class Meta:
        model = CeleryTaskLog
        fields = ["status", "business_id"]

    def filter_status(self, queryset, name, value):
        """Support comma separated or repeated status params."""
        raw_values = self.data.getlist(name)
        statuses: list[str] = []
        for v in raw_values:
            if v:
                statuses.extend(s.strip().upper() for s in v.split(",") if s.strip())
        if statuses:
            return queryset.filter(status__in=statuses)
        return queryset


class TaskLogListView(generics.ListAPIView):
    """Return Celery task logs with optional filtering."""

    serializer_class = CeleryTaskLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskLogFilterSet

    def get_queryset(self):
        qs = CeleryTaskLog.objects.all().order_by("-eta")
        start = self.request.query_params.get("started_after")
        if start:
            qs = qs.filter(finished_at__gte=start)
        return qs


class MessageTaskListView(generics.ListAPIView):
    """Simplified list of executed message tasks."""

    serializer_class = MessageTaskSerializer

    def get_queryset(self):
        return (
            CeleryTaskLog.objects.filter(
                name__in=[
                    "send_follow_up",
                    "send_scheduled_message",
                    "send_lead_scheduled_message",
                ],
                finished_at__isnull=False,
            )
            .order_by("-finished_at")
        )

