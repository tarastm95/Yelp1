from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('webhooks', '0018_yelpbusiness'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='business',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.CASCADE, to='webhooks.yelpbusiness', help_text='Який бізнес використовує ці налаштування. Null → налаштування за замовчуванням'),
        ),
    ]
