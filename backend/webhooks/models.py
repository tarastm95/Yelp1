from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, time
from .fields import EncryptedTextField


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
    phone_opt_in = models.BooleanField(
        default=False,
        help_text="Use these settings when consumer phone number is available",
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
    ai_response_style = models.CharField(
        max_length=20,
        choices=[
            ('formal', 'Formal'),
            ('casual', 'Casual'),
            ('auto', 'Auto'),
        ],
        default='auto',
        help_text="Стиль AI відповіді"
    )
    ai_include_location = models.BooleanField(
        default=False,
        help_text="Включати локацію бізнесу в AI повідомлення"
    )
    ai_mention_response_time = models.BooleanField(
        default=False,
        help_text="Згадувати очікуваний час відповіді в AI повідомленнях"
    )
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

    export_to_sheets = models.BooleanField(
        default=False, help_text="Записувати нові ліди в Google Sheets"
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
        help_text="Модель OpenAI для використання"
    )
    
    # Global prompt settings
    base_system_prompt = models.TextField(
        default="You are a professional business communication assistant. Generate personalized, friendly, and professional greeting messages for potential customers who have inquired about services.",
        help_text="Базовий системний промпт для AI"
    )
    max_message_length = models.PositiveIntegerField(
        default=160,
        help_text="Максимальна довжина згенерованого повідомлення"
    )
    default_temperature = models.FloatField(
        default=0.7,
        help_text="Temperature для AI генерації (0.0-1.0)"
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
    phone_opt_in = models.BooleanField(
        default=False,
        help_text="Use this template when consumer phone number is available",
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
    phone_in_dialog = models.BooleanField(
        default=False,
        help_text="Consumer provided phone number in reply to auto message",
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
    phone_opt_in = models.BooleanField()
    phone_available = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lead_id", "text"],
                name="uniq_lead_text",
                condition=~Q(text=""),
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


