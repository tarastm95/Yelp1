import logging
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.utils import timezone

import django_rq

from .models import CeleryTaskLog, LeadPendingTask, ProcessedLead
from .serializers import CeleryTaskLogSerializer, MessageTaskSerializer, LeadPendingTaskSerializer

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

    pagination_class = TaskLogPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on data source."""
        status = self.request.query_params.get("status", "")
        if status == "scheduled":
            return LeadPendingTaskSerializer
        return CeleryTaskLogSerializer
    
    def filter_queryset(self, queryset):
        """Apply filtering only for CeleryTaskLog queries."""
        status = self.request.query_params.get("status", "")
        # For scheduled (LeadPendingTask) queries, skip DjangoFilterBackend filtering
        if status == "scheduled":
            return queryset

        # For CeleryTaskLog queries, apply normal filtering
        for backend in [DjangoFilterBackend]:
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def get_queryset(self):
        """Return data from appropriate source based on status filter."""
        status = self.request.query_params.get("status", "")
        business_id = self.request.query_params.get("business_id")
        
        logger.info(f"[TASK-LIST] Request: status={status}, business_id={business_id}")
        
        if status == "scheduled":
            # Scheduled tasks - from LeadPendingTask (active=True)
            logger.info(f"[TASK-LIST] Using LeadPendingTask for scheduled tasks")
            qs = LeadPendingTask.objects.filter(active=True).order_by("-created_at")

            if business_id:
                business_lead_ids = ProcessedLead.objects.filter(
                    business_id=business_id
                ).values_list('lead_id', flat=True)
                qs = qs.filter(lead_id__in=business_lead_ids)

            logger.info(f"[TASK-LIST] Returning {qs.count()} scheduled tasks")
            return qs

        elif status in ["revoked", "canceled"]:
            # Revoked/canceled tasks - from CeleryTaskLog (status REVOKED)
            logger.info(f"[TASK-LIST] Using CeleryTaskLog for revoked/canceled tasks")

            # Clean up old pending records where active=False
            LeadPendingTask.objects.filter(active=False).delete()

            # Sort by finished_at (cancellation time), then by eta (original schedule time)  
            qs = CeleryTaskLog.objects.filter(status="REVOKED").order_by("-finished_at", "-eta")

            if business_id:
                qs = qs.filter(business_id=business_id)

            start = self.request.query_params.get("started_after")
            if start:
                qs = qs.filter(finished_at__gte=start)

            logger.info(f"[TASK-LIST] Returning {qs.count()} revoked/canceled tasks")
            return qs

        else:
            # Completed and failed tasks - from CeleryTaskLog (as before)
            logger.info(f"[TASK-LIST] Using CeleryTaskLog for completed/failed tasks")
            # Sort by finished_at (execution time) - newest first, then by eta
            qs = CeleryTaskLog.objects.all().order_by("-finished_at", "-eta")
            start = self.request.query_params.get("started_after")
            if start:
                qs = qs.filter(finished_at__gte=start)
            logger.info(f"[TASK-LIST] Returning {qs.count()} completed/failed tasks")
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


class TaskStatsView(APIView):
    """Return task statistics without pagination."""

    def get(self, request):
        """Return counts of tasks by status with optional business filtering."""
        logger.info(f"[TASK-STATS] 📊 Task Stats API request")
        logger.info(f"[TASK-STATS] Query params: {dict(request.query_params)}")
        
        # Base queryset
        qs = CeleryTaskLog.objects.all()
        
        # Apply business filtering if provided
        business_id = request.query_params.get("business_id")
        if business_id:
            logger.info(f"[TASK-STATS] Filtering by business_id: {business_id}")
            qs = qs.filter(business_id=business_id)
        
        # Optional date filtering
        started_after = request.query_params.get("started_after")
        if started_after:
            logger.info(f"[TASK-STATS] Filtering by started_after: {started_after}")
            qs = qs.filter(finished_at__gte=started_after)
        
        # Count by status
        stats = {
            'successful': qs.filter(status='SUCCESS').count(),
            'failed': qs.filter(status='FAILURE').count(),
        }
        
        # Get business lead IDs for filtering (used for both scheduled and canceled)
        business_lead_ids = None
        if business_id:
            business_lead_ids = ProcessedLead.objects.filter(
                business_id=business_id
            ).values_list('lead_id', flat=True)
        
        # For scheduled tasks, use LeadPendingTask (without complex RQ validation for now)
        scheduled_qs = LeadPendingTask.objects.filter(active=True)
        if business_lead_ids is not None:
            scheduled_qs = scheduled_qs.filter(lead_id__in=business_lead_ids)
        
        # For canceled tasks, use CeleryTaskLog.REVOKED only
        stats['scheduled'] = scheduled_qs.count()
        stats['canceled'] = qs.filter(status='REVOKED').count()
        stats['total'] = stats['successful'] + stats['failed'] + stats['scheduled'] + stats['canceled']

        # Enhanced logging for debugging
        logger.info(f"[TASK-STATS] Statistics breakdown:")
        logger.info(f"[TASK-STATS] - Successful (CeleryTaskLog.SUCCESS): {stats['successful']}")
        logger.info(f"[TASK-STATS] - Failed (CeleryTaskLog.FAILURE): {stats['failed']}")
        logger.info(f"[TASK-STATS] - Scheduled (LeadPendingTask.active=True): {stats['scheduled']}")
        logger.info(f"[TASK-STATS] - Canceled (CeleryTaskLog.REVOKED): {stats['canceled']}")
        logger.info(f"[TASK-STATS] - Total: {stats['total']}")
        logger.info(f"[TASK-STATS] Returning stats: {stats}")
        return Response(stats)


class TaskRevokeView(APIView):
    """Revoke a scheduled task and log the reason."""

    def post(self, request, task_id: str):
        reason = request.data.get("reason", "Task manually revoked from dashboard")
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


class TaskTimeSeriesView(APIView):
    """Return Task time-series data grouped by date."""

    def get(self, request):
        """Return Task counts grouped by date."""
        logger.info(f"[TASK-TIMESERIES] 📊 Task Time Series API request")
        logger.info(f"[TASK-TIMESERIES] Query params: {dict(request.query_params)}")
        
        # Parse date range
        days = int(request.query_params.get("days", 30))
        business_id = request.query_params.get("business_id")
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        logger.info(f"[TASK-TIMESERIES] Date range: {start_date} to {end_date} ({days} days)")
        
        # Base queryset - use finished_at date for completed tasks, eta for scheduled
        qs = CeleryTaskLog.objects.filter(
            Q(finished_at__date__gte=start_date, finished_at__date__lte=end_date) |
            Q(eta__date__gte=start_date, eta__date__lte=end_date, finished_at__isnull=True)
        )
        
        # Apply business filtering if provided
        if business_id:
            logger.info(f"[TASK-TIMESERIES] Filtering by business_id: {business_id}")
            qs = qs.filter(business_id=business_id)
        
        # Group by date and calculate statistics for finished tasks
        finished_stats = qs.filter(finished_at__isnull=False).annotate(
            date=TruncDate('finished_at')
        ).values('date').annotate(
            successful_count=Count('id', filter=Q(status='SUCCESS')),
            failed_count=Count('id', filter=Q(status='FAILURE')),
            canceled_count=Count('id', filter=Q(status='REVOKED'))
        ).order_by('date')
        
        # Group by date for scheduled tasks (using eta)
        scheduled_stats = qs.filter(finished_at__isnull=True, status='SCHEDULED').annotate(
            date=TruncDate('eta')
        ).values('date').annotate(
            scheduled_count=Count('id')
        ).order_by('date')
        
        # Combine results
        result_dict = {}
        
        # Add finished task stats
        for stat in finished_stats:
            date_str = stat['date'].isoformat()
            result_dict[date_str] = {
                'date': date_str,
                'task_count': stat['successful_count'] + stat['failed_count'] + stat['canceled_count'],
                'successful_count': stat['successful_count'],
                'failed_count': stat['failed_count'],
                'scheduled_count': 0,
                'canceled_count': stat['canceled_count']
            }
        
        # Add scheduled task stats
        for stat in scheduled_stats:
            date_str = stat['date'].isoformat()
            if date_str in result_dict:
                result_dict[date_str]['scheduled_count'] = stat['scheduled_count']
                result_dict[date_str]['task_count'] += stat['scheduled_count']
            else:
                result_dict[date_str] = {
                    'date': date_str,
                    'task_count': stat['scheduled_count'],
                    'successful_count': 0,
                    'failed_count': 0,
                    'scheduled_count': stat['scheduled_count'],
                    'canceled_count': 0
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
                    'task_count': 0,
                    'successful_count': 0,
                    'failed_count': 0,
                    'scheduled_count': 0,
                    'canceled_count': 0
                })
        
        logger.info(f"[TASK-TIMESERIES] Returning {len(final_result)} daily records")
        return Response(final_result)

