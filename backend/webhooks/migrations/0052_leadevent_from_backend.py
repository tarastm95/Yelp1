from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0051_leadevent_follow_up_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='leadevent',
            name='from_backend',
            field=models.BooleanField(default=False),
        ),
    ]
