from django.db import migrations, models
from django.db.models import Q

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0050_drop_scheduled_models'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='leadevent',
            constraint=models.UniqueConstraint(
                fields=['lead_id', 'text'],
                name='uniq_follow_up_lead_text',
                condition=Q(event_type='FOLLOW_UP'),
            ),
        ),
    ]
