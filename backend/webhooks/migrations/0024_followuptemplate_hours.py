from django.db import migrations, models
import datetime

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0023_yelpbusiness_hours'),
    ]

    operations = [
        migrations.AddField(
            model_name='followuptemplate',
            name='open_from',
            field=models.TimeField(default=datetime.time(8, 0)),
        ),
        migrations.AddField(
            model_name='followuptemplate',
            name='open_to',
            field=models.TimeField(default=datetime.time(20, 0)),
        ),
    ]
