from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0055_notification_setting"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notificationsetting",
            name="phone_number",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
