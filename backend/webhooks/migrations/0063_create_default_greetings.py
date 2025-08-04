# Generated manually to create default time-based greetings

from django.db import migrations


def create_default_greetings(apps, schema_editor):
    """Create default global time-based greetings"""
    TimeBasedGreeting = apps.get_model('webhooks', 'TimeBasedGreeting')
    
    # Check if global default already exists
    if not TimeBasedGreeting.objects.filter(business__isnull=True).exists():
        TimeBasedGreeting.objects.create(
            business=None,  # Global default
            morning_start='05:00',
            morning_end='12:00',
            afternoon_start='12:00',
            afternoon_end='17:00',
            evening_start='17:00',
            evening_end='21:00',
            morning_formal='Good morning',
            morning_casual='Morning!',
            afternoon_formal='Good afternoon',
            afternoon_casual='Hi',
            evening_formal='Good evening',
            evening_casual='Evening!',
            night_greeting='Hello',
            default_style='formal'
        )


def reverse_default_greetings(apps, schema_editor):
    """Remove default global time-based greetings"""
    TimeBasedGreeting = apps.get_model('webhooks', 'TimeBasedGreeting')
    TimeBasedGreeting.objects.filter(business__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0062_add_time_based_greeting'),
    ]

    operations = [
        migrations.RunPython(create_default_greetings, reverse_default_greetings),
    ]