from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0052_leadevent_from_backend"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="autoresponsesettings",
            name="follow_up_template",
        ),
        migrations.RemoveField(
            model_name="autoresponsesettings",
            name="follow_up_delay",
        ),
        migrations.RemoveField(
            model_name="autoresponsesettings",
            name="follow_up_open_from",
        ),
        migrations.RemoveField(
            model_name="autoresponsesettings",
            name="follow_up_open_to",
        ),
    ]
