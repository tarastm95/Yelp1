# Generated manually for TimeBasedGreeting model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0061_remove_phone_in_dialog_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeBasedGreeting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('morning_start', models.TimeField(default='05:00', help_text='Morning greeting start time')),
                ('morning_end', models.TimeField(default='12:00', help_text='Morning greeting end time')),
                ('afternoon_start', models.TimeField(default='12:00', help_text='Afternoon greeting start time')),
                ('afternoon_end', models.TimeField(default='17:00', help_text='Afternoon greeting end time')),
                ('evening_start', models.TimeField(default='17:00', help_text='Evening greeting start time')),
                ('evening_end', models.TimeField(default='21:00', help_text='Evening greeting end time')),
                ('morning_formal', models.CharField(default='Good morning', help_text='Formal morning greeting', max_length=100)),
                ('morning_casual', models.CharField(default='Morning!', help_text='Casual morning greeting', max_length=100)),
                ('afternoon_formal', models.CharField(default='Good afternoon', help_text='Formal afternoon greeting', max_length=100)),
                ('afternoon_casual', models.CharField(default='Hi', help_text='Casual afternoon greeting', max_length=100)),
                ('evening_formal', models.CharField(default='Good evening', help_text='Formal evening greeting', max_length=100)),
                ('evening_casual', models.CharField(default='Evening!', help_text='Casual evening greeting', max_length=100)),
                ('night_greeting', models.CharField(default='Hello', help_text='Late night greeting (after evening_end)', max_length=100)),
                ('default_style', models.CharField(choices=[('formal', 'Formal (Good morning, Good afternoon)'), ('casual', 'Casual (Morning!, Hi, Evening!)'), ('mixed', 'Mixed (varies by time)')], default='formal', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business', models.ForeignKey(blank=True, help_text='Business-specific greetings. Null = global default', null=True, on_delete=django.db.models.deletion.CASCADE, to='webhooks.yelpbusiness')),
            ],
            options={
                'verbose_name': 'Time-based Greeting',
                'verbose_name_plural': 'Time-based Greetings',
            },
        ),
        migrations.AddConstraint(
            model_name='timebasedgreeting',
            constraint=models.UniqueConstraint(condition=models.Q(business__isnull=False), fields=('business',), name='uniq_greeting_per_business'),
        ),
    ]