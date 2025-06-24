from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0022_yelpbusiness_time_zone'),
    ]

    operations = [
        migrations.AddField(
            model_name='yelpbusiness',
            name='open_days',
            field=models.CharField(max_length=128, blank=True),
        ),
        migrations.AddField(
            model_name='yelpbusiness',
            name='open_hours',
            field=models.TextField(blank=True),
        ),
    ]
