# Generated manually for SMSLog model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0058_yelpbusiness_sms_notifications_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMSLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sid', models.CharField(db_index=True, help_text='Twilio Message SID', max_length=128, unique=True)),
                ('to_phone', models.CharField(db_index=True, help_text='Destination phone number', max_length=32)),
                ('from_phone', models.CharField(help_text='Source phone number (Twilio)', max_length=32)),
                ('body', models.TextField(help_text='SMS message content')),
                ('lead_id', models.CharField(blank=True, db_index=True, help_text='Related lead ID', max_length=64, null=True)),
                ('business_id', models.CharField(blank=True, db_index=True, help_text='Related business ID', max_length=128, null=True)),
                ('purpose', models.CharField(blank=True, help_text='Purpose: notification, auto_response, manual, api', max_length=50)),
                ('status', models.CharField(default='sent', help_text='Status: sent, delivered, failed, etc.', max_length=20)),
                ('error_message', models.TextField(blank=True, help_text='Error details if failed', null=True)),
                ('price', models.CharField(blank=True, help_text='SMS cost', max_length=20, null=True)),
                ('price_unit', models.CharField(blank=True, help_text='Currency', max_length=10, null=True)),
                ('direction', models.CharField(blank=True, help_text='outbound-api', max_length=20, null=True)),
                ('sent_at', models.DateTimeField(auto_now_add=True, help_text='When SMS was sent from our system')),
                ('twilio_created_at', models.DateTimeField(blank=True, help_text='Twilio timestamp', null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['business_id', '-sent_at'], name='webhooks_smslog_bus_sent_idx'),
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['lead_id', '-sent_at'], name='webhooks_smslog_lead_sent_idx'),
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['purpose', '-sent_at'], name='webhooks_smslog_purpose_sent_idx'),
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['status', '-sent_at'], name='webhooks_smslog_status_sent_idx'),
        ),
    ] 