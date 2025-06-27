from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0032_followuptemplate_phone_opt_in'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeadPendingTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lead_id', models.CharField(max_length=64, db_index=True)),
                ('task_id', models.CharField(max_length=128, unique=True)),
                ('phone_opt_in', models.BooleanField()),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
