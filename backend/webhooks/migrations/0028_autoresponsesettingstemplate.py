from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0027_autoresponsesettings_greeting_delay'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoResponseSettingsTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('data', models.JSONField(help_text='Serialized AutoResponseSettings data')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
