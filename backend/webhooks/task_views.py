import logging
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters
from rest_framework import generics

from .models import CeleryTaskLog
from .serializers import CeleryTaskLogSerializer

logger = logging.getLogger(__name__)


class TaskLogFilterSet(FilterSet):
    """Allow filtering by multiple status values."""

    status = filters.CharFilter(method="filter_status")

    class Meta:
        model = CeleryTaskLog
        fields = ["status", "business_id"]

    def filter_status(self, queryset, name, value):
        values = self.data.getlist(name)
        if values:
            return queryset.filter(status__in=values)
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

