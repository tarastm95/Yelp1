from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0056_notification_unique_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationsetting",
            name="business",
            field=models.ForeignKey(null=True, blank=True, on_delete=models.CASCADE, to="webhooks.yelpbusiness"),
        ),
        migrations.AlterField(
            model_name="notificationsetting",
            name="phone_number",
            field=models.CharField(max_length=64),
        ),
        migrations.AddConstraint(
            model_name="notificationsetting",
            constraint=models.UniqueConstraint(fields=["business", "phone_number"], name="uniq_notification_business_phone"),
        ),
    ]
