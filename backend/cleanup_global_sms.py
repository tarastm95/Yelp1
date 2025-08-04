#!/usr/bin/env python3
"""
Скрипт для удаления глобальных SMS настроек из базы данных.
Оставляет только бизнес-специфичные настройки.

Запуск:
python manage.py shell < cleanup_global_sms.py
или
python cleanup_global_sms.py
"""

import os
import sys
import django

# Настройка Django environment
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yelp_project.settings')
    django.setup()

from webhooks.models import NotificationSetting

def cleanup_global_sms_settings():
    """
    Удаляет все глобальные SMS настройки (business=NULL)
    """
    print("🧹 CLEANUP: Удаление глобальных SMS настроек")
    print("=" * 50)
    
    # Найти все глобальные настройки
    global_settings = NotificationSetting.objects.filter(business__isnull=True)
    count = global_settings.count()
    
    print(f"📊 Найдено глобальных SMS настроек: {count}")
    
    if count == 0:
        print("✅ Глобальных настроек не найдено. База данных уже очищена.")
        return
    
    # Показать детали настроек которые будут удалены
    print("\n📋 Настройки для удаления:")
    for i, setting in enumerate(global_settings, 1):
        print(f"  {i}. ID: {setting.id}")
        print(f"     Телефон: {setting.phone_number}")
        print(f"     Шаблон: {setting.message_template[:50]}...")
        print(f"     Бизнес: {setting.business or 'Global (NULL)'}")
        print()
    
    # Подтверждение
    response = input(f"⚠️  Удалить {count} глобальных SMS настроек? (yes/no): ")
    
    if response.lower() in ['yes', 'y', 'да', 'д']:
        # Удаление
        deleted_count, _ = global_settings.delete()
        print(f"✅ Удалено {deleted_count} глобальных SMS настроек")
        
        # Проверка оставшихся настроек
        remaining = NotificationSetting.objects.count()
        business_specific = NotificationSetting.objects.filter(business__isnull=False).count()
        
        print(f"📊 Статистика после очистки:")
        print(f"   - Всего настроек: {remaining}")
        print(f"   - Бизнес-специфичных: {business_specific}")
        print(f"   - Глобальных: {remaining - business_specific}")
        
        if remaining == business_specific:
            print("🎉 База данных успешно очищена! Остались только бизнес-специфичные настройки.")
        else:
            print("⚠️  Остались некоторые глобальные настройки. Проверьте базу данных.")
            
    else:
        print("❌ Операция отменена. Настройки не удалены.")

def show_current_settings():
    """
    Показывает текущие настройки в базе данных
    """
    print("📊 ТЕКУЩИЕ SMS НАСТРОЙКИ")
    print("=" * 50)
    
    total = NotificationSetting.objects.count()
    business_specific = NotificationSetting.objects.filter(business__isnull=False).count()
    global_settings = NotificationSetting.objects.filter(business__isnull=True).count()
    
    print(f"Всего настроек: {total}")
    print(f"Бизнес-специфичных: {business_specific}")
    print(f"Глобальных: {global_settings}")
    print()
    
    if global_settings > 0:
        print("🌍 Глобальные настройки:")
        for setting in NotificationSetting.objects.filter(business__isnull=True):
            print(f"  - ID: {setting.id}, Телефон: {setting.phone_number}")
    
    if business_specific > 0:
        print("🏢 Бизнес-специфичные настройки:")
        for setting in NotificationSetting.objects.filter(business__isnull=False):
            business_name = setting.business.name if setting.business else "Unknown"
            print(f"  - ID: {setting.id}, Телефон: {setting.phone_number}, Бизнес: {business_name}")

if __name__ == "__main__":
    print("🗂️  SMS SETTINGS CLEANUP UTILITY")
    print("=" * 50)
    
    # Показать текущее состояние
    show_current_settings()
    print()
    
    # Выполнить очистку
    cleanup_global_sms_settings()
    
    print("\n🏁 Готово!")