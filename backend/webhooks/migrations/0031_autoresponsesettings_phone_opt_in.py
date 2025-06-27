from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0030_leaddetail_phone_opt_in'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='phone_opt_in',
            field=models.BooleanField(default=False,
                help_text='Use these settings when consumer phone number is available'),
        ),
    ]
