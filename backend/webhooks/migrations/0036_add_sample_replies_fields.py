# Generated migration for Sample Replies fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0035_update_autoresponsesettings_sequence'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoresponsesettings',
            name='use_sample_replies',
            field=models.BooleanField(default=False, help_text='🤖 Режим 2: Використовувати Sample Replies для AI генерації (тільки для AI Generated режиму)'),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='sample_replies_content',
            field=models.TextField(blank=True, help_text='Зміст Sample Replies (текст з PDF або ручний ввід)', null=True),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='sample_replies_filename',
            field=models.CharField(blank=True, help_text='Назва завантаженого файлу Sample Replies', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='sample_replies_priority',
            field=models.BooleanField(default=True, help_text='Режим 2: Пріоритет Sample Replies над звичайним AI промптом'),
        ),
    ]
