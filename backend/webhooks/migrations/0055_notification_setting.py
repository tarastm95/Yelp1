from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0054_autoresponsesettings_open_days"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(max_length=64)),
                ("message_template", models.TextField()),
            ],
        ),
    ]
