from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0044_leaddetail_phone_in_additional_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaddetail',
            name='phone_number',
            field=models.CharField(max_length=32, blank=True),
        ),
    ]
