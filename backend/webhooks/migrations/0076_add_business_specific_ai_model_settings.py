# Generated manually for business-specific AI model settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0075_create_default_simple_greetings'),
    ]

    operations = [
        # Add business-specific AI model settings to AutoResponseSettings
        migrations.AddField(
            model_name='autoresponsesettings',
            name='ai_model',
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                help_text='OpenAI модель для цього бізнесу (якщо порожня - використовується глобальна)'
            ),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='ai_temperature',
            field=models.FloatField(
                null=True,
                blank=True,
                help_text='Temperature для AI генерації цього бізнесу (якщо порожня - використовується глобальна)'
            ),
        ),
        # Rename existing AISettings fields to indicate they are fallbacks
        migrations.AlterField(
            model_name='aisettings',
            name='openai_model',
            field=models.CharField(
                max_length=50,
                default='gpt-4o',
                help_text='Fallback модель OpenAI (коли не вказана для бізнесу)'
            ),
        ),
        migrations.AlterField(
            model_name='aisettings',
            name='default_temperature',
            field=models.FloatField(
                default=0.7,
                help_text='Fallback temperature для AI генерації (коли не вказана для бізнесу)'
            ),
        ),
        migrations.AlterField(
            model_name='aisettings',
            name='max_message_length',
            field=models.PositiveIntegerField(
                default=160,
                help_text='Fallback максимальна довжина повідомлення (коли не вказана для бізнесу)'
            ),
        ),
        migrations.AlterField(
            model_name='aisettings',
            name='base_system_prompt',
            field=models.TextField(
                default='You are a professional business communication assistant. Generate personalized, friendly, and professional greeting messages for potential customers who have inquired about services.',
                help_text='Fallback системний промпт для AI (коли не вказаний кастомний промпт для бізнесу)'
            ),
        ),
    ]