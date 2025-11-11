# Generated migration for AI generation fields (Variant B)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0081_add_message_queue_fields'),
    ]

    operations = [
        # Make text field optional (can be empty until AI generation)
        migrations.AlterField(
            model_name='leadpendingtask',
            name='text',
            field=models.TextField(blank=True, default=''),
        ),
        
        # Add AI generation fields
        migrations.AddField(
            model_name='leadpendingtask',
            name='template_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='ID FollowUpTemplate для AI генерації (якщо потрібно)'
            ),
        ),
        migrations.AddField(
            model_name='leadpendingtask',
            name='ai_mode',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('NONE', 'No AI'),
                    ('TEMPLATE', 'Template'),
                    ('AI_FULL', 'AI Full'),
                    ('AI_VECTOR', 'AI Vector'),
                ],
                default='NONE',
                help_text='Режим генерації тексту'
            ),
        ),
        migrations.AddField(
            model_name='leadpendingtask',
            name='generated_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Коли текст було згенеровано AI'
            ),
        ),
        
        # Remove old text-based uniqueness constraint
        migrations.RemoveConstraint(
            model_name='leadpendingtask',
            name='uniq_lead_text_active',
        ),
    ]

