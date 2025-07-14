from django.db import migrations, models

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
        migrations.AddConstraint(
            model_name="leadpendingtask",
            constraint=models.UniqueConstraint(
                fields=["lead_id", "text"], name="uniq_lead_text"
            ),
        ),
    ]
