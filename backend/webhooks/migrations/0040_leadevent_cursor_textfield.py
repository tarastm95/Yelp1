from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0039_leaddetail_temp_email_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leadevent',
            name='cursor',
            field=models.TextField(blank=True),
        ),
    ]
