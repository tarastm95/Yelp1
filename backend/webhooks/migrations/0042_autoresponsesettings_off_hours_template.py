from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0041_follow_up_template_blank'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='greeting_off_hours_template',
            field=models.TextField(blank=True, default='', help_text='Шаблон привітання для неробочих годин'),
        ),
    ]
