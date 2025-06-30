from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0036_leaddetail_phone_in_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaddetail',
            name='phone_in_dialog',
            field=models.BooleanField(
                default=False,
                help_text='Consumer provided phone number in reply to auto message'
            ),
        ),
    ]
