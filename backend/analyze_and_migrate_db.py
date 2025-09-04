#!/usr/bin/env python3
"""
Аналізує та мігрує phone_opt_in дані в базі
"""
import os
import sys
import django

# Налаштування Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from webhooks.models import AutoResponseSettings, FollowUpTemplate, LeadPendingTask

def analyze_and_migrate():
    print('🔍 АНАЛІЗ ПОТОЧНИХ ДАНИХ В БД:')
    print('=' * 50)
    
    # 1. Аналізуємо AutoResponseSettings
    all_settings = AutoResponseSettings.objects.all()
    print(f'📊 Всього AutoResponseSettings: {all_settings.count()}')
    
    phone_optin_settings = AutoResponseSettings.objects.filter(phone_opt_in=True)
    print(f'📱 З phone_opt_in=True: {phone_optin_settings.count()}')
    
    for setting in phone_optin_settings:
        print(f'   - ID={setting.id}, business={setting.business}, enabled={setting.enabled}')
    
    # 2. Аналізуємо FollowUpTemplate
    all_templates = FollowUpTemplate.objects.all()
    print(f'📊 Всього FollowUpTemplate: {all_templates.count()}')
    
    phone_optin_templates = FollowUpTemplate.objects.filter(phone_opt_in=True)
    print(f'📱 З phone_opt_in=True: {phone_optin_templates.count()}')
    
    for template in phone_optin_templates:
        print(f'   - ID={template.id}, name="{template.name}", business={template.business}')
    
    # 3. Аналізуємо активні LeadPendingTask
    all_tasks = LeadPendingTask.objects.filter(active=True)
    print(f'📊 Всього активних LeadPendingTask: {all_tasks.count()}')
    
    phone_optin_tasks = LeadPendingTask.objects.filter(phone_opt_in=True, active=True)
    print(f'📱 Активних з phone_opt_in=True: {phone_optin_tasks.count()}')
    
    for task in phone_optin_tasks[:5]:  # Показуємо тільки перші 5
        print(f'   - ID={task.id}, lead_id={task.lead_id}, text="{task.text[:30]}..."')
    
    print()
    print('🚀 ПОЧИНАЄМО МІГРАЦІЮ:')
    print('=' * 50)
    
    # 4. Виконуємо міграцію
    
    # Мігруємо AutoResponseSettings
    print('🔄 Конвертуємо AutoResponseSettings...')
    updated_settings = AutoResponseSettings.objects.filter(phone_opt_in=True).update(phone_opt_in=False)
    print(f'✅ Конвертовано {updated_settings} AutoResponseSettings з phone_opt_in=True → phone_opt_in=False')
    
    # Мігруємо FollowUpTemplate
    print('🔄 Конвертуємо FollowUpTemplate...')
    updated_templates = FollowUpTemplate.objects.filter(phone_opt_in=True).update(phone_opt_in=False)
    print(f'✅ Конвертовано {updated_templates} FollowUpTemplate з phone_opt_in=True → phone_opt_in=False')
    
    # Мігруємо активні LeadPendingTask
    print('🔄 Конвертуємо активні LeadPendingTask...')
    updated_tasks = LeadPendingTask.objects.filter(phone_opt_in=True, active=True).update(phone_opt_in=False)
    print(f'✅ Конвертовано {updated_tasks} активних LeadPendingTask з phone_opt_in=True → phone_opt_in=False')
    
    print()
    print('🎉 МІГРАЦІЯ ЗАВЕРШЕНА УСПІШНО!')
    print('=' * 50)
    print('✅ Всі Phone Opt-In записи конвертовано в No Phone сценарій')
    print('✅ Phone Opt-In шаблони тепер стали No Phone шаблонами')
    print('✅ Активні Phone Opt-In завдання тепер No Phone завдання')
    print('✅ Система готова до роботи з 2 сценаріями')
    
    # 5. Перевіряємо результат
    print()
    print('🔍 ПЕРЕВІРКА ПІСЛЯ МІГРАЦІЇ:')
    print('=' * 30)
    
    remaining_optin_settings = AutoResponseSettings.objects.filter(phone_opt_in=True).count()
    remaining_optin_templates = FollowUpTemplate.objects.filter(phone_opt_in=True).count()
    remaining_optin_tasks = LeadPendingTask.objects.filter(phone_opt_in=True, active=True).count()
    
    print(f'📊 AutoResponseSettings з phone_opt_in=True: {remaining_optin_settings} (має бути 0)')
    print(f'📊 FollowUpTemplate з phone_opt_in=True: {remaining_optin_templates} (має бути 0)')
    print(f'📊 Активних LeadPendingTask з phone_opt_in=True: {remaining_optin_tasks} (має бути 0)')
    
    if remaining_optin_settings == 0 and remaining_optin_templates == 0 and remaining_optin_tasks == 0:
        print('🎯 ✅ МІГРАЦІЯ ПОВНІСТЮ УСПІШНА!')
    else:
        print('⚠️ Залишилися деякі phone_opt_in=True записи')

if __name__ == '__main__':
    analyze_and_migrate()
