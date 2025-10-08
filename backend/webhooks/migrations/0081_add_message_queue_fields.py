# Generated migration for message queue fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0080_change_vector_similarity_threshold_default'),
    ]

    operations = [
        # Додаємо нові поля
        migrations.AddField(
            model_name='leadpendingtask',
            name='sequence_number',
            field=models.PositiveIntegerField(
                default=0,
                db_index=True,
                help_text='Порядковий номер в черзі (0=greeting, 1=first follow-up, 2=second follow-up, ...)'
            ),
        ),
        migrations.AddField(
            model_name='leadpendingtask',
            name='previous_task_id',
            field=models.CharField(
                max_length=128,
                null=True,
                blank=True,
                help_text='ID попереднього task в черзі (для перевірки послідовності)'
            ),
        ),
        migrations.AddField(
            model_name='leadpendingtask',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('PENDING', 'Pending'),
                    ('WAITING', 'Waiting'),
                    ('SENDING', 'Sending'),
                    ('SENT', 'Sent'),
                    ('FAILED', 'Failed'),
                    ('CANCELLED', 'Cancelled')
                ],
                default='PENDING',
                db_index=True,
                help_text='Статус відправки повідомлення'
            ),
        ),
        migrations.AddField(
            model_name='leadpendingtask',
            name='sent_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='Коли повідомлення було відправлено'
            ),
        ),
        # Додаємо constraint для унікальності sequence_number
        migrations.AddConstraint(
            model_name='leadpendingtask',
            constraint=models.UniqueConstraint(
                condition=models.Q(active=True),
                fields=['lead_id', 'sequence_number'],
                name='uniq_lead_sequence'
            ),
        ),
    ]

