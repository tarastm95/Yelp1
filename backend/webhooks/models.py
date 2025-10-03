from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, time
from .fields import EncryptedTextField

# Import vector models for Sample Replies
try:
    from .vector_models import VectorDocument, VectorChunk
except ImportError:
    # Fallback if pgvector not available yet
    VectorDocument = None
    VectorChunk = None


class Event(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    def __str__(self):
        return f"Event {self.id} @ {self.created_at}"


class ProcessedLead(models.Model):
    business_id = models.CharField(max_length=128, db_index=True)
    lead_id = models.CharField(max_length=128, unique=True, db_index=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ProcessedLead {self.lead_id}"


class YelpOAuthState(models.Model):
    state = models.CharField(max_length=128, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class YelpToken(models.Model):
    business_id = models.CharField(max_length=128, unique=True, db_index=True)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class YelpBusiness(models.Model):
    """Stores basic info about a Yelp business."""

    business_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    time_zone = models.CharField(max_length=64, blank=True)
    open_days = models.CharField(max_length=128, blank=True)
    open_hours = models.TextField(blank=True)
    details = models.JSONField(blank=True, null=True)
    sms_notifications_enabled = models.BooleanField(
        default=False,
        help_text="Enable/disable SMS notifications for new leads for this business"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_id} - {self.name}"


class AutoResponseSettings(models.Model):
    business = models.ForeignKey(
        YelpBusiness,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Який бізнес використовує ці налаштування. Null → налаштування за замовчуванням",
    )
    phone_available = models.BooleanField(
        default=False,
        help_text="Use these settings when phone number was provided in text",
    )
    enabled = models.BooleanField(
        default=False, help_text="Увімкнути/вимкнути автoвідповіді"
    )

    # Вітальне повідомлення
    greeting_template = models.TextField(
        default="Hello{sep}{name}! Thank you for your inquiry regarding “{jobs}”.",
        help_text="Шаблон першого повідомлення з плейсхолдерами {name}, {jobs}, {sep}",
    )
    greeting_off_hours_template = models.TextField(
        default="",
        blank=True,
        help_text="Шаблон привітання для неробочих годин",
    )
    include_name = models.BooleanField(
        default=True, help_text="Включати ім’я клієнта у вітальне повідомлення"
    )
    include_jobs = models.BooleanField(
        default=True, help_text="Включати список робіт у вітальне повідомлення"
    )

    greeting_delay = models.PositiveIntegerField(
        default=0,
        help_text="Затримка перед привітанням, в секундах",
    )

    # AI Settings for greeting messages
    use_ai_greeting = models.BooleanField(
        default=False,
        help_text="Використовувати AI для генерації вітальних повідомлень"
    )
    # ai_response_style removed - AI learns style from PDF examples via inquiry→response pairs
    # ai_include_location and ai_mention_response_time removed - controlled via Custom Instructions
    ai_custom_prompt = models.TextField(
        blank=True,
        null=True,
        help_text="Кастомний промпт для AI (якщо порожній - використовується глобальний)"
    )

    # AI Business Data Settings - що включати в AI повідомлення
    ai_include_rating = models.BooleanField(
        default=True,
        help_text="Включати рейтинг бізнесу в AI повідомлення"
    )
    ai_include_categories = models.BooleanField(
        default=True,
        help_text="Включати категорії/спеціалізацію бізнесу в AI повідомлення"
    )
    ai_include_phone = models.BooleanField(
        default=True,
        help_text="Включати телефон бізнесу в AI повідомлення"
    )
    ai_include_website = models.BooleanField(
        default=False,
        help_text="Включати веб-сайт бізнесу в AI повідомлення"
    )
    ai_include_price_range = models.BooleanField(
        default=True,
        help_text="Включати ціновий діапазон ($-$$$$) в AI повідомлення"
    )
    ai_include_hours = models.BooleanField(
        default=True,
        help_text="Включати інформацію про робочі години в AI повідомлення"
    )
    ai_include_reviews_count = models.BooleanField(
        default=True,
        help_text="Включати кількість відгуків в AI повідомлення"
    )
    ai_include_address = models.BooleanField(
        default=False,
        help_text="Включати повну адресу в AI повідомлення"
    )
    ai_include_transactions = models.BooleanField(
        default=False,
        help_text="Включати доступні послуги/транзакції в AI повідомлення"
    )

    # AI Message Length Settings
    ai_max_message_length = models.PositiveIntegerField(
        default=160,
        help_text="Максимальна довжина AI-згенерованого повідомлення (символів). Якщо 0 - використовується глобальне налаштування"
    )
    
    # 🤖 Business-specific AI Model Settings
    ai_model = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="OpenAI модель для цього бізнесу (якщо порожня - використовується глобальна)"
    )
    ai_temperature = models.FloatField(
        null=True,
        blank=True,
        help_text="Temperature для AI генерації цього бізнесу (якщо порожня - використовується глобальна)"
    )

    # 🔍 Vector Search Settings (для Sample Replies режиму)
    vector_similarity_threshold = models.FloatField(
        default=0.4,
        help_text="Поріг семантичної схожості для vector search (0.0-1.0). Нижчі значення дають більше результатів"
    )
    vector_search_limit = models.PositiveIntegerField(
        default=5,
        help_text="Максимальна кількість результатів vector search"
    )
    vector_chunk_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Типи чанків для пошуку: ['inquiry', 'response', 'example', 'general']. Порожній список = всі типи"
    )

    # 📄 Sample Replies Settings (тільки для режиму 2: AI Generated)
    use_sample_replies = models.BooleanField(
        default=False,
        help_text="🤖 Режим 2: Використовувати Sample Replies для AI генерації (тільки для AI Generated режиму)"
    )
    sample_replies_content = models.TextField(
        blank=True,
        null=True,
        help_text="Зміст Sample Replies (текст з PDF або ручний ввід)"
    )
    sample_replies_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Назва завантаженого файлу Sample Replies"
    )
    sample_replies_priority = models.BooleanField(
        default=True,
        help_text="Режим 2: Пріоритет Sample Replies над звичайним AI промптом"
    )

    export_to_sheets = models.BooleanField(
        default=False, help_text="Записувати нові ліди в Google Sheets"
    )

    # 📱 SMS Notification Settings
    sms_on_phone_found = models.BooleanField(
        default=True, 
        help_text="Відправляти SMS коли система знаходить номер телефону в тексті"
    )
    sms_on_customer_reply = models.BooleanField(
        default=True,
        help_text="Відправляти SMS коли клієнт відповідає на повідомлення"
    )
    sms_on_phone_opt_in = models.BooleanField(
        default=True,
        help_text="Відправляти SMS коли приходить phone opt-in від клієнта"
    )

    greeting_open_from = models.TimeField(
        default=time(8, 0),
        help_text="Час початку робочих годин для привітання (локальний час)",
    )
    greeting_open_to = models.TimeField(
        default=time(20, 0),
        help_text="Час завершення робочих годин для привітання (локальний час)",
    )
    greeting_open_days = models.CharField(
        max_length=64,
        blank=True,
        help_text="Скорочені назви днів тижня через кому, напр. 'Mon, Tue, Wed'",
    )

    def __str__(self):
        return f"AutoResponseSettings(id={self.id}, enabled={self.enabled})"


