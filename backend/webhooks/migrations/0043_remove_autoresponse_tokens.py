from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0042_autoresponsesettings_off_hours_template'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='autoresponsesettings',
            name='access_token',
        ),
        migrations.RemoveField(
            model_name='autoresponsesettings',
            name='refresh_token',
        ),
        migrations.RemoveField(
            model_name='autoresponsesettings',
            name='token_expires_at',
        ),
    ]
