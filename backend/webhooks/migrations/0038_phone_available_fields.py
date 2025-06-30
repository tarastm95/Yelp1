from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0037_leaddetail_phone_in_dialog'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='phone_available',
            field=models.BooleanField(default=False, help_text='Use these settings when phone number was provided in text'),
        ),
        migrations.AddField(
            model_name='followuptemplate',
            name='phone_available',
            field=models.BooleanField(default=False, help_text='Use this template when phone number was provided in text'),
        ),
        migrations.AddField(
            model_name='leadpendingtask',
            name='phone_available',
            field=models.BooleanField(default=False),
        ),
    ]
