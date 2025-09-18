"""
API endpoints for Lead Activity Logging system.

Provides comprehensive lead activity history through database-backed logging.
"""

import logging
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import LeadActivityLog, LeadDetail, CeleryTaskLog, LeadEvent
from .utils import get_lead_activity_summary

logger = logging.getLogger(__name__)


class LeadLogsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


@api_view(['GET'])
def lead_activity_history(request, lead_id):
    """
    Get complete activity history for a lead from database logging.
    
    Query Parameters:
        - type: Filter by activity_type (WEBHOOK, PLANNING, EXECUTION, etc.)
        - component: Filter by component (BACKEND, WORKER, etc.)
        - limit: Number of results (default: 100, max: 500)
        - since: ISO timestamp to get logs after
        - search: Search in message text
    """
    logger.info(f"[LEAD-LOGS] 📊 API request for lead activity: {lead_id}")
    logger.info(f"[LEAD-LOGS] Query params: {dict(request.query_params)}")
    
    # Filters
    activity_type = request.GET.get('type')
    component = request.GET.get('component') 
    limit = min(int(request.GET.get('limit', 100)), 500)
    since = request.GET.get('since')
    search = request.GET.get('search')
    
    # Base query
    logs = LeadActivityLog.objects.filter(lead_id=lead_id)
    
    # Apply filters
    if activity_type:
        logs = logs.filter(activity_type=activity_type.upper())
        
    if component:
        logs = logs.filter(component=component.upper())
        
    if since:
        try:
            from django.utils.dateparse import parse_datetime
            since_dt = parse_datetime(since)
            if since_dt:
                logs = logs.filter(timestamp__gte=since_dt)
        except Exception as e:
            logger.warning(f"[LEAD-LOGS] Invalid since parameter: {since}")
    
    if search:
        logs = logs.filter(
            Q(message__icontains=search) | 
            Q(event_name__icontains=search)
        )
    
    # Order and limit
    logs = logs.order_by('-timestamp')[:limit]
    
    # Get lead info
    lead_detail = LeadDetail.objects.filter(lead_id=lead_id).first()
    
    # Collect data
    logs_data = []
    for log in logs:
        logs_data.append({
            'id': log.id,
            'timestamp': log.timestamp,
            'activity_type': log.activity_type,
            'component': log.component,
            'event_name': log.event_name,
            'message': log.message,
            'metadata': log.metadata,
            'business_id': log.business_id,
            'task_id': log.task_id,
        })
    
    # Get summary
    summary = get_lead_activity_summary(lead_id)
    
    logger.info(f"[LEAD-LOGS] Returning {len(logs_data)} logs for lead {lead_id}")
    
    return Response({
        'lead_id': lead_id,
        'lead_info': {
            'name': lead_detail.name if lead_detail else None,
            'jobs': lead_detail.jobs if lead_detail else None,
            'created_at': lead_detail.created_at if lead_detail else None,
            'phone_number': lead_detail.phone_number if lead_detail else None,
        } if lead_detail else None,
        'filters': {
            'type': activity_type,
            'component': component,
            'limit': limit,
            'since': since,
            'search': search,
        },
        'summary': summary,
        'total_returned': len(logs_data),
        'logs': logs_data
    })


