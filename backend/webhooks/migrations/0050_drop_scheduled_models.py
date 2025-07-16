from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0049_leadpendingtask_unique_condition'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ScheduledMessageHistory',
        ),
        migrations.DeleteModel(
            name='ScheduledMessage',
        ),
        migrations.DeleteModel(
            name='LeadScheduledMessageHistory',
        ),
        migrations.DeleteModel(
            name='LeadScheduledMessage',
        ),
    ]
