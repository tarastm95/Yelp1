from django.db import migrations, models
from django.db.models import F


def set_initial_text(apps, schema_editor):
    LeadPendingTask = apps.get_model("webhooks", "LeadPendingTask")
    LeadPendingTask.objects.all().update(text=F("task_id"))

class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0047_leadscheduledmessage_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="leadpendingtask",
            name="text",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.RunPython(set_initial_text, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="leadpendingtask",
            constraint=models.UniqueConstraint(
                fields=["lead_id", "text"], name="uniq_lead_text"
            ),
        ),
    ]
