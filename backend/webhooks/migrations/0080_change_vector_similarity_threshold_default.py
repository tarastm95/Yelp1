# Generated manually to fix vector similarity threshold default

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0079_delete_vectorchunk_delete_vectordocument'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autoresponsesettings',
            name='vector_similarity_threshold',
            field=models.FloatField(
                default=0.4,
                help_text='Поріг семантичної схожості для vector search (0.0-1.0). Нижчі значення дають більше результатів'
            ),
        ),
    ]
