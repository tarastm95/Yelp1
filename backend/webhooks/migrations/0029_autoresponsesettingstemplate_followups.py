from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0028_autoresponsesettingstemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettingstemplate',
            name='follow_up_templates',
            field=models.JSONField(default=list, blank=True, help_text='Serialized list of additional FollowUpTemplate objects'),
        ),
    ]
