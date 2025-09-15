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

from .models import CeleryTaskLog, LeadPendingTask
from .serializers import CeleryTaskLogSerializer, MessageTaskSerializer

logger = logging.getLogger(__name__)


class TaskLogPagination(PageNumberPagination):
    """Custom pagination for task logs - 20 items per page."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TaskLogFilterSet(FilterSet):
    """Allow filtering by multiple status values and lead ID."""

    status = filters.CharFilter(method="filter_status")
    lead_id = filters.CharFilter(method="filter_lead_id")

    class Meta:
        model = CeleryTaskLog
        fields = ["status", "business_id", "lead_id"]

    def filter_status(self, queryset, name, value):
        """Support comma separated or repeated status params with status mapping."""
        raw_values = self.data.getlist(name)
        statuses: list[str] = []
        
        # Status mapping for frontend compatibility
        status_mapping = {
            'CANCELED': 'REVOKED',  # Frontend sends 'canceled', database has 'REVOKED'
            'CANCELLED': 'REVOKED', # Alternative spelling
            'SUCCESS': 'SUCCESS',
            'FAILURE': 'FAILURE', 
            'SCHEDULED': 'SCHEDULED',
            'REVOKED': 'REVOKED',
        }
        
        for v in raw_values:
            if v:
                for s in v.split(","):
                    if s.strip():
                        normalized = s.strip().upper()
                        # Map frontend status to database status
                        db_status = status_mapping.get(normalized, normalized)
                        statuses.append(db_status)
        
        logger.info(f"[FILTER] Status filter: frontend='{raw_values}' → database={statuses}")
        
        if statuses:
            return queryset.filter(status__in=statuses)
        return queryset
    
    def filter_lead_id(self, queryset, name, value):
        """Filter tasks by lead ID in args field."""
        if not value:
            return queryset
            
        logger.info(f"[FILTER] Lead ID filter: '{value}'")
        
        # Filter tasks where args contains the lead_id
        # args is stored as JSON, first element is typically lead_id
        # Use PostgreSQL JSON operations instead of MySQL JSON_EXTRACT
        try:
            from django.db import connection
            vendor = connection.vendor
            
            if vendor == 'postgresql':
                # PostgreSQL syntax: args->0 for first array element
                filtered_qs = queryset.extra(
                    where=["args->>0 = %s"],
                    params=[value]
                )
            else:
                # MySQL/SQLite fallback
                filtered_qs = queryset.extra(
                    where=["JSON_EXTRACT(args, '$[0]') = %s"],
                    params=[value]
                )
            
            count = filtered_qs.count()
            logger.info(f"[FILTER] Found {count} tasks for lead_id '{value}' (DB: {vendor})")
            
            return filtered_qs
            
        except Exception as e:
            logger.error(f"[FILTER] Error filtering by lead_id '{value}': {e}")
            # Fallback to text search in args
            return queryset.filter(args__icontains=value)


class TaskLogListView(generics.ListAPIView):
    """Return task logs with optional filtering and pagination."""

    serializer_class = CeleryTaskLogSerializer
    filter_backends = [DjangoFilterBackend] 
    filterset_class = TaskLogFilterSet
    pagination_class = TaskLogPagination

    def get_queryset(self):
        """Return CeleryTaskLog data sorted by execution time."""
        status_param = self.request.query_params.get("status", "")
        business_param = self.request.query_params.get("business_id", "")
        lead_id_param = self.request.query_params.get("lead_id", "")
        
        logger.info(f"[TASK-LIST] 📊 API REQUEST DETAILS:")
        logger.info(f"[TASK-LIST] - Status filter: '{status_param}'")
        logger.info(f"[TASK-LIST] - Business filter: '{business_param}'") 
        logger.info(f"[TASK-LIST] - Lead ID filter: '{lead_id_param}'")
        logger.info(f"[TASK-LIST] - Full query params: {dict(self.request.query_params)}")
        
        # Clean up old pending records (they're duplicated in CeleryTaskLog)
        cleaned = LeadPendingTask.objects.filter(active=False).count()
        if cleaned > 0:
            LeadPendingTask.objects.filter(active=False).delete()
            logger.info(f"[TASK-LIST] Cleaned up {cleaned} old LeadPendingTask records")
        
        # Sort by execution time - newest executed first
        qs = CeleryTaskLog.objects.all().order_by(
            "-finished_at",  # Executed tasks first (newest)
            "-eta"           # Then by planned time
        )
        
        # Apply date filtering if provided
        start = self.request.query_params.get("started_after") 
        if start:
            qs = qs.filter(finished_at__gte=start)
            
        total_count = qs.count()
        logger.info(f"[TASK-LIST] 📈 BEFORE FILTERING:")
        logger.info(f"[TASK-LIST] - Total CeleryTaskLog records: {total_count}")
        
        # Show breakdown by status
        status_breakdown = {}
        for status_val in ['SUCCESS', 'FAILURE', 'SCHEDULED', 'REVOKED']:
            count = qs.filter(status=status_val).count()
            status_breakdown[status_val] = count
            logger.info(f"[TASK-LIST] - {status_val}: {count}")
        
        # Log specific lead_id filtering results if applicable
        if lead_id_param:
            try:
                from django.db import connection
                vendor = connection.vendor
                
                if vendor == 'postgresql':
                    lead_tasks = qs.extra(
                        where=["args->>0 = %s"],
                        params=[lead_id_param]
                    )
                else:
                    lead_tasks = qs.extra(
                        where=["JSON_EXTRACT(args, '$[0]') = %s"],
                        params=[lead_id_param]
                    )
                    
                logger.info(f"[TASK-LIST] 🔍 Lead ID '{lead_id_param}' specific results: {lead_tasks.count()} tasks ({vendor})")
                for task in lead_tasks[:3]:  # Log first 3 tasks for this lead
                    logger.info(f"[TASK-LIST]   - {task.status}: {task.name} at {task.eta}")
                    
            except Exception as e:
                logger.error(f"[TASK-LIST] Error querying lead_id '{lead_id_param}': {e}")
                # Fallback query
                lead_tasks = qs.filter(args__icontains=lead_id_param)
                logger.info(f"[TASK-LIST] Using fallback search: {lead_tasks.count()} tasks")
        
        return qs
    
    def list(self, request, *args, **kwargs):
        """Override list to add detailed logging of serialized response."""
        response = super().list(request, *args, **kwargs)
        
        status_param = request.query_params.get("status", "")
        logger.info(f"[TASK-LIST] 📤 API RESPONSE FOR status='{status_param}':")
        logger.info(f"[TASK-LIST] - Response status code: {response.status_code}")
        logger.info(f"[TASK-LIST] - Total count: {response.data.get('count', 'N/A')}")
        logger.info(f"[TASK-LIST] - Results count: {len(response.data.get('results', []))}")
        
        # Show first few results for debugging
        results = response.data.get('results', [])
        for i, result in enumerate(results[:3]):
            logger.info(f"[TASK-LIST] - Result #{i+1}:")
            logger.info(f"[TASK-LIST]   - task_id: {result.get('task_id', 'N/A')}")
            logger.info(f"[TASK-LIST]   - status: {result.get('status', 'N/A')}")
            logger.info(f"[TASK-LIST]   - eta: {result.get('eta', 'N/A')}")
            logger.info(f"[TASK-LIST]   - finished_at: {result.get('finished_at', 'N/A')}")
            logger.info(f"[TASK-LIST]   - args: {result.get('args', 'N/A')}")
        
        if len(results) > 3:
            logger.info(f"[TASK-LIST] ... and {len(results) - 3} more results")
            
        return response


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
        
        # Apply lead ID filtering if provided
        lead_id = request.query_params.get("lead_id")
        if lead_id:
            logger.info(f"[TASK-STATS] Filtering by lead_id: {lead_id}")
            try:
                from django.db import connection
                vendor = connection.vendor
                
                if vendor == 'postgresql':
                    # PostgreSQL syntax: args->0 for first array element
                    qs = qs.extra(
                        where=["args->>0 = %s"],
                        params=[lead_id]
                    )
                else:
                    # MySQL/SQLite fallback
                    qs = qs.extra(
                        where=["JSON_EXTRACT(args, '$[0]') = %s"],
                        params=[lead_id]
                    )
                    
                logger.info(f"[TASK-STATS] Applied lead_id filter for {vendor} database")
                
            except Exception as e:
                logger.error(f"[TASK-STATS] Error filtering by lead_id '{lead_id}': {e}")
                # Fallback to text search in args
                qs = qs.filter(args__icontains=lead_id)
        
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
        
        
        # All statistics from CeleryTaskLog only
        stats['scheduled'] = qs.filter(status='SCHEDULED').count()
        stats['canceled'] = qs.filter(status='REVOKED').count()
        stats['total'] = stats['successful'] + stats['failed'] + stats['scheduled'] + stats['canceled']
 
        # Enhanced logging for debugging
        logger.info(f"[TASK-STATS] Statistics breakdown (all from CeleryTaskLog):")
        logger.info(f"[TASK-STATS] - Successful: {stats['successful']}")
        logger.info(f"[TASK-STATS] - Failed: {stats['failed']}")
        logger.info(f"[TASK-STATS] - Scheduled: {stats['scheduled']}")
        logger.info(f"[TASK-STATS] - Canceled: {stats['canceled']}")
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

