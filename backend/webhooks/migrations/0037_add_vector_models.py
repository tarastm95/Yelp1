# Generated migration for Vector models with pgvector support

from django.db import migrations, models
import django.db.models.deletion
import pgvector.django


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0036_add_sample_replies_fields'),
    ]

    operations = [
        # Ensure pgvector extension is enabled
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="-- Extension will persist"
        ),
        
        # Create VectorDocument table
        migrations.CreateModel(
            name='VectorDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_id', models.CharField(db_index=True, help_text='Yelp business ID для якого цей документ', max_length=128)),
                ('location_id', models.CharField(blank=True, db_index=True, help_text='Опціональний location ID для мульти-локаційних бізнесів', max_length=128, null=True)),
                ('filename', models.CharField(max_length=255)),
                ('file_hash', models.CharField(help_text='SHA-256 хеш вмісту файлу для дедуплікації', max_length=64, unique=True)),
                ('file_size', models.PositiveIntegerField(help_text='Розмір файлу в байтах')),
                ('page_count', models.PositiveIntegerField(default=0)),
                ('chunk_count', models.PositiveIntegerField(default=0)),
                ('total_tokens', models.PositiveIntegerField(default=0)),
                ('processing_status', models.CharField(choices=[('processing', 'Processing'), ('completed', 'Completed'), ('error', 'Error')], default='processing', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('embedding_model', models.CharField(default='text-embedding-3-small', help_text='OpenAI модель використана для ембедінгів', max_length=50)),
                ('embedding_dimensions', models.PositiveIntegerField(default=1536, help_text='Розмірність векторів ембедінгів')),
                ('metadata', models.JSONField(default=dict, help_text='Додаткові метадані про обробку та статистику')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'webhooks_vectordocument',
            },
        ),
        
        # Create VectorChunk table
        migrations.CreateModel(
            name='VectorChunk',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(help_text='Текстовий вміст чанку')),
                ('page_number', models.PositiveIntegerField(help_text='Номер сторінки джерела')),
                ('chunk_index', models.PositiveIntegerField(help_text='Порядок в документі')),
                ('token_count', models.PositiveIntegerField(help_text='Кількість токенів у чанку')),
                ('embedding', pgvector.django.VectorField(dimensions=1536, help_text='OpenAI text-embedding-3-small вектор (1536 розмірів)')),
                ('chunk_type', models.CharField(choices=[('inquiry', 'Customer Inquiry'), ('response', 'Business Response'), ('example', 'Complete Example'), ('general', 'General Content')], default='general', help_text='Тип семантичного контенту', max_length=20)),
                ('metadata', models.JSONField(default=dict, help_text='Метадані чанку: has_customer_name, has_service_type, etc.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(help_text='Документ до якого належить цей чанк', on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='webhooks.vectordocument')),
            ],
            options={
                'db_table': 'webhooks_vectorchunk',
            },
        ),
        
        # Add indexes for VectorDocument
        migrations.AddIndex(
            model_name='vectordocument',
            index=models.Index(fields=['business_id', '-created_at'], name='webhooks_ve_busines_1a2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='vectordocument',
            index=models.Index(fields=['business_id', 'location_id'], name='webhooks_ve_busines_4d5e6f_idx'),
        ),
        migrations.AddIndex(
            model_name='vectordocument',
            index=models.Index(fields=['processing_status'], name='webhooks_ve_process_7g8h9i_idx'),
        ),
        migrations.AddIndex(
            model_name='vectordocument',
            index=models.Index(fields=['file_hash'], name='webhooks_ve_file_ha_0j1k2l_idx'),
        ),
        
        # Add indexes for VectorChunk
        migrations.AddIndex(
            model_name='vectorchunk',
            index=models.Index(fields=['document', 'chunk_index'], name='webhooks_ve_documen_3m4n5o_idx'),
        ),
        migrations.AddIndex(
            model_name='vectorchunk',
            index=models.Index(fields=['chunk_type'], name='webhooks_ve_chunk_t_6p7q8r_idx'),
        ),
        migrations.AddIndex(
            model_name='vectorchunk',
            index=models.Index(fields=['page_number'], name='webhooks_ve_page_nu_9s0t1u_idx'),
        ),
        
        # Add constraints
        migrations.AddConstraint(
            model_name='vectordocument',
            constraint=models.UniqueConstraint(fields=('business_id', 'location_id', 'file_hash'), name='unique_vector_business_location_file'),
        ),
        migrations.AddConstraint(
            model_name='vectorchunk',
            constraint=models.UniqueConstraint(fields=('document', 'chunk_index'), name='unique_vector_document_chunk_index'),
        ),
        
        # Create vector similarity indexes for faster searches
        # IVFFlat index for cosine distance (recommended for embeddings)
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS webhooks_vectorchunk_embedding_cosine_idx 
            ON webhooks_vectorchunk 
            USING ivfflat (embedding vector_cosine_ops) 
            WITH (lists = 100);
            """,
            reverse_sql="DROP INDEX IF EXISTS webhooks_vectorchunk_embedding_cosine_idx;"
        ),
        
        # L2 distance index (optional, for different similarity metrics)
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS webhooks_vectorchunk_embedding_l2_idx 
            ON webhooks_vectorchunk 
            USING ivfflat (embedding vector_l2_ops) 
            WITH (lists = 100);
            """,
            reverse_sql="DROP INDEX IF EXISTS webhooks_vectorchunk_embedding_l2_idx;"
        ),
    ]
