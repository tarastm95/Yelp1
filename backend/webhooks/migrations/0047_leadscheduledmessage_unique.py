from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0046_scheduledmessage_unique'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='leadscheduledmessage',
            constraint=models.UniqueConstraint(
                fields=['lead_id', 'content'],
                name='uniq_lead_content',
            ),
        ),
    ]
