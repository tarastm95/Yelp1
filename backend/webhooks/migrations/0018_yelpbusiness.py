from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0017_leadscheduledmessage_leadscheduledmessagehistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='YelpBusiness',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_id', models.CharField(max_length=128, unique=True, db_index=True)),
                ('name', models.CharField(max_length=255)),
                ('location', models.CharField(max_length=255, blank=True)),
                ('details', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
