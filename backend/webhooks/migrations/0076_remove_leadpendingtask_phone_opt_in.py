# Generated migration for removing phone_opt_in from LeadPendingTask

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0075_merge_20250904_0858'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='leadpendingtask',
            name='phone_opt_in',
        ),
    ]