@api_view(['GET'])
def lead_complete_timeline(request, lead_id):
    """
    Get complete timeline combining database logs, tasks, and events.
    Shows full lead journey from creation to completion.
    """
    logger.info(f"[LEAD-TIMELINE] 📋 Complete timeline request for lead: {lead_id}")
    
    timeline = []
    
    # 1. Database activity logs
    activity_logs = LeadActivityLog.objects.filter(lead_id=lead_id)
    for log in activity_logs:
        timeline.append({
            'timestamp': log.timestamp,
            'source': 'ACTIVITY_LOG',
            'type': log.activity_type,
            'component': log.component,
            'event': log.event_name,
            'message': log.message,
            'metadata': log.metadata,
            'details': f"[{log.activity_type}] {log.message}"
        })
    
    # 2. Task execution logs
    tasks = CeleryTaskLog.objects.filter(args__contains=[lead_id])
    for task in tasks:
        timeline.append({
            'timestamp': task.eta or task.started_at or task.finished_at,
            'source': 'TASK_LOG',
            'type': 'TASK_EXECUTION',
            'component': 'WORKER',
            'event': task.name,
            'message': f"Task {task.status}: {task.name}",
            'metadata': {
                'task_id': task.task_id,
                'status': task.status,
                'eta': task.eta,
                'started_at': task.started_at,
                'finished_at': task.finished_at,
                'sent_at': getattr(task, 'sent_at', None),
                'message_text': task.args[1] if len(task.args) > 1 else None,
                'result': task.result,
            },
            'details': f"[TASK] {task.status}: {task.args[1][:100] if len(task.args) > 1 else 'No message'}..."
        })
    
    # 3. Lead events (Yelp interactions)
    events = LeadEvent.objects.filter(lead_id=lead_id)
    for event in events:
        timeline.append({
            'timestamp': event.time_created,
            'source': 'LEAD_EVENT',
            'type': 'YELP_INTERACTION',
            'component': 'YELP_API',
            'event': f"{event.user_type}_{event.event_type}",
            'message': f"{event.user_type} {event.event_type}: {event.text[:100]}...",
            'metadata': {
                'event_id': event.event_id,
                'user_type': event.user_type,
                'event_type': event.event_type,
                'from_backend': event.from_backend,
                'full_text': event.text,
            },
            'details': f"[{event.user_type}] {event.text[:200]}..."
        })
    
    # Sort chronologically
    timeline.sort(key=lambda x: x['timestamp'] if x['timestamp'] else timezone.now())
    
    # Get lead info
    lead_detail = LeadDetail.objects.filter(lead_id=lead_id).first()
    
    logger.info(f"[LEAD-TIMELINE] Returning {len(timeline)} timeline entries for lead {lead_id}")
    
    return Response({
        'lead_id': lead_id,
        'lead_info': {
            'name': lead_detail.name if lead_detail else None,
            'jobs': lead_detail.jobs if lead_detail else None,
            'created_at': lead_detail.created_at if lead_detail else None,
            'phone_number': lead_detail.phone_number if lead_detail else None,
        } if lead_detail else None,
        'total_entries': len(timeline),
        'timeline': timeline
    })


@api_view(['GET'])  
def lead_logs_search(request):
    """
    Search across all lead logs with various filters.
    
    Query Parameters:
        - q: Search query in messages
        - type: Activity type filter
        - business_id: Business filter
        - days: How many days back to search (default: 7)
        - limit: Max results (default: 100)
    """
    query = request.GET.get('q', '')
    activity_type = request.GET.get('type')
    business_id = request.GET.get('business_id')
    days = int(request.GET.get('days', 7))
    limit = min(int(request.GET.get('limit', 100)), 500)
    
    logger.info(f"[LEAD-LOGS] 🔍 Search request: q='{query}', type={activity_type}, business={business_id}")
    
    # Base query with time limit
    since = timezone.now() - timedelta(days=days)
    logs = LeadActivityLog.objects.filter(timestamp__gte=since)
    
    # Apply filters
    if query:
        logs = logs.filter(
            Q(message__icontains=query) |
            Q(lead_id__icontains=query) |
            Q(event_name__icontains=query)
        )
    
    if activity_type:
        logs = logs.filter(activity_type=activity_type.upper())
        
    if business_id:
        logs = logs.filter(business_id=business_id)
    
    # Get results
    logs = logs.order_by('-timestamp')[:limit]
    
    # Format response
    results = []
    for log in logs:
        results.append({
            'lead_id': log.lead_id,
            'timestamp': log.timestamp,
            'activity_type': log.activity_type,
            'component': log.component,
            'event_name': log.event_name,
            'message': log.message,
            'metadata': log.metadata
        })
    
    logger.info(f"[LEAD-LOGS] Search returned {len(results)} results")
    
    return Response({
        'query': query,
        'filters': {
            'type': activity_type,
            'business_id': business_id,
            'days': days,
            'limit': limit,
        },
        'total_results': len(results),
        'results': results
    })