class AISettings(models.Model):
    """Глобальні налаштування для AI генерації повідомлень"""
    
    # OpenAI Configuration
    openai_api_key = EncryptedTextField(
        help_text="OpenAI API ключ (зберігається зашифровано)"
    )
    openai_model = models.CharField(
        max_length=50,
        default="gpt-4o",
        help_text="Fallback модель OpenAI (коли не вказана для бізнесу)"
    )
    
    # Global prompt settings
    base_system_prompt = models.TextField(
        default="You are a professional business communication assistant. Generate personalized, friendly, and professional greeting messages for potential customers who have inquired about services.",
        help_text="Fallback системний промпт для AI (коли не вказаний кастомний промпт для бізнесу)"
    )
    max_message_length = models.PositiveIntegerField(
        default=160,
        help_text="Fallback максимальна довжина повідомлення (коли не вказана для бізнесу)"
    )
    default_temperature = models.FloatField(
        default=0.7,
        help_text="Fallback temperature для AI генерації (коли не вказана для бізнесу)"
    )
    
    # Business rules
    always_include_business_name = models.BooleanField(
        default=True,
        help_text="Завжди включати назву бізнесу в повідомлення"
    )
    always_use_customer_name = models.BooleanField(
        default=True,
        help_text="Завжди використовувати ім'я клієнта, якщо доступне"
    )
    fallback_to_template = models.BooleanField(
        default=True,
        help_text="Використовувати шаблон як fallback при помилці AI"
    )
    
    # Rate limiting
    requests_per_minute = models.PositiveIntegerField(
        default=60,
        help_text="Максимальна кількість запитів до AI на хвилину"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Settings"
        verbose_name_plural = "AI Settings"
    
    def __str__(self):
        return f"AI Settings (Model: {self.openai_model})"


class FollowUpTemplate(models.Model):
    business = models.ForeignKey(
        YelpBusiness,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Який бізнес використовує цей шаблон. Null → шаблон за замовчуванням",
    )
    phone_available = models.BooleanField(
        default=False,
        help_text="Use this template when phone number was provided in text",
    )
    name = models.CharField(max_length=100, help_text="Лаконічна назва шаблону")
    template = models.TextField(
        help_text='Текст з плейсхолдерами: "{name}", "{jobs}", "{sep}"'
    )
    delay = models.DurationField(
        default=timedelta(hours=24),
        help_text="Затримка перед першим follow-up (наприклад, 24h)",
    )
    open_from = models.TimeField(
        default=time(8, 0), help_text="Час початку робочих годин (локальний час)"
    )
    open_to = models.TimeField(
        default=time(20, 0), help_text="Час закінчення робочих годин (локальний час)"
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (+{self.delay})"


class JobMapping(models.Model):
    """Глобальні налаштування для заміни назв послуг {jobs}"""
    original_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Оригінальна назва послуги, яка приходить з Yelp"
    )
    custom_name = models.CharField(
        max_length=200,
        help_text="Ваша власна назва для цієї послуги"
    )
    active = models.BooleanField(
        default=True,
        help_text="Чи активна ця заміна"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['original_name']
        verbose_name = "Job Name Mapping"
        verbose_name_plural = "Job Name Mappings"

    def __str__(self):
        return f"{self.original_name} → {self.custom_name}"


class LeadEvent(models.Model):
    event_id = models.CharField(max_length=64, unique=True, db_index=True)
    lead_id = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=32)
    user_type = models.CharField(max_length=32)
    user_id = models.CharField(max_length=64)
    user_display_name = models.CharField(max_length=100, blank=True)
    text = models.TextField(blank=True)
    cursor = models.TextField(blank=True)
    time_created = models.DateTimeField()
    raw = models.JSONField()
    from_backend = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event_id} @ {self.lead_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lead_id", "text"],
                name="uniq_follow_up_lead_text",
                condition=Q(event_type="FOLLOW_UP"),
            )
        ]


