from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0024_followuptemplate_hours'),
    ]

    operations = [
        migrations.CreateModel(
            name='CeleryTaskLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(max_length=128, unique=True, db_index=True)),
                ('name', models.CharField(max_length=200)),
                ('args', models.JSONField(blank=True, null=True)),
                ('kwargs', models.JSONField(blank=True, null=True)),
                ('eta', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(max_length=20)),
                ('result', models.TextField(blank=True, null=True)),
                ('business_id', models.CharField(max_length=128, blank=True, null=True)),
            ],
        ),
    ]
