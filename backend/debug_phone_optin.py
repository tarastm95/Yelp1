#!/usr/bin/env python3
"""
Діагностичний скрипт для перевірки Phone Opt-In проблем
"""
import os
import sys
import django

# Налаштування Django
sys.path.append('/var/www/yelp/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from webhooks.models import LeadDetail, LeadEvent, AutoResponseSettings, LeadPendingTask

def debug_lead_phone_optin(lead_id):
    print(f"🔍 ДІАГНОСТИКА PHONE OPT-IN для ліда: {lead_id}")
    print("=" * 60)
    
    # 1. Перевіряємо LeadDetail
    try:
        lead_detail = LeadDetail.objects.get(lead_id=lead_id)
        print(f"📋 LeadDetail знайдено:")
        print(f"   - business_id: {lead_detail.business_id}")
        print(f"   - phone_opt_in: {lead_detail.phone_opt_in}")
        print(f"   - phone_number: {lead_detail.phone_number}")
        print(f"   - phone_in_text: {getattr(lead_detail, 'phone_in_text', 'Not set')}")
        print(f"   - time_created: {lead_detail.time_created}")
    except LeadDetail.DoesNotExist:
        print("❌ LeadDetail НЕ знайдено!")
        return
    
    # 2. Перевіряємо AutoResponseSettings
    print(f"\n🎯 AutoResponseSettings для business_id: {lead_detail.business_id}")
    settings = AutoResponseSettings.objects.filter(business_id=lead_detail.business_id)
    for setting in settings:
        print(f"   - ID: {setting.id}, phone_opt_in: {setting.phone_opt_in}, phone_available: {setting.phone_available}, enabled: {setting.enabled}")
    
    # 3. Шукаємо CONSUMER_PHONE_NUMBER_OPT_IN_EVENT
    print(f"\n📱 Пошук CONSUMER_PHONE_NUMBER_OPT_IN_EVENT:")
    phone_optin_events = LeadEvent.objects.filter(
        lead_id=lead_id,
        event_type="CONSUMER_PHONE_NUMBER_OPT_IN_EVENT"
    ).order_by('time_created')
    
    if phone_optin_events.exists():
        print(f"   ✅ Знайдено {phone_optin_events.count()} CONSUMER_PHONE_NUMBER_OPT_IN_EVENT(s):")
        for event in phone_optin_events:
            print(f"      - event_id: {event.event_id}")
            print(f"      - time_created: {event.time_created}")
            print(f"      - user_type: {event.user_type}")
            print(f"      - text: '{event.text}'")
    else:
        print("   ❌ CONSUMER_PHONE_NUMBER_OPT_IN_EVENT НЕ знайдено!")
        print("   🔍 Це пояснює, чому phone_opt_in=False")
    
    # 4. Перевіряємо всі події для цього ліда
    print(f"\n📊 Всі події для ліда (останні 10):")
    all_events = LeadEvent.objects.filter(lead_id=lead_id).order_by('-time_created')[:10]
    for event in all_events:
        print(f"   - {event.event_type} | {event.user_type} | {event.time_created} | '{event.text[:50]}...'")
    
    # 5. Перевіряємо чи є consumer eventi
    print(f"\n👤 Consumer події:")
    consumer_events = LeadEvent.objects.filter(
        lead_id=lead_id,
        user_type="CONSUMER"
    ).order_by('time_created')
    
    for event in consumer_events:
        print(f"   - {event.event_type} | {event.time_created} | '{event.text[:50]}...'")
    
    # 6. Перевіряємо активні завдання
    print(f"\n📋 Активні завдання:")
    active_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
    for task in active_tasks:
        print(f"   - ID: {task.id}, phone_opt_in: {task.phone_opt_in}, phone_available: {task.phone_available}, text: '{task.text[:50]}...'")
    
    # 7. Рекомендації
    print(f"\n💡 РЕКОМЕНДАЦІЇ:")
    if not phone_optin_events.exists():
        print("   1. Споживач ніколи не погоджувався надати номер телефону")
        print("   2. Yelp не надіслав CONSUMER_PHONE_NUMBER_OPT_IN_EVENT")
        print("   3. Перевірте чи правильно налаштований webhook в Yelp")
        print("   4. Можливо потрібно попросити споживача знову погодитися на надання номера")
    else:
        print("   1. Phone opt-in події є, але LeadDetail.phone_opt_in=False")
        print("   2. Можливо проблема з обробкою webhook")
        print("   3. Перевірте логи webhook для цих подій")

if __name__ == "__main__":
    lead_id = "iUf11StqZaveuBxNIfDQ8w"  # Ваш проблемний лід
    debug_lead_phone_optin(lead_id)
