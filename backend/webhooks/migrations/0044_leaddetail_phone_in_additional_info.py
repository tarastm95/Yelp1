from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0043_remove_autoresponse_tokens'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaddetail',
            name='phone_in_additional_info',
            field=models.BooleanField(default=False, help_text='Consumer provided phone number inside additional_info'),
        ),
    ]