class LeadDetail(models.Model):
    lead_id = models.CharField(max_length=64, unique=True, db_index=True)
    business_id = models.CharField(max_length=64)
    conversation_id = models.CharField(max_length=64, blank=True)
    temporary_email_address = models.EmailField(max_length=200, blank=True, null=True)
    temporary_email_address_expiry = models.DateTimeField(null=True, blank=True)
    time_created = models.DateTimeField()
    last_event_time = models.DateTimeField(null=True, blank=True)
    user_display_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    project = models.JSONField()
    phone_opt_in = models.BooleanField(default=False)
    phone_in_text = models.BooleanField(
        default=False,
        help_text="Consumer provided phone number inside a text message",
    )
    phone_in_additional_info = models.BooleanField(
        default=False,
        help_text="Consumer provided phone number inside additional_info",
    )
    customer_replied = models.BooleanField(
        default=False,
        help_text="Customer has already replied at least once (to prevent repeated Customer Reply SMS)",
    )
    phone_sms_sent = models.BooleanField(
        default=False,
        help_text="Any SMS notification has already been sent for this lead (to prevent duplicate SMS)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"LeadDetail({self.lead_id})"



class CeleryTaskLog(models.Model):
    """Metadata for Celery task executions."""

    task_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    args = models.JSONField(blank=True, null=True)
    kwargs = models.JSONField(blank=True, null=True)
    eta = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Real time when message was sent to Yelp API")
    status = models.CharField(max_length=20)
    result = models.TextField(blank=True, null=True)
    traceback = models.TextField(blank=True, null=True)
    business_id = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"{self.task_id} {self.name} {self.status}"


class SMSLog(models.Model):
    """Log of SMS messages sent via Twilio."""
    
    # Basic SMS info
    sid = models.CharField(max_length=128, unique=True, db_index=True, help_text="Twilio Message SID")
    to_phone = models.CharField(max_length=32, db_index=True, help_text="Destination phone number")
    from_phone = models.CharField(max_length=32, help_text="Source phone number (Twilio)")
    body = models.TextField(help_text="SMS message content")
    
    # Context info  
    lead_id = models.CharField(max_length=64, blank=True, null=True, db_index=True, help_text="Related lead ID")
    business_id = models.CharField(max_length=128, blank=True, null=True, db_index=True, help_text="Related business ID")
    purpose = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Purpose: notification, auto_response, manual, api"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20, 
        default='sent', 
        help_text="Status: sent, delivered, failed, etc."
    )
    error_message = models.TextField(blank=True, null=True, help_text="Error details if failed")
    
    # Twilio metadata
    price = models.CharField(max_length=20, blank=True, null=True, help_text="SMS cost")
    price_unit = models.CharField(max_length=10, blank=True, null=True, help_text="Currency")
    direction = models.CharField(max_length=20, blank=True, null=True, help_text="outbound-api")
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True, help_text="When SMS was sent from our system")
    twilio_created_at = models.DateTimeField(null=True, blank=True, help_text="Twilio timestamp")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['business_id', '-sent_at']),
            models.Index(fields=['lead_id', '-sent_at']),
            models.Index(fields=['purpose', '-sent_at']),
            models.Index(fields=['status', '-sent_at']),
        ]

    def __str__(self):
        return f"SMS {self.sid} to {self.to_phone} ({self.status})"


