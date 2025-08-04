# Generated manually for simplifying time-based greetings

from django.db import migrations, models


def migrate_greetings_data(apps, schema_editor):
    """Migrate data from old formal/casual fields to new simple greeting fields"""
    TimeBasedGreeting = apps.get_model('webhooks', 'TimeBasedGreeting')
    
    for greeting in TimeBasedGreeting.objects.all():
        # Choose formal or casual based on default_style, fallback to formal
        style = getattr(greeting, 'default_style', 'formal')
        
        if style == 'casual':
            greeting.morning_greeting = getattr(greeting, 'morning_casual', 'Morning!')
            greeting.afternoon_greeting = getattr(greeting, 'afternoon_casual', 'Hi')
            greeting.evening_greeting = getattr(greeting, 'evening_casual', 'Evening!')
        else:  # formal or mixed -> use formal
            greeting.morning_greeting = getattr(greeting, 'morning_formal', 'Good morning')
            greeting.afternoon_greeting = getattr(greeting, 'afternoon_formal', 'Good afternoon')
            greeting.evening_greeting = getattr(greeting, 'evening_formal', 'Good evening')
        
        greeting.save()


def reverse_migrate_greetings_data(apps, schema_editor):
    """Reverse migration - copy back to formal fields"""
    TimeBasedGreeting = apps.get_model('webhooks', 'TimeBasedGreeting')
    
    for greeting in TimeBasedGreeting.objects.all():
        greeting.morning_formal = greeting.morning_greeting
        greeting.afternoon_formal = greeting.afternoon_greeting 
        greeting.evening_formal = greeting.evening_greeting
        greeting.default_style = 'formal'
        greeting.save()


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0071_timebasedgreeting'),
    ]

    operations = [
        # Add new simplified greeting fields
        migrations.AddField(
            model_name='timebasedgreeting',
            name='morning_greeting',
            field=models.CharField(default='Good morning', help_text='Morning greeting', max_length=100),
        ),
        migrations.AddField(
            model_name='timebasedgreeting',
            name='afternoon_greeting',
            field=models.CharField(default='Good afternoon', help_text='Afternoon greeting', max_length=100),
        ),
        migrations.AddField(
            model_name='timebasedgreeting',
            name='evening_greeting',
            field=models.CharField(default='Good evening', help_text='Evening greeting', max_length=100),
        ),
        
        # Migrate data from old fields to new fields
        migrations.RunPython(migrate_greetings_data, reverse_migrate_greetings_data),
        
        # Remove old formal/casual fields and default_style
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='morning_formal',
        ),
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='morning_casual',
        ),
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='afternoon_formal',
        ),
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='afternoon_casual',
        ),
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='evening_formal',
        ),
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='evening_casual',
        ),
        migrations.RemoveField(
            model_name='timebasedgreeting',
            name='default_style',
        ),
    ]