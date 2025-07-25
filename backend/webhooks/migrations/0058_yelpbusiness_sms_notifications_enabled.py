# Generated manually for sms_notifications_enabled field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0057_notification_business'),
    ]

    operations = [
        migrations.AddField(
            model_name='yelpbusiness',
            name='sms_notifications_enabled',
            field=models.BooleanField(default=False, help_text='Enable/disable SMS notifications for new leads for this business'),
        ),
    ] 