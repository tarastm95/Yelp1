from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0048_leadpendingtask_text"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="leadpendingtask",
            name="uniq_lead_text",
        ),
        migrations.AddConstraint(
            model_name="leadpendingtask",
            constraint=models.UniqueConstraint(
                fields=["lead_id", "text"],
                name="uniq_lead_text",
                condition=~Q(text=""),
            ),
        ),
    ]
