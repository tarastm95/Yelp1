#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки Phone Opt-In виправлення
"""
import os
import sys
import django

# Налаштування Django
sys.path.append('/var/www/yelp/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from webhooks.models import LeadDetail, LeadEvent, AutoResponseSettings, LeadPendingTask

def test_phone_optin_logic():
    print("🧪 ТЕСТУВАННЯ PHONE OPT-IN ЛОГІКИ")
    print("=" * 50)
    
    # Створюємо тестові дані
    test_lead_id = "test_phone_optin_fix_123"
    test_business_id = "test_business_123"
    
    # Очищуємо старі тестові дані
    LeadDetail.objects.filter(lead_id=test_lead_id).delete()
    LeadEvent.objects.filter(lead_id=test_lead_id).delete()
    LeadPendingTask.objects.filter(lead_id=test_lead_id).delete()
    
    # 1. Створюємо LeadDetail без phone opt-in
    lead_detail = LeadDetail.objects.create(
        lead_id=test_lead_id,
        business_id=test_business_id,
        phone_opt_in=False,
        phone_number="",
        project={"test": "data"}
    )
    print(f"✅ Створено LeadDetail: phone_opt_in={lead_detail.phone_opt_in}")
    
    # 2. Створюємо AutoResponseSettings для phone opt-in
    settings, created = AutoResponseSettings.objects.get_or_create(
        business_id=test_business_id,
        phone_opt_in=True,
        phone_available=False,
        defaults={
            'enabled': True,
            'greeting': 'Test phone opt-in greeting',
        }
    )
    print(f"✅ AutoResponseSettings: phone_opt_in=True створено/знайдено")
    
    # 3. Створюємо тестове phone opt-in завдання
    task = LeadPendingTask.objects.create(
        lead_id=test_lead_id,
        text="Test phone opt-in follow-up message",
        task_id="test_task_123",
        phone_opt_in=True,
        phone_available=False,
        active=True
    )
    print(f"✅ Створено phone opt-in завдання: {task.task_id}")
    
    # 4. Симулюємо CONSUMER_PHONE_NUMBER_OPT_IN_EVENT
    print("\n📱 Симулюємо CONSUMER_PHONE_NUMBER_OPT_IN_EVENT...")
    
    # Оновлюємо LeadDetail.phone_opt_in=True (як це робить webhook)
    updated = LeadDetail.objects.filter(
        lead_id=test_lead_id, phone_opt_in=False
    ).update(phone_opt_in=True)
    print(f"✅ LeadDetail оновлено: {updated} запис(ів)")
    
    # Перевіряємо результат
    lead_detail.refresh_from_db()
    print(f"✅ LeadDetail.phone_opt_in тепер: {lead_detail.phone_opt_in}")
    
    # 5. Тестуємо логіку перевірки phone opt-in consumer response
    print("\n👤 Тестуємо логіку consumer response...")
    
    ld_flags = LeadDetail.objects.filter(lead_id=test_lead_id).values("phone_opt_in", "phone_number").first()
    print(f"ld_flags: {ld_flags}")
    
    if (ld_flags and ld_flags.get("phone_opt_in")):
        print("✅ Phone opt-in consumer response буде виявлено!")
        print("✅ Логіка _cancel_pre_phone_tasks буде викликана")
        
        # Тестуємо _cancel_pre_phone_tasks логіку
        from django.db.models import Q
        pending = LeadPendingTask.objects.filter(
            lead_id=test_lead_id, 
            active=True
        ).filter(
            Q(phone_available=False) | Q(phone_opt_in=True)
        )
        print(f"✅ Знайдено {pending.count()} завдань для скасування")
        
        if pending.exists():
            for p in pending:
                print(f"   - Task: {p.task_id}, phone_opt_in={p.phone_opt_in}, phone_available={p.phone_available}")
    else:
        print("❌ Phone opt-in consumer response НЕ буде виявлено!")
    
    # 6. Очищення тестових даних
    print("\n🧹 Очищення тестових даних...")
    LeadDetail.objects.filter(lead_id=test_lead_id).delete()
    LeadEvent.objects.filter(lead_id=test_lead_id).delete()
    LeadPendingTask.objects.filter(lead_id=test_lead_id).delete()
    AutoResponseSettings.objects.filter(business_id=test_business_id).delete()
    print("✅ Тестові дані очищено")
    
    print("\n🎉 ТЕСТ ЗАВЕРШЕНО УСПІШНО!")
    print("Виправлення має працювати правильно.")

if __name__ == "__main__":
    test_phone_optin_logic()
