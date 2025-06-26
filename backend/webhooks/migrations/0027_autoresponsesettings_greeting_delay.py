from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0026_autoresponsesettings_hours'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='greeting_delay',
            field=models.PositiveIntegerField(default=0, help_text='Затримка перед привітанням, в секундах'),
        ),
    ]
