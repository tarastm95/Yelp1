# Generated migration for AI settings

from django.db import migrations, models
import django.db.models.deletion
from datetime import time
import webhooks.fields


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0059_smslog'),
    ]

    operations = [
        # Add AI fields to AutoResponseSettings
        migrations.AddField(
            model_name='autoresponsesettings',
            name='use_ai_greeting',
            field=models.BooleanField(
                default=False, 
                help_text='Використовувати AI для генерації вітальних повідомлень'
            ),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='ai_response_style',
            field=models.CharField(
                choices=[('formal', 'Formal'), ('casual', 'Casual'), ('auto', 'Auto')],
                default='auto',
                help_text='Стиль AI відповіді',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='ai_include_location',
            field=models.BooleanField(
                default=False, 
                help_text='Включати локацію бізнесу в AI повідомлення'
            ),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='ai_mention_response_time',
            field=models.BooleanField(
                default=False, 
                help_text='Згадувати очікуваний час відповіді в AI повідомленнях'
            ),
        ),
        migrations.AddField(
            model_name='autoresponsesettings',
            name='ai_custom_prompt',
            field=models.TextField(
                blank=True, 
                null=True,
                help_text='Кастомний промпт для AI (якщо порожній - використовується глобальний)'
            ),
        ),
        # Create AISettings model
        migrations.CreateModel(
            name='AISettings',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, 
                    primary_key=True, 
                    serialize=False, 
                    verbose_name='ID'
                )),
                ('openai_api_key', webhooks.fields.EncryptedTextField(
                    help_text='OpenAI API ключ (зберігається зашифровано)'
                )),
                ('openai_model', models.CharField(
                    default='gpt-4o', 
                    help_text='Модель OpenAI для використання', 
                    max_length=50
                )),
                ('base_system_prompt', models.TextField(
                    default='You are a professional business communication assistant. Generate personalized, friendly, and professional greeting messages for potential customers who have inquired about services.',
                    help_text='Базовий системний промпт для AI'
                )),
                ('max_message_length', models.PositiveIntegerField(
                    default=160,
                    help_text='Максимальна довжина згенерованого повідомлення'
                )),
                ('default_temperature', models.FloatField(
                    default=0.7,
                    help_text='Temperature для AI генерації (0.0-1.0)'
                )),
                ('always_include_business_name', models.BooleanField(
                    default=True,
                    help_text='Завжди включати назву бізнесу в повідомлення'
                )),
                ('always_use_customer_name', models.BooleanField(
                    default=True,
                    help_text='Завжди використовувати імя клієнта, якщо доступне'
                )),
                ('fallback_to_template', models.BooleanField(
                    default=True,
                    help_text='Використовувати шаблон як fallback при помилці AI'
                )),
                ('requests_per_minute', models.PositiveIntegerField(
                    default=60,
                    help_text='Максимальна кількість запитів до AI на хвилину'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'AI Settings',
                'verbose_name_plural': 'AI Settings',
            },
        ),
    ] 