#!/usr/bin/env python
"""
Debug script to analyze the duplicate message issue.
Run with: python debug_lead.py GOG77uQay19ZN8Px6Vwt9g
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from webhooks.models import (
    LeadDetail, LeadEvent, LeadPendingTask, 
    AutoResponseSettings, ProcessedLead
)
from datetime import datetime

def analyze_lead(lead_id):
    print(f"🔍 ANALYZING LEAD: {lead_id}")
    print("=" * 60)
    
    # 1. LeadDetail
    try:
        lead = LeadDetail.objects.get(lead_id=lead_id)
        print(f"📊 LeadDetail found:")
        print(f"  - ID: {lead.pk}")
        print(f"  - Business ID: {lead.business_id}")
        print(f"  - User: {lead.user_display_name}")
        print(f"  - Created: {lead.created_at}")
        print(f"  - Updated: {lead.updated_at}")
        print(f"  - Phone opt-in: {lead.phone_opt_in}")
        print(f"  - Phone in text: {lead.phone_in_text}")
        print(f"  - Phone number: {lead.phone_number}")
        print(f"  - Project job_names: {lead.project.get('job_names', [])}")
        print(f"  - Jobs formatted: '{', '.join(lead.project.get('job_names', []))}'")
        print()
    except LeadDetail.DoesNotExist:
        print("❌ LeadDetail not found")
        return
    
    # 2. ProcessedLead
    try:
        processed = ProcessedLead.objects.get(lead_id=lead_id)
        print(f"📋 ProcessedLead found:")
        print(f"  - ID: {processed.pk}")
        print(f"  - Business ID: {processed.business_id}")
        print(f"  - Processed at: {processed.processed_at}")
        print()
    except ProcessedLead.DoesNotExist:
        print("❌ ProcessedLead not found")
    
    # 3. AutoResponseSettings for this business
    business_id = lead.business_id
    print(f"⚙️ AutoResponseSettings for business {business_id}:")
    
    scenarios = [
        (False, False, "NEW_LEAD"),
        (True, False, "PHONE_OPT_IN"), 
        (False, True, "PHONE_AVAILABLE")
    ]
    
    for phone_opt_in, phone_available, scenario in scenarios:
        # Business-specific
        biz_settings = AutoResponseSettings.objects.filter(
            business__business_id=business_id,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available
        ).first()
        
        # Default
        default_settings = AutoResponseSettings.objects.filter(
            business__isnull=True,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available
        ).first()
        
        used_settings = biz_settings if biz_settings else default_settings
        
        print(f"  {scenario} (opt_in={phone_opt_in}, available={phone_available}):")
        if used_settings:
            print(f"    ✅ Settings ID: {used_settings.id}")
            print(f"    📝 Type: {'Business' if biz_settings else 'Default'}")
            print(f"    🔛 Enabled: {used_settings.enabled}")
            print(f"    🤖 AI: {getattr(used_settings, 'use_ai_greeting', False)}")
            print(f"    📱 Template: {used_settings.greeting_template[:50]}...")
        else:
            print(f"    ❌ No settings found")
        print()
    
    # 4. LeadEvents 
    events = LeadEvent.objects.filter(lead_id=lead_id).order_by('time_created')
    print(f"📨 LeadEvents ({events.count()}):")
    for i, event in enumerate(events, 1):
        print(f"  {i}. ID: {event.pk}")
        print(f"     Event ID: {event.event_id}")
        print(f"     Type: {event.event_type}")
        print(f"     User: {event.user_type}")
        print(f"     Time: {event.time_created}")
        print(f"     From backend: {event.from_backend}")
        print(f"     Text: {event.text[:100]}...")
        print()
    
    # 5. LeadPendingTasks
    tasks = LeadPendingTask.objects.filter(lead_id=lead_id).order_by('-created_at')
    print(f"⏰ LeadPendingTasks ({tasks.count()}):")
    for i, task in enumerate(tasks, 1):
        print(f"  {i}. ID: {task.pk}")
        print(f"     Task ID: {task.task_id}")
        print(f"     Active: {task.active}")
        print(f"     Phone opt-in: {task.phone_opt_in}")
        print(f"     Phone available: {task.phone_available}")
        print(f"     Created: {task.created_at}")
        print(f"     Text: {task.text[:100]}...")
        print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_lead.py <lead_id>")
        sys.exit(1)
    
    lead_id = sys.argv[1]
    analyze_lead(lead_id) 