from django.db import migrations, models
import datetime

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0025_celerytasklog'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='greeting_open_from',
            field=models.TimeField(default=datetime.time(8, 0)),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='greeting_open_to',
            field=models.TimeField(default=datetime.time(20, 0)),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='follow_up_open_from',
            field=models.TimeField(default=datetime.time(8, 0)),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='follow_up_open_to',
            field=models.TimeField(default=datetime.time(20, 0)),
        ),
    ]
