from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0040_leadevent_cursor_textfield"),
    ]

    operations = [
        migrations.AlterField(
            model_name="autoresponsesettings",
            name="follow_up_template",
            field=models.TextField(
                default="Just checking back in{sep}{name} — any questions about “{jobs}”?",
                help_text="Шаблон follow-up повідомлення з плейсхолдерами {name}, {jobs}, {sep}",
                blank=True,
            ),
        ),
    ]
