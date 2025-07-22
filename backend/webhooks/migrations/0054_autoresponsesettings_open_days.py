from django.db import migrations, models
import datetime

class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0053_remove_autoresponsesettings_follow_up"),
    ]

    operations = [
        migrations.AddField(
            model_name="autoresponsesettings",
            name="greeting_open_days",
            field=models.CharField(max_length=64, blank=True),
        ),
    ]
