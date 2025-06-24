from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0019_autoresponsesettings_business'),
    ]

    operations = [
        migrations.AddField(
            model_name='followuptemplate',
            name='business',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.CASCADE, to='webhooks.yelpbusiness', help_text='Який бізнес використовує цей шаблон. Null → шаблон за замовчуванням'),
        ),
    ]
