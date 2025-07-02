from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0038_phone_available_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leaddetail',
            name='temporary_email_address',
            field=models.EmailField(max_length=200, blank=True, null=True),
        ),
    ]