class LeadPendingTask(models.Model):
    """Track Celery tasks scheduled for a lead."""

    lead_id = models.CharField(max_length=64, db_index=True)
    text = models.TextField()
    task_id = models.CharField(max_length=128, unique=True)
    phone_available = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lead_id", "text"],
                name="uniq_lead_text_active",
                condition=Q(active=True) & ~Q(text=""),
            )
        ]

    def __str__(self):
        return f"{self.task_id} for {self.lead_id}: {self.text[:20]}"


class NotificationSetting(models.Model):
    """Phone number and template used to notify about new leads."""

    business = models.ForeignKey(
        YelpBusiness,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Business for this setting. Null → global",
    )
    phone_number = models.CharField(max_length=64)
    message_template = models.TextField(
        help_text=(
            "Text with placeholders {business_id}, {lead_id}, "
            "{business_name}, {timestamp}, {phone}"
        )
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "phone_number"],
                name="uniq_notification_business_phone",
            )
        ]

    def __str__(self):
        return f"Notification to {self.phone_number}"


class TimeBasedGreeting(models.Model):
    """Time-based greetings for different parts of the day"""
    
    business = models.ForeignKey(
        YelpBusiness,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Business-specific greetings. Null = global default"
    )
    
    # Time ranges (24-hour format)
    morning_start = models.TimeField(default="05:00", help_text="Morning greeting start time")
    morning_end = models.TimeField(default="12:00", help_text="Morning greeting end time")
    
    afternoon_start = models.TimeField(default="12:00", help_text="Afternoon greeting start time")
    afternoon_end = models.TimeField(default="17:00", help_text="Afternoon greeting end time")
    
    evening_start = models.TimeField(default="17:00", help_text="Evening greeting start time")
    evening_end = models.TimeField(default="21:00", help_text="Evening greeting end time")
    
    # Greeting messages
    morning_greeting = models.CharField(max_length=100, default="Good morning", help_text="Morning greeting")
    afternoon_greeting = models.CharField(max_length=100, default="Good afternoon", help_text="Afternoon greeting")
    evening_greeting = models.CharField(max_length=100, default="Good evening", help_text="Evening greeting")
    night_greeting = models.CharField(max_length=100, default="Hello", help_text="Late night greeting (after evening_end)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business"],
                name="uniq_greeting_per_business",
                condition=models.Q(business__isnull=False)
            )
        ]
        verbose_name = "Time-based Greeting"
        verbose_name_plural = "Time-based Greetings"
    
    def __str__(self):
        if self.business:
            return f"Greetings for {self.business.name}"
        return "Global Default Greetings"


