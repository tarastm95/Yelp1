from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0029_autoresponsesettingstemplate_followups'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaddetail',
            name='phone_opt_in',
            field=models.BooleanField(default=False),
        ),
    ]
