from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0031_autoresponsesettings_phone_opt_in'),
    ]

    operations = [
        migrations.AddField(
            model_name='followuptemplate',
            name='phone_opt_in',
            field=models.BooleanField(default=False,
                help_text='Use this template when consumer phone number is available'),
        ),
    ]
