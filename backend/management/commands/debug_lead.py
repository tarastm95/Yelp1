"""
Management command to debug lead processing and auto-response issues.
Usage: python manage.py debug_lead <lead_id>
"""
import os
import sys
import json
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.db import models
from webhooks.models import LeadEvent, LeadPendingTask, ProcessedLead


class Command(BaseCommand):
    help = 'Debug lead processing and show detailed analysis'

    def add_arguments(self, parser):
        parser.add_argument('lead_id', type=str, help='Lead ID to analyze')
        parser.add_argument(
            '--show-logs',
            action='store_true',
            help='Show filtered Docker logs for this lead'
        )
        parser.add_argument(
            '--show-events',
            action='store_true', 
            help='Show all LeadEvent records for this lead'
        )
        parser.add_argument(
            '--show-tasks',
            action='store_true',
            help='Show all pending tasks for this lead'
        )

    def handle(self, *args, **options):
        lead_id = options['lead_id']
        
        self.stdout.write(self.style.SUCCESS(f'🔍 DEBUGGING LEAD: {lead_id}'))
        self.stdout.write('=' * 80)
        
        # 1. Basic Lead Info
        self.show_lead_info(lead_id)
        
        # 2. LeadEvent Analysis
        if options.get('show_events', True):
            self.analyze_lead_events(lead_id)
        
        # 3. Pending Tasks Analysis  
        if options.get('show_tasks', True):
            self.analyze_pending_tasks(lead_id)
            
        # 4. Docker Logs (if requested)
        if options.get('show_logs'):
            self.show_docker_logs(lead_id)
            
        # 5. Auto-Response Detection Analysis
        self.analyze_auto_response_detection(lead_id)

    def show_lead_info(self, lead_id):
        self.stdout.write('\n📊 BASIC LEAD INFORMATION:')
        self.stdout.write('-' * 40)
        
        try:
            processed = ProcessedLead.objects.get(lead_id=lead_id)
            self.stdout.write(f'✅ ProcessedLead exists: ID={processed.id}')
            self.stdout.write(f'   Business ID: {processed.business_id}')
            self.stdout.write(f'   Processed at: {processed.processed_at}')
        except ProcessedLead.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ ProcessedLead does not exist'))
            
    def analyze_lead_events(self, lead_id):
        self.stdout.write('\n📝 LEADEVENT ANALYSIS:')
        self.stdout.write('-' * 40)
        
        events = LeadEvent.objects.filter(lead_id=lead_id).order_by('time_created')
        
        if not events:
            self.stdout.write(self.style.ERROR('❌ No LeadEvent records found'))
            return
            
        self.stdout.write(f'Total events: {events.count()}')
        
        biz_events = events.filter(user_type='BUSINESS')
        consumer_events = events.filter(user_type='CONSUMER')
        backend_events = events.filter(from_backend=True)
        
        self.stdout.write(f'BIZ events: {biz_events.count()}')
        self.stdout.write(f'CONSUMER events: {consumer_events.count()}') 
        self.stdout.write(f'from_backend=True events: {backend_events.count()}')
        
        self.stdout.write('\n🔍 BIZ EVENTS DETAILED ANALYSIS:')
        for i, event in enumerate(biz_events, 1):
            self.stdout.write(f'\n  Event #{i} (ID: {event.event_id}):')
            self.stdout.write(f'    from_backend: {event.from_backend}')
            self.stdout.write(f'    time_created: {event.time_created}')
            self.stdout.write(f'    text: "{event.text[:100]}..."')
            self.stdout.write(f'    raw backend_sent: {event.raw.get("backend_sent", "Not present")}')
            self.stdout.write(f'    raw task_id: {event.raw.get("task_id", "Not present")}')
            
            # Check if this should be from_backend=True
            if event.raw.get('backend_sent') and not event.from_backend:
                self.stdout.write(self.style.ERROR(f'    ⚠️  ISSUE: Has backend_sent=True but from_backend=False'))
                
    def analyze_pending_tasks(self, lead_id):
        self.stdout.write('\n⏰ PENDING TASKS ANALYSIS:')
        self.stdout.write('-' * 40)
        
        tasks = LeadPendingTask.objects.filter(lead_id=lead_id).order_by('created_at')
        
        if not tasks:
            self.stdout.write('❌ No LeadPendingTask records found')
            return
            
        active_tasks = tasks.filter(active=True)
        inactive_tasks = tasks.filter(active=False)
        
        self.stdout.write(f'Total tasks: {tasks.count()}')
        self.stdout.write(f'Active tasks: {active_tasks.count()}')
        self.stdout.write(f'Inactive tasks: {inactive_tasks.count()}')
        
        self.stdout.write('\n📋 TASK DETAILS:')
        for i, task in enumerate(tasks, 1):
            self.stdout.write(f'\n  Task #{i} (ID: {task.task_id}):')
            self.stdout.write(f'    active: {task.active}')
            self.stdout.write(f'    phone_available: {task.phone_available}')
            self.stdout.write(f'    created_at: {task.created_at}')
            self.stdout.write(f'    text: "{task.text[:100]}..."')
            
    def analyze_auto_response_detection(self, lead_id):
        self.stdout.write('\n🤖 AUTO-RESPONSE DETECTION ANALYSIS:')
        self.stdout.write('-' * 40)
        
        # Look for potential misidentified auto-responses
        biz_events = LeadEvent.objects.filter(
            lead_id=lead_id, 
            user_type='BUSINESS'
        ).order_by('time_created')
        
        issues_found = 0
        
        for event in biz_events:
            has_backend_sent = event.raw.get('backend_sent', False)
            has_task_id = 'task_id' in event.raw
            from_backend_value = event.from_backend
            
            # Check for inconsistencies
            if has_backend_sent and not from_backend_value:
                issues_found += 1
                self.stdout.write(f'\n  ⚠️  ISSUE #{issues_found}:')
                self.stdout.write(f'    Event ID: {event.event_id}')
                self.stdout.write(f'    Text: "{event.text[:50]}..."')
                self.stdout.write(f'    raw.backend_sent: {has_backend_sent}')
                self.stdout.write(f'    from_backend: {from_backend_value}')
                self.stdout.write(f'    PROBLEM: Should be from_backend=True!')
                
        if issues_found == 0:
            self.stdout.write('✅ No auto-response detection issues found')
        else:
            self.stdout.write(f'\n💥 FOUND {issues_found} AUTO-RESPONSE DETECTION ISSUE(S)')
            self.stdout.write('These events were sent by your backend but marked as manual!')
            
    def show_docker_logs(self, lead_id):
        self.stdout.write(f'\n📋 DOCKER LOGS FOR LEAD: {lead_id}')
        self.stdout.write('-' * 40)
        
        # Run docker-compose logs command
        import subprocess
        try:
            result = subprocess.run([
                'docker-compose', 'logs', '--no-color'
            ], capture_output=True, text=True, cwd='/var/www/yelp/backend')
            
            if result.returncode == 0:
                # Filter logs for this lead_id
                logs = result.stdout
                filtered_logs = []
                for line in logs.split('\n'):
                    if lead_id in line:
                        filtered_logs.append(line)
                        
                if filtered_logs:
                    self.stdout.write(f'Found {len(filtered_logs)} log entries:')
                    for log in filtered_logs[-20:]:  # Show last 20 entries
                        self.stdout.write(log)
                else:
                    self.stdout.write('❌ No logs found for this lead ID')
            else:
                self.stdout.write(f'Error running docker-compose logs: {result.stderr}')
                
        except Exception as e:
            self.stdout.write(f'Error accessing Docker logs: {e}')
