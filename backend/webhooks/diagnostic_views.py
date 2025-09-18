"""
Diagnostic and Error Tracking API endpoints.

Provides comprehensive system monitoring, error tracking, and diagnostic tools.
"""

import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import django_rq

from .models import SystemErrorLog, SystemHealthMetric, CeleryTaskLog, LeadDetail, LeadEvent
from .utils import get_system_health_summary, log_system_error, log_performance_metric

logger = logging.getLogger(__name__)


@api_view(['GET'])
def system_health_dashboard(request):
    """
    Comprehensive system health dashboard.
    
    Returns:
        - Overall health score
        - Error statistics  
        - Performance metrics
        - Queue status
        - Recent issues
    """
    logger.info("[DIAGNOSTIC] 🏥 System health dashboard request")
    
    try:
        # Get health summary
        health = get_system_health_summary()
        
        # Additional real-time data
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        
        # RQ Queue status
        try:
            queue = django_rq.get_queue('default')
            scheduler = django_rq.get_scheduler('default')
            
            queue_stats = {
                'pending_jobs': len(queue.get_jobs()),
                'scheduled_jobs': len(scheduler.get_jobs()),
                'failed_jobs': len(queue.failed_job_registry),
                'started_jobs': len(queue.started_job_registry),
            }
        except Exception as e:
            queue_stats = {'error': str(e)}
        
        # Recent critical errors
        critical_errors = SystemErrorLog.objects.filter(
            severity='CRITICAL',
            timestamp__gte=last_hour,
            resolved=False
        ).order_by('-timestamp')[:5]
        
        critical_errors_data = []
        for error in critical_errors:
            critical_errors_data.append({
                'error_id': error.error_id,
                'timestamp': error.timestamp,
                'error_type': error.error_type,
                'message': error.error_message,
                'component': error.component,
                'lead_id': error.lead_id,
            })
        
        # Database stats
        db_stats = {
            'total_leads': LeadDetail.objects.count(),
            'leads_today': LeadDetail.objects.filter(created_at__date=now.date()).count(),
            'total_events': LeadEvent.objects.count(),
            'events_today': LeadEvent.objects.filter(created_at__date=now.date()).count(),
        }
        
        logger.info(f"[DIAGNOSTIC] Health score: {health['health_score']}, Status: {health['status']}")
        
        return Response({
            'timestamp': now,
            'health': health,
            'queue': queue_stats,
            'critical_errors': critical_errors_data,
            'database': db_stats,
        })
        
    except Exception as e:
        log_system_error(
            error_type='API_ERROR',
            error_message=f"Failed to generate health dashboard: {str(e)}",
            exception=e,
            severity='HIGH'
        )
        return Response({
            'error': 'Failed to generate health dashboard',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def error_logs_dashboard(request):
    """
    Error tracking dashboard with filtering and search.
    
    Query Parameters:
        - type: Error type filter
        - severity: Severity filter (LOW, MEDIUM, HIGH, CRITICAL)
        - resolved: Filter by resolution status (true/false)
        - hours: How many hours back to search (default: 24)
        - limit: Max results (default: 50)
        - search: Search in error messages
    """
    logger.info("[DIAGNOSTIC] 🚨 Error logs dashboard request")
    logger.info(f"[DIAGNOSTIC] Query params: {dict(request.query_params)}")
    
    # Filters
    error_type = request.GET.get('type')
    severity = request.GET.get('severity')
    resolved = request.GET.get('resolved')
    hours = int(request.GET.get('hours', 24))
    limit = min(int(request.GET.get('limit', 50)), 200)
    search = request.GET.get('search')
    
    try:
        # Base query
        since = timezone.now() - timedelta(hours=hours)
        errors = SystemErrorLog.objects.filter(timestamp__gte=since)
        
        # Apply filters
        if error_type:
            errors = errors.filter(error_type=error_type.upper())
            
        if severity:
            errors = errors.filter(severity=severity.upper())
            
        if resolved is not None:
            resolved_bool = resolved.lower() == 'true'
            errors = errors.filter(resolved=resolved_bool)
            
        if search:
            errors = errors.filter(
                Q(error_message__icontains=search) |
                Q(exception_type__icontains=search) |
                Q(component__icontains=search)
            )
        
        # Get results
        errors = errors.order_by('-timestamp')[:limit]
        
        # Format response
        errors_data = []
        for error in errors:
            errors_data.append({
                'error_id': error.error_id,
                'timestamp': error.timestamp,
                'error_type': error.error_type,
                'severity': error.severity,
                'component': error.component,
                'function_name': error.function_name,
                'line_number': error.line_number,
                'error_message': error.error_message,
                'exception_type': error.exception_type,
                'traceback': error.traceback,
                'lead_id': error.lead_id,
                'business_id': error.business_id,
                'task_id': error.task_id,
                'metadata': error.metadata,
                'resolved': error.resolved,
                'resolved_at': error.resolved_at,
                'resolution_notes': error.resolution_notes,
            })
        
        # Summary statistics
        total_errors = SystemErrorLog.objects.filter(timestamp__gte=since).count()
        by_severity = SystemErrorLog.objects.filter(timestamp__gte=since).values('severity').annotate(count=Count('id'))
        by_type = SystemErrorLog.objects.filter(timestamp__gte=since).values('error_type').annotate(count=Count('id'))
        
        logger.info(f"[DIAGNOSTIC] Returning {len(errors_data)} errors out of {total_errors} total")
        
        return Response({
            'filters': {
                'type': error_type,
                'severity': severity,
                'resolved': resolved,
                'hours': hours,
                'search': search,
                'limit': limit,
            },
            'summary': {
                'total_errors': total_errors,
                'returned_count': len(errors_data),
                'by_severity': {item['severity']: item['count'] for item in by_severity},
                'by_type': {item['error_type']: item['count'] for item in by_type},
            },
            'errors': errors_data
        })
        
    except Exception as e:
        log_system_error(
            error_type='API_ERROR',
            error_message=f"Failed to fetch error logs: {str(e)}",
            exception=e,
            severity='MEDIUM'
        )
        return Response({
            'error': 'Failed to fetch error logs',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def resolve_error(request, error_id):
    """Mark an error as resolved with optional notes"""
    try:
        error = SystemErrorLog.objects.get(error_id=error_id)
        error.resolved = True
        error.resolved_at = timezone.now()
        error.resolution_notes = request.data.get('notes', '')
        error.save()
        
        logger.info(f"[DIAGNOSTIC] ✅ Error {error_id} marked as resolved")
        
        return Response({
            'error_id': error_id,
            'resolved': True,
            'resolved_at': error.resolved_at,
            'notes': error.resolution_notes
        })
        
    except SystemErrorLog.DoesNotExist:
        return Response({
            'error': f'Error {error_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Failed to resolve error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def performance_metrics_dashboard(request):
    """
    Performance metrics dashboard with trends and alerts.
    
    Query Parameters:
        - metric: Specific metric type
        - hours: Time range (default: 24)
        - business_id: Business filter
    """
    metric_type = request.GET.get('metric')
    hours = int(request.GET.get('hours', 24))
    business_id = request.GET.get('business_id')
    
    logger.info(f"[DIAGNOSTIC] 📊 Performance metrics request: metric={metric_type}, hours={hours}")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Base query
        metrics = SystemHealthMetric.objects.filter(timestamp__gte=since)
        
        if metric_type:
            metrics = metrics.filter(metric_type=metric_type.upper())
            
        if business_id:
            metrics = metrics.filter(business_id=business_id)
        
        # Get trends
        metrics_data = []
        for metric in metrics.order_by('-timestamp')[:100]:
            metrics_data.append({
                'timestamp': metric.timestamp,
                'metric_type': metric.metric_type,
                'value': metric.value,
                'unit': metric.unit,
                'component': metric.component,
                'metadata': metric.metadata
            })
        
        # Calculate averages
        avg_data = {}
        for mt in ['API_RESPONSE_TIME', 'QUEUE_LENGTH', 'MEMORY_USAGE']:
            avg = SystemHealthMetric.objects.filter(
                metric_type=mt,
                timestamp__gte=since
            ).aggregate(avg_value=Avg('value'))['avg_value']
            
            if avg is not None:
                avg_data[mt] = round(avg, 2)
        
        # Current RQ status  
        try:
            queue = django_rq.get_queue('default')
            current_queue_length = len(queue.get_jobs())
            
            # Log current queue length as metric
            log_performance_metric(
                metric_type='QUEUE_LENGTH',
                value=current_queue_length,
                component='RQ_QUEUE'
            )
        except Exception as e:
            current_queue_length = -1
        
        return Response({
            'time_range_hours': hours,
            'filters': {
                'metric_type': metric_type,
                'business_id': business_id
            },
            'current_status': {
                'queue_length': current_queue_length,
                'timestamp': timezone.now()
            },
            'averages': avg_data,
            'metrics': metrics_data,
            'total_metrics': len(metrics_data)
        })
        
    except Exception as e:
        log_system_error(
            error_type='API_ERROR',
            error_message=f"Failed to fetch performance metrics: {str(e)}",
            exception=e,
            severity='MEDIUM'
        )
        return Response({
            'error': 'Failed to fetch performance metrics',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def diagnostic_action(request):
    """
    Execute diagnostic actions like retry failed tasks, refresh tokens, etc.
    
    Body:
        action: Action type (retry_failed_tasks, refresh_tokens, test_yelp_api)
        parameters: Action-specific parameters
    """
    action = request.data.get('action')
    parameters = request.data.get('parameters', {})
    
    logger.info(f"[DIAGNOSTIC] 🔧 Diagnostic action request: {action}")
    
    try:
        if action == 'retry_failed_tasks':
            # Retry recent failed tasks
            hours = parameters.get('hours', 1)
            since = timezone.now() - timedelta(hours=hours)
            
            failed_tasks = CeleryTaskLog.objects.filter(
                status='FAILURE',
                finished_at__gte=since
            )
            
            retry_count = 0
            queue = django_rq.get_queue('default')
            
            for task in failed_tasks[:10]:  # Limit to 10 retries
                if task.name == 'webhooks.tasks.send_follow_up' and len(task.args) >= 2:
                    try:
                        queue.enqueue(
                            'webhooks.tasks.send_follow_up',
                            task.args[0],  # lead_id
                            task.args[1],  # text
                            business_id=task.kwargs.get('business_id')
                        )
                        retry_count += 1
                    except Exception as e:
                        logger.error(f"[DIAGNOSTIC] Failed to retry task {task.task_id}: {e}")
            
            return Response({
                'action': action,
                'result': f'Retried {retry_count} failed tasks',
                'details': {
                    'total_failed': failed_tasks.count(),
                    'retried': retry_count,
                    'hours_back': hours
                }
            })
            
        elif action == 'test_yelp_api':
            # Test Yelp API connectivity
            import requests
            from .utils import get_valid_business_token
            
            try:
                # Test with first available token
                business_id = parameters.get('business_id')
                if business_id:
                    token = get_valid_business_token(business_id)
                    test_url = "https://api.yelp.com/v3/businesses/search"
                    
                    start_time = timezone.now()
                    resp = requests.get(
                        test_url,
                        headers={'Authorization': f'Bearer {token}'},
                        params={'location': 'test'},
                        timeout=10
                    )
                    response_time = (timezone.now() - start_time).total_seconds() * 1000
                    
                    # Log performance metric
                    log_performance_metric(
                        metric_type='API_RESPONSE_TIME',
                        value=response_time,
                        unit='ms',
                        component='YELP_API_TEST'
                    )
                    
                    return Response({
                        'action': action,
                        'result': 'Yelp API test successful',
                        'details': {
                            'status_code': resp.status_code,
                            'response_time_ms': round(response_time, 2),
                            'business_id': business_id
                        }
                    })
                else:
                    return Response({
                        'action': action,
                        'error': 'business_id parameter required'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                log_system_error(
                    error_type='API_ERROR',
                    error_message=f"Yelp API test failed: {str(e)}",
                    exception=e,
                    severity='HIGH',
                    business_id=business_id
                )
                return Response({
                    'action': action,
                    'result': 'Yelp API test failed',
                    'error': str(e)
                })
                
        elif action == 'clear_old_errors':
            # Clear resolved errors older than X days
            days = parameters.get('days', 7)
            cutoff = timezone.now() - timedelta(days=days)
            
            deleted_count, _ = SystemErrorLog.objects.filter(
                resolved=True,
                timestamp__lt=cutoff
            ).delete()
            
            return Response({
                'action': action,
                'result': f'Cleared {deleted_count} old resolved errors',
                'details': {
                    'days_back': days,
                    'deleted_count': deleted_count
                }
            })
            
        else:
            return Response({
                'error': f'Unknown action: {action}',
                'available_actions': [
                    'retry_failed_tasks',
                    'test_yelp_api', 
                    'clear_old_errors'
                ]
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        log_system_error(
            error_type='API_ERROR',
            error_message=f"Diagnostic action failed: {action} - {str(e)}",
            exception=e,
            severity='HIGH'
        )
        return Response({
            'error': 'Diagnostic action failed',
            'action': action,
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def lead_diagnostic_report(request, lead_id):
    """
    Comprehensive diagnostic report for a specific lead.
    
    Analyzes:
        - Timeline completeness
        - Timing issues
        - Error patterns
        - Success/failure analysis
    """
    logger.info(f"[DIAGNOSTIC] 📋 Lead diagnostic report for: {lead_id}")
    
    try:
        # Collect all data for lead
        lead_detail = LeadDetail.objects.filter(lead_id=lead_id).first()
        tasks = CeleryTaskLog.objects.filter(args__contains=[lead_id]).order_by('eta')
        events = LeadEvent.objects.filter(lead_id=lead_id).order_by('time_created')
        errors = SystemErrorLog.objects.filter(lead_id=lead_id).order_by('-timestamp')
        
        # Analysis
        analysis = {
            'lead_exists': bool(lead_detail),
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status='SUCCESS').count(),
            'failed_tasks': tasks.filter(status='FAILURE').count(),
            'scheduled_tasks': tasks.filter(status='SCHEDULED').count(),
            'total_events': events.count(),
            'total_errors': errors.count(),
        }
        
        # Timing analysis
        timing_issues = []
        if tasks.count() > 1:
            task_times = [(task.eta, task.finished_at, task.status) for task in tasks if task.eta]
            for i, (eta, finished, status) in enumerate(task_times):
                if finished and eta:
                    delay = (finished - eta).total_seconds()
                    if abs(delay) > 60:  # More than 1 minute off
                        timing_issues.append({
                            'task_index': i + 1,
                            'expected_time': eta,
                            'actual_time': finished,
                            'delay_seconds': round(delay, 1),
                            'status': status
                        })
        
        # Error patterns
        error_patterns = []
        for error in errors[:5]:
            error_patterns.append({
                'timestamp': error.timestamp,
                'type': error.error_type,
                'severity': error.severity,
                'message': error.error_message,
                'resolved': error.resolved
            })
        
        # Success rate calculation
        if analysis['total_tasks'] > 0:
            success_rate = (analysis['completed_tasks'] / analysis['total_tasks']) * 100
        else:
            success_rate = 0
            
        # Health assessment
        health_status = 'HEALTHY'
        issues = []
        
        if analysis['failed_tasks'] > 0:
            health_status = 'WARNING'
            issues.append(f"{analysis['failed_tasks']} failed tasks")
            
        if analysis['total_errors'] > 0:
            health_status = 'ERROR'
            issues.append(f"{analysis['total_errors']} errors logged")
            
        if len(timing_issues) > 0:
            health_status = 'WARNING'
            issues.append(f"{len(timing_issues)} timing issues")
            
        if not lead_detail:
            health_status = 'ERROR'
            issues.append('Lead not found in database')
        
        return Response({
            'lead_id': lead_id,
            'lead_info': {
                'name': lead_detail.user_display_name if lead_detail else None,
                'jobs': lead_detail.project.get('job_names', []) if lead_detail and lead_detail.project else [],
                'created_at': lead_detail.created_at if lead_detail else None,
                'phone_number': lead_detail.phone_number if lead_detail else None,
            } if lead_detail else None,
            'health_status': health_status,
            'issues': issues,
            'analysis': analysis,
            'success_rate': round(success_rate, 1),
            'timing_issues': timing_issues,
            'error_patterns': error_patterns,
            'recommendations': generate_recommendations(analysis, timing_issues, error_patterns)
        })
        
    except Exception as e:
        log_system_error(
            error_type='API_ERROR',
            error_message=f"Failed to generate diagnostic report for lead {lead_id}: {str(e)}",
            exception=e,
            severity='MEDIUM',
            lead_id=lead_id
        )
        return Response({
            'error': 'Failed to generate diagnostic report',
            'lead_id': lead_id,
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def generate_recommendations(analysis, timing_issues, error_patterns) -> list:
    """Generate actionable recommendations based on analysis"""
    recommendations = []
    
    if analysis['failed_tasks'] > 0:
        recommendations.append({
            'type': 'ERROR',
            'title': 'Failed Tasks Detected',
            'description': f"{analysis['failed_tasks']} tasks failed execution",
            'action': 'Check task logs and retry if needed',
            'severity': 'HIGH' if analysis['failed_tasks'] > 2 else 'MEDIUM'
        })
    
    if len(timing_issues) > 0:
        avg_delay = sum(issue['delay_seconds'] for issue in timing_issues) / len(timing_issues)
        recommendations.append({
            'type': 'TIMING',
            'title': 'Timing Issues Found',
            'description': f"Average delay: {avg_delay:.1f} seconds",
            'action': 'Check RQ Scheduler configuration and server load',
            'severity': 'HIGH' if avg_delay > 300 else 'MEDIUM'
        })
    
    if len(error_patterns) > 0:
        critical_errors = [e for e in error_patterns if e['severity'] == 'CRITICAL']
        if critical_errors:
            recommendations.append({
                'type': 'CRITICAL',
                'title': 'Critical Errors Present',
                'description': f"{len(critical_errors)} critical errors need attention",
                'action': 'Review error logs and fix underlying issues',
                'severity': 'CRITICAL'
            })
    
    if analysis['total_tasks'] == 0:
        recommendations.append({
            'type': 'WARNING',
            'title': 'No Tasks Found',
            'description': 'Lead has no follow-up tasks scheduled or executed',
            'action': 'Check follow-up template configuration',
            'severity': 'MEDIUM'
        })
    
    # Add positive feedback
    success_rate = (analysis['completed_tasks'] / analysis['total_tasks'] * 100) if analysis['total_tasks'] > 0 else 0
    if success_rate >= 95:
        recommendations.append({
            'type': 'SUCCESS',
            'title': 'Excellent Performance',
            'description': f"Success rate: {success_rate:.1f}%",
            'action': 'System performing well',
            'severity': 'LOW'
        })
    
    return recommendations


@api_view(['GET'])
def system_status_check(request):
    """Quick system status check for monitoring"""
    try:
        # Quick health checks
        checks = {
            'database': False,
            'redis': False,
            'yelp_api': False,
            'recent_activity': False
        }
        
        # Database check
        try:
            LeadDetail.objects.count()
            checks['database'] = True
        except Exception:
            pass
        
        # Redis check
        try:
            queue = django_rq.get_queue('default')
            len(queue.get_jobs())
            checks['redis'] = True
        except Exception:
            pass
        
        # Recent activity check
        recent = timezone.now() - timedelta(minutes=30)
        recent_activity = CeleryTaskLog.objects.filter(finished_at__gte=recent).exists()
        checks['recent_activity'] = recent_activity
        
        # Overall status
        all_green = all(checks.values())
        status_text = 'OPERATIONAL' if all_green else 'ISSUES'
        
        return Response({
            'status': status_text,
            'timestamp': timezone.now(),
            'checks': checks,
            'all_systems_operational': all_green
        })
        
    except Exception as e:
        return Response({
            'status': 'ERROR',
            'error': str(e),
            'timestamp': timezone.now()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
