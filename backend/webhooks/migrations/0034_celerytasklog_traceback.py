from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0033_leadpendingtask'),
    ]

    operations = [
        migrations.AddField(
            model_name='celerytasklog',
            name='traceback',
            field=models.TextField(blank=True, null=True),
        ),
    ]
