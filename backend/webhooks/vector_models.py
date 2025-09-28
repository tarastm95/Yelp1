"""
🔍 Vector Models for Sample Replies with pgvector
Зберігання документів та чанків з ембедінгами OpenAI для семантичного пошуку
"""

from django.db import models
from pgvector.django import VectorField
from .models import YelpBusiness
import json

class VectorDocument(models.Model):
    """PDF документ з Sample Replies для векторного пошуку"""
    
    # Business association
    business_id = models.CharField(
        max_length=128, 
        db_index=True,
        help_text="Yelp business ID для якого цей документ"
    )
    location_id = models.CharField(
        max_length=128, 
        blank=True, 
        null=True,
        db_index=True,
        help_text="Опціональний location ID для мульти-локаційних бізнесів"
    )
    
    # Document metadata
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(
        max_length=64, 
        unique=True, 
        help_text="SHA-256 хеш вмісту файлу для дедуплікації"
    )
    file_size = models.PositiveIntegerField(help_text="Розмір файлу в байтах")
    
    # Processing statistics
    page_count = models.PositiveIntegerField(default=0)
    chunk_count = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    
    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('error', 'Error'),
        ],
        default='processing'
    )
    error_message = models.TextField(blank=True, null=True)
    
    # Embedding model info
    embedding_model = models.CharField(
        max_length=50,
        default='text-embedding-3-small',
        help_text="OpenAI модель використана для ембедінгів"
    )
    embedding_dimensions = models.PositiveIntegerField(
        default=1536,
        help_text="Розмірність векторів ембедінгів"
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Додаткові метадані про обробку та статистику"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhooks_vectordocument'
        indexes = [
            models.Index(fields=['business_id', '-created_at']),
            models.Index(fields=['business_id', 'location_id']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['file_hash']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['business_id', 'location_id', 'file_hash'],
                name='unique_vector_business_location_file'
            )
        ]
    
    def __str__(self):
        location_part = f" (Location: {self.location_id})" if self.location_id else ""
        return f"Vector Doc: {self.filename} - {self.business_id}{location_part}"
    
    @property
    def is_ready_for_search(self) -> bool:
        """Перевірка чи документ готовий для векторного пошуку"""
        return (
            self.processing_status == 'completed' and 
            self.chunk_count > 0
        )


class VectorChunk(models.Model):
    """Семантичний чанк тексту з векторним ембедінгом для пошуку"""
    
    # Document reference
    document = models.ForeignKey(
        VectorDocument,
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Документ до якого належить цей чанк"
    )
    
    # Content information  
    content = models.TextField(help_text="Текстовий вміст чанку")
    page_number = models.PositiveIntegerField(help_text="Номер сторінки джерела")
    chunk_index = models.PositiveIntegerField(help_text="Порядок в документі")
    token_count = models.PositiveIntegerField(help_text="Кількість токенів у чанку")
    
    # Vector embedding (1536 dimensions for text-embedding-3-small)
    embedding = VectorField(
        dimensions=1536,
        help_text="OpenAI text-embedding-3-small вектор (1536 розмірів)"
    )
    
    # Semantic metadata
    chunk_type = models.CharField(
        max_length=20,
        choices=[
            ('inquiry', 'Customer Inquiry'),
            ('response', 'Business Response'),
            ('example', 'Complete Example'),
            ('general', 'General Content'),
        ],
        default='general',
        help_text="Тип семантичного контенту"
    )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Метадані чанку: has_customer_name, has_service_type, etc."
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'webhooks_vectorchunk'
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['chunk_type']),
            models.Index(fields=['page_number']),
            # Vector similarity index буде створений в міграції
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'chunk_index'],
                name='unique_vector_document_chunk_index'
            )
        ]
    
    def __str__(self):
        return f"Vector Chunk {self.chunk_index} from {self.document.filename} (page {self.page_number})"
    
    def get_preview(self, max_length: int = 100) -> str:
        """Отримати превʼю вмісту чанку"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    @property
    def similarity_search_ready(self) -> bool:
        """Перевірка чи чанк готовий для векторного пошуку"""
        return bool(self.embedding)
    
    def calculate_similarity(self, query_embedding: list) -> float:
        """Розрахунок косинусної схожості з query embedding"""
        if not self.embedding:
            return 0.0
        
        # Це буде виконано через raw SQL в реальному пошуку
        # Тут просто placeholder
        return 0.0
