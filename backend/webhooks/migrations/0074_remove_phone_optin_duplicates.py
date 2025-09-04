# Generated migration for removing phone_opt_in duplicates after unifying scenarios

from django.db import migrations
from django.db.models import Count


def remove_phone_optin_duplicates(apps, schema_editor):
    """
    Видаляє всі Phone Opt-In та Phone Available шаблони/налаштування,
    залишаючи тільки No Phone (phone_available=False) після об'єднання сценаріїв
    """
    FollowUpTemplate = apps.get_model('webhooks', 'FollowUpTemplate')
    AutoResponseSettings = apps.get_model('webhooks', 'AutoResponseSettings')
    
    print("\n🧹 ОЧИЩЕННЯ PHONE OPT-IN ТА PHONE AVAILABLE ЗАПИСІВ")
    print("=" * 60)
    print("🎯 Залишаємо тільки No Phone шаблони (phone_available=False)")
    print("🗑️ Видаляємо всі Phone Available шаблони (phone_available=True)")
    print("=" * 60)
    
    # 1. FollowUpTemplate: Видаляємо всі phone_available=True записи
    print("\n📋 Очищення FollowUpTemplate...")
    
    phone_available_templates = FollowUpTemplate.objects.filter(phone_available=True)
    phone_available_count = phone_available_templates.count()
    
    if phone_available_count > 0:
        print(f"   🗑️ Видаляємо {phone_available_count} Phone Available шаблонів...")
        phone_available_templates.delete()
        print(f"   ✅ Видалено {phone_available_count} Phone Available шаблонів")
    else:
        print("   ℹ️  Phone Available шаблонів не знайдено")
    
    # Очищаємо дублікати серед No Phone шаблонів (phone_available=False)
    print("   🔄 Очищення дублікатів серед No Phone шаблонів...")
    
    no_phone_duplicates = FollowUpTemplate.objects.filter(
        phone_available=False
    ).values(
        'business_id', 'name', 'template', 'delay'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    total_deleted_no_phone = 0
    
    for dup in no_phone_duplicates:
        copies = FollowUpTemplate.objects.filter(
            business_id=dup['business_id'],
            name=dup['name'],
            template=dup['template'],
            delay=dup['delay'],
            phone_available=False
        ).order_by('id')
        
        if copies.count() > 1:
            # Залишаємо найстарший (найменший ID)
            to_keep = copies.first()
            to_delete = copies.exclude(id=to_keep.id)
            
            deleted_count = to_delete.count()
            to_delete.delete()
            total_deleted_no_phone += deleted_count
            
            print(f"   🗑️ Видалено {deleted_count} дублікатів No Phone для '{dup['name']}'")
    
    print(f"   ✅ FollowUpTemplate: видалено {phone_available_count} Phone Available + {total_deleted_no_phone} дублікатів No Phone")
    
    # 2. AutoResponseSettings: Видаляємо всі phone_available=True записи
    print("\n📋 Очищення AutoResponseSettings...")
    
    phone_available_settings = AutoResponseSettings.objects.filter(phone_available=True)
    phone_available_settings_count = phone_available_settings.count()
    
    if phone_available_settings_count > 0:
        print(f"   🗑️ Видаляємо {phone_available_settings_count} Phone Available налаштувань...")
        phone_available_settings.delete()
        print(f"   ✅ Видалено {phone_available_settings_count} Phone Available налаштувань")
    else:
        print("   ℹ️  Phone Available налаштувань не знайдено")
    
    # Очищаємо дублікати серед No Phone налаштувань (phone_available=False)
    print("   🔄 Очищення дублікатів серед No Phone налаштувань...")
    
    no_phone_settings_duplicates = AutoResponseSettings.objects.filter(
        phone_available=False
    ).values(
        'business_id'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    total_deleted_no_phone_settings = 0
    
    for dup in no_phone_settings_duplicates:
        copies = AutoResponseSettings.objects.filter(
            business_id=dup['business_id'],
            phone_available=False
        ).order_by('id')
        
        if copies.count() > 1:
            # Залишаємо найстарший (найменший ID)
            to_keep = copies.first()
            to_delete = copies.exclude(id=to_keep.id)
            
            deleted_count = to_delete.count()
            to_delete.delete()
            total_deleted_no_phone_settings += deleted_count
            
            business_name = "Global" if not dup['business_id'] else f"Business {dup['business_id']}"
            print(f"   🗑️ Видалено {deleted_count} дублікатів No Phone для '{business_name}'")
    
    print(f"   ✅ AutoResponseSettings: видалено {phone_available_settings_count} Phone Available + {total_deleted_no_phone_settings} дублікатів No Phone")
    
    # 3. Очищення LeadPendingTask старих phone_available=True завдань
    print("\n📋 Очищення LeadPendingTask старих записів...")
    
    LeadPendingTask = apps.get_model('webhooks', 'LeadPendingTask')
    
    # Видаляємо всі phone_available=True завдання (старі Phone Available)
    phone_available_tasks = LeadPendingTask.objects.filter(phone_available=True)
    phone_available_tasks_count = phone_available_tasks.count()
    
    if phone_available_tasks_count > 0:
        phone_available_tasks.delete()
        print(f"   🗑️ Видалено {phone_available_tasks_count} Phone Available завдань")
    
    # Видаляємо неактивні старі завдання
    old_inactive_tasks = LeadPendingTask.objects.filter(active=False)
    inactive_count = old_inactive_tasks.count()
    
    if inactive_count > 0:
        old_inactive_tasks.delete()
        print(f"   🗑️ Видалено {inactive_count} неактивних старих завдань")
    
    # 4. Детальний звіт
    remaining_templates = FollowUpTemplate.objects.count()
    remaining_no_phone_templates = FollowUpTemplate.objects.filter(phone_available=False).count()
    remaining_settings = AutoResponseSettings.objects.count()
    remaining_no_phone_settings = AutoResponseSettings.objects.filter(phone_available=False).count()
    remaining_tasks = LeadPendingTask.objects.filter(phone_available=False).count()
    
    print(f"\n📊 ПІДСУМОК ПІСЛЯ ОЧИЩЕННЯ:")
    print(f"   FollowUpTemplate: {remaining_templates} записів (всі No Phone: {remaining_no_phone_templates})")
    print(f"   AutoResponseSettings: {remaining_settings} записів (всі No Phone: {remaining_no_phone_settings})")
    print(f"   LeadPendingTask: {remaining_tasks} No Phone завдань залишилося")
    print(f"\n🗑️  ВСЬОГО ВИДАЛЕНО:")
    print(f"   Phone Available шаблонів: {phone_available_count}")
    print(f"   Phone Available налаштувань: {phone_available_settings_count}")
    print(f"   Phone Available завдань: {phone_available_tasks_count}")
    print(f"   Дублікатів No Phone шаблонів: {total_deleted_no_phone}")
    print(f"   Дублікатів No Phone налаштувань: {total_deleted_no_phone_settings}")
    print(f"   Неактивних завдань: {inactive_count}")
    print(f"\n✅ Тепер тільки No Phone шаблони використовуються для всіх сценаріїв!")
    print("   📱 Phone Opt-In ліди будуть користуватися No Phone шаблонами")


def reverse_migration(apps, schema_editor):
    """
    Не можна відновити видалені дублікати
    """
    print("⚠️  Відкат цієї міграції неможливий - дублікати були видалені назавжди")
    print("   Це нормально, оскільки видалялися тільки дублікати, а не унікальні дані")


class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0073_jobmapping_remove_leadpendingtask_uniq_lead_text_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=remove_phone_optin_duplicates,
            reverse_code=reverse_migration,
        ),
    ]
