from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0035_update_autoresponsesettings_sequence'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaddetail',
            name='phone_in_text',
            field=models.BooleanField(default=False,
                                      help_text='Consumer provided phone number inside a text message'),
        ),
    ]
