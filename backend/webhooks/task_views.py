import logging
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

import django_rq

from .models import CeleryTaskLog, LeadPendingTask
from .serializers import CeleryTaskLogSerializer, MessageTaskSerializer

logger = logging.getLogger(__name__)


class TaskLogPagination(PageNumberPagination):
    """Custom pagination for task logs - 20 items per page."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


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
    """Return task logs with optional filtering and pagination."""

    serializer_class = CeleryTaskLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskLogFilterSet
    pagination_class = TaskLogPagination

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


class TaskRevokeView(APIView):
    """Revoke a scheduled task and log the reason."""

    def post(self, request, task_id: str):
        reason = request.data.get("reason", "")
        queue = django_rq.get_queue("default")
        scheduler = django_rq.get_scheduler("default")
        try:
            job = queue.fetch_job(task_id)
            if job:
                job.cancel()
            scheduler.cancel(task_id)
        except Exception as exc:
            logger.error(f"[TASK] Error revoking {task_id}: {exc}")
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CeleryTaskLog.objects.filter(task_id=task_id).update(
            status="REVOKED", result=reason
        )
        LeadPendingTask.objects.filter(task_id=task_id).update(active=False)
        return Response({"status": "revoked"})

