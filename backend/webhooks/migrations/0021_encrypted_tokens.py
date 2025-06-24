from django.db import migrations
import webhooks.fields

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0020_followuptemplate_business'),
    ]

    operations = [
        migrations.AlterField(
            model_name='yelptoken',
            name='access_token',
            field=webhooks.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='yelptoken',
            name='refresh_token',
            field=webhooks.fields.EncryptedTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='autoresponsesettings',
            name='access_token',
            field=webhooks.fields.EncryptedTextField(help_text='Yelp API access token'),
        ),
        migrations.AlterField(
            model_name='autoresponsesettings',
            name='refresh_token',
            field=webhooks.fields.EncryptedTextField(blank=True, help_text='Yelp API refresh token (дійсний 365 днів)'),
        ),
    ]
