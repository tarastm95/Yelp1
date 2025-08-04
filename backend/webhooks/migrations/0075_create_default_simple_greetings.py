# Create default global greeting settings

from django.db import migrations


def create_default_greetings(apps, schema_editor):
    """Create default global greeting settings if none exist"""
    TimeBasedGreeting = apps.get_model('webhooks', 'TimeBasedGreeting')
    
    # Only create if no global settings exist
    if not TimeBasedGreeting.objects.filter(business__isnull=True).exists():
        TimeBasedGreeting.objects.create(
            business=None,
            morning_start='05:00',
            morning_end='12:00',
            afternoon_start='12:00',
            afternoon_end='17:00',
            evening_start='17:00',
            evening_end='21:00',
            morning_greeting='Good morning',
            afternoon_greeting='Good afternoon',
            evening_greeting='Good evening',
            night_greeting='Hello'
        )


def remove_default_greetings(apps, schema_editor):
    """Remove default greetings"""
    TimeBasedGreeting = apps.get_model('webhooks', 'TimeBasedGreeting')
    TimeBasedGreeting.objects.filter(business__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0074_simplify_time_based_greetings'),
    ]

    operations = [
        migrations.RunPython(create_default_greetings, remove_default_greetings),
    ]