# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0076_add_business_specific_ai_model_settings'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_name', models.CharField(help_text='Оригінальна назва послуги, яка приходить з Yelp', max_length=200, unique=True)),
                ('custom_name', models.CharField(help_text='Ваша власна назва для цієї послуги', max_length=200)),
                ('active', models.BooleanField(default=True, help_text='Чи активна ця заміна')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Job Name Mapping',
                'verbose_name_plural': 'Job Name Mappings',
                'ordering': ['original_name'],
            },
        ),
    ]