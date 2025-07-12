from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0045_leaddetail_phone_number'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='scheduledmessage',
            constraint=models.UniqueConstraint(fields=['lead_id', 'template'], name='uniq_lead_template'),
        ),
    ]
