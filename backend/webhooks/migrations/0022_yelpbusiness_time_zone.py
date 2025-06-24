from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0021_encrypted_tokens'),
    ]

    operations = [
        migrations.AddField(
            model_name='yelpbusiness',
            name='time_zone',
            field=models.CharField(max_length=64, blank=True),
        ),
    ]
