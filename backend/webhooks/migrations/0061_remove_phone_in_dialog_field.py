# Generated migration for removing phone_in_dialog field
# As it was merged with phone_in_text for simplification

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0060_ai_settings_and_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='leaddetail',
            name='phone_in_dialog',
        ),
    ]