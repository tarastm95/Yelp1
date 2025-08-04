# Generated manually for simplifying time-based greetings

from django.db import migrations, models


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