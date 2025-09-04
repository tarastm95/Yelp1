"""
Django management command для міграції Phone Opt-In до No Phone сценарію
"""
from django.core.management.base import BaseCommand
from webhooks.models import AutoResponseSettings, FollowUpTemplate, LeadPendingTask


class Command(BaseCommand):
    help = 'Мігрує всі Phone Opt-In записи до No Phone сценарію'

    def handle(self, *args, **options):
        self.stdout.write('🔍 АНАЛІЗ ПОТОЧНИХ ДАНИХ В БД:')
        self.stdout.write('=' * 50)
        
        # 1. Аналізуємо AutoResponseSettings
        all_settings = AutoResponseSettings.objects.all()
        self.stdout.write(f'📊 Всього AutoResponseSettings: {all_settings.count()}')
        
        phone_optin_settings = AutoResponseSettings.objects.filter(phone_opt_in=True)
        self.stdout.write(f'📱 З phone_opt_in=True: {phone_optin_settings.count()}')
        
        for setting in phone_optin_settings:
            self.stdout.write(f'   - ID={setting.id}, business={setting.business}, enabled={setting.enabled}')
        
        # 2. Аналізуємо FollowUpTemplate
        all_templates = FollowUpTemplate.objects.all()
        self.stdout.write(f'📊 Всього FollowUpTemplate: {all_templates.count()}')
        
        phone_optin_templates = FollowUpTemplate.objects.filter(phone_opt_in=True)
        self.stdout.write(f'📱 З phone_opt_in=True: {phone_optin_templates.count()}')
        
        for template in phone_optin_templates:
            self.stdout.write(f'   - ID={template.id}, name="{template.name}", business={template.business}')
        
        # 3. Аналізуємо активні LeadPendingTask
        all_tasks = LeadPendingTask.objects.filter(active=True)
        self.stdout.write(f'📊 Всього активних LeadPendingTask: {all_tasks.count()}')
        
        phone_optin_tasks = LeadPendingTask.objects.filter(phone_opt_in=True, active=True)
        self.stdout.write(f'📱 Активних з phone_opt_in=True: {phone_optin_tasks.count()}')
        
        for task in phone_optin_tasks[:5]:  # Показуємо тільки перші 5
            self.stdout.write(f'   - ID={task.id}, lead_id={task.lead_id}, text="{task.text[:30]}..."')
        
        self.stdout.write('')
        self.stdout.write('🚀 ПОЧИНАЄМО МІГРАЦІЮ:')
        self.stdout.write('=' * 50)
        
        # 4. Виконуємо міграцію
        
        # Мігруємо AutoResponseSettings
        self.stdout.write('🔄 Конвертуємо AutoResponseSettings...')
        updated_settings = AutoResponseSettings.objects.filter(phone_opt_in=True).update(phone_opt_in=False)
        self.stdout.write(self.style.SUCCESS(f'✅ Конвертовано {updated_settings} AutoResponseSettings з phone_opt_in=True → phone_opt_in=False'))
        
        # Мігруємо FollowUpTemplate
        self.stdout.write('🔄 Конвертуємо FollowUpTemplate...')
        updated_templates = FollowUpTemplate.objects.filter(phone_opt_in=True).update(phone_opt_in=False)
        self.stdout.write(self.style.SUCCESS(f'✅ Конвертовано {updated_templates} FollowUpTemplate з phone_opt_in=True → phone_opt_in=False'))
        
        # Мігруємо активні LeadPendingTask
        self.stdout.write('🔄 Конвертуємо активні LeadPendingTask...')
        updated_tasks = LeadPendingTask.objects.filter(phone_opt_in=True, active=True).update(phone_opt_in=False)
        self.stdout.write(self.style.SUCCESS(f'✅ Конвертовано {updated_tasks} активних LeadPendingTask з phone_opt_in=True → phone_opt_in=False'))
        
        self.stdout.write('')
        self.stdout.write('🎉 МІГРАЦІЯ ЗАВЕРШЕНА УСПІШНО!')
        self.stdout.write('=' * 50)
        self.stdout.write('✅ Всі Phone Opt-In записи конвертовано в No Phone сценарій')
        self.stdout.write('✅ Phone Opt-In шаблони тепер стали No Phone шаблонами')
        self.stdout.write('✅ Активні Phone Opt-In завдання тепер No Phone завдання')
        self.stdout.write('✅ Система готова до роботи з 2 сценаріями')
        
        # 5. Перевіряємо результат
        self.stdout.write('')
        self.stdout.write('🔍 ПЕРЕВІРКА ПІСЛЯ МІГРАЦІЇ:')
        self.stdout.write('=' * 30)
        
        remaining_optin_settings = AutoResponseSettings.objects.filter(phone_opt_in=True).count()
        remaining_optin_templates = FollowUpTemplate.objects.filter(phone_opt_in=True).count()
        remaining_optin_tasks = LeadPendingTask.objects.filter(phone_opt_in=True, active=True).count()
        
        self.stdout.write(f'📊 AutoResponseSettings з phone_opt_in=True: {remaining_optin_settings} (має бути 0)')
        self.stdout.write(f'📊 FollowUpTemplate з phone_opt_in=True: {remaining_optin_templates} (має бути 0)')
        self.stdout.write(f'📊 Активних LeadPendingTask з phone_opt_in=True: {remaining_optin_tasks} (має бути 0)')
        
        if remaining_optin_settings == 0 and remaining_optin_templates == 0 and remaining_optin_tasks == 0:
            self.stdout.write(self.style.SUCCESS('🎯 ✅ МІГРАЦІЯ ПОВНІСТЮ УСПІШНА!'))
            self.stdout.write(self.style.SUCCESS('🚀 Система готова до роботи з новою логікою'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Залишилися деякі phone_opt_in=True записи'))
            self.stdout.write(self.style.WARNING('Можливо потрібна додаткова перевірка'))