class LeadActivityLog(models.Model):
    """Detailed persistent logging for every lead activity"""
    
    # Lead identification
    lead_id = models.CharField(max_length=128, db_index=True)
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Categorization
    activity_type = models.CharField(max_length=50, db_index=True, choices=[
        ('WEBHOOK', 'Webhook Processing'),
        ('PLANNING', 'Follow-up Planning'),
        ('EXECUTION', 'Message Execution'),
        ('ANALYSIS', 'Event Analysis'),
        ('ERROR', 'Error Handling'),
    ])
    
    component = models.CharField(max_length=30, choices=[
        ('BACKEND', 'Django Backend'),
        ('WORKER', 'RQ Worker'),
        ('SCHEDULER', 'RQ Scheduler'),
        ('API', 'API Request'),
    ])
    
    event_name = models.CharField(max_length=100, help_text="Function or event name")
    
    # Content
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    # Optional relationships
    business_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    task_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['lead_id', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
            models.Index(fields=['business_id', '-timestamp']),
            models.Index(fields=['task_id', '-timestamp']),
        ]
        
    def __str__(self):
        return f"[{self.activity_type}] {self.lead_id}: {self.message[:50]}"


class SystemErrorLog(models.Model):
    """System-wide error tracking for monitoring and diagnostics"""
    
    # Error identification
    error_id = models.CharField(max_length=128, unique=True, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Error categorization
    error_type = models.CharField(max_length=50, choices=[
        ('API_ERROR', 'API Communication Error'),
        ('DJANGO_ERROR', 'Django Application Error'), 
        ('TASK_ERROR', 'RQ Task Execution Error'),
        ('TOKEN_ERROR', 'Token/Authentication Error'),
        ('DATABASE_ERROR', 'Database Operation Error'),
        ('TIMING_ERROR', 'Follow-up Timing Error'),
        ('WEBHOOK_ERROR', 'Webhook Processing Error'),
        ('VALIDATION_ERROR', 'Data Validation Error'),
    ], db_index=True)
    
    severity = models.CharField(max_length=20, choices=[
        ('LOW', 'Low - Informational'),
        ('MEDIUM', 'Medium - Warning'),
        ('HIGH', 'High - Error'),
        ('CRITICAL', 'Critical - System Down'),
    ], default='MEDIUM', db_index=True)
    
    # Error context
    component = models.CharField(max_length=50)  # webhook_views, tasks, etc.
    function_name = models.CharField(max_length=100, blank=True)
    line_number = models.IntegerField(null=True, blank=True)
    
    # Error content
    error_message = models.TextField()
    exception_type = models.CharField(max_length=100, blank=True)
    traceback = models.TextField(blank=True)
    
    # Context data
    lead_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    business_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    task_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    
    # Additional context
    metadata = models.JSONField(default=dict, blank=True)
    
    # Resolution tracking
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['error_type', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
            models.Index(fields=['lead_id', '-timestamp']),
            models.Index(fields=['resolved', '-timestamp']),
        ]
        
    def __str__(self):
        return f"[{self.error_type}] {self.error_message[:50]}"


class SystemHealthMetric(models.Model):
    """System performance and health metrics tracking"""
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metric_type = models.CharField(max_length=50, choices=[
        ('API_RESPONSE_TIME', 'API Response Time'),
        ('FOLLOW_UP_SUCCESS_RATE', 'Follow-up Success Rate'),
        ('QUEUE_LENGTH', 'RQ Queue Length'),
        ('DATABASE_QUERY_TIME', 'Database Query Time'),
        ('YELP_API_SUCCESS_RATE', 'Yelp API Success Rate'),
        ('TOKEN_REFRESH_RATE', 'Token Refresh Rate'),
        ('MEMORY_USAGE', 'Memory Usage'),
        ('ACTIVE_LEADS', 'Active Leads Count'),
    ], db_index=True)
    
    # Metric values
    value = models.FloatField()
    unit = models.CharField(max_length=20, default='count')  # ms, %, count, MB
    
    # Context
    component = models.CharField(max_length=50, blank=True)
    business_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['metric_type', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        
    def __str__(self):
        return f"{self.metric_type}: {self.value}{self.unit}"


