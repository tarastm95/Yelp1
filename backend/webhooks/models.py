from django.db import models
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
    business_id   = models.CharField(max_length=128, unique=True, db_index=True)
    access_token  = EncryptedTextField()
    refresh_token = EncryptedTextField(null=True, blank=True)
    expires_at    = models.DateTimeField(null=True, blank=True)
    scopes        = models.TextField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)


class YelpBusiness(models.Model):
    """Stores basic info about a Yelp business."""

    business_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    time_zone = models.CharField(max_length=64, blank=True)
    open_days = models.CharField(max_length=128, blank=True)
    open_hours = models.TextField(blank=True)
    details = models.JSONField(blank=True, null=True)
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
    enabled = models.BooleanField(
        default=False,
        help_text="Увімкнути/вимкнути автoвідповіді"
    )
    access_token     = EncryptedTextField(help_text="Yelp API access token")
    refresh_token    = EncryptedTextField(blank=True,
                                        help_text="Yelp API refresh token (дійсний 365 днів)")
    token_expires_at = models.DateTimeField(null=True, blank=True,
                                            help_text="Коли access_token перестане бути дійсним")

    # Вітальне повідомлення
    greeting_template = models.TextField(
        default="Hello{sep}{name}! Thank you for your inquiry regarding “{jobs}”.",
        help_text="Шаблон першого повідомлення з плейсхолдерами {name}, {jobs}, {sep}"
    )
    include_name = models.BooleanField(
        default=True,
        help_text="Включати ім’я клієнта у вітальне повідомлення"
    )
    include_jobs = models.BooleanField(
        default=True,
        help_text="Включати список робіт у вітальне повідомлення"
    )

    greeting_delay = models.PositiveIntegerField(
        default=0,
        help_text="Затримка перед привітанням, в секундах",
    )

    # Вбудований follow-up
    follow_up_template = models.TextField(
        default="Just checking back in{sep}{name} — any questions about “{jobs}”?",
        help_text="Шаблон follow-up повідомлення з плейсхолдерами {name}, {jobs}, {sep}"
    )
    follow_up_delay = models.PositiveIntegerField(
        default=2,
        help_text="Затримка перед follow-up, в секундах"
    )

    export_to_sheets = models.BooleanField(
        default=False,
        help_text="Записувати нові ліди в Google Sheets"
    )

    greeting_open_from = models.TimeField(
        default=time(8, 0),
        help_text="Час початку робочих годин для привітання (локальний час)"
    )
    greeting_open_to = models.TimeField(
        default=time(20, 0),
        help_text="Час завершення робочих годин для привітання (локальний час)"
    )
    follow_up_open_from = models.TimeField(
        default=time(8, 0),
        help_text="Час початку робочих годин для built-in follow-up (локальний час)"
    )
    follow_up_open_to = models.TimeField(
        default=time(20, 0),
        help_text="Час завершення робочих годин для built-in follow-up (локальний час)"
    )

    def __str__(self):
        return f"AutoResponseSettings(id={self.id}, enabled={self.enabled})"


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
    name = models.CharField(
        max_length=100,
        help_text="Лаконічна назва шаблону"
    )
    template = models.TextField(
        help_text='Текст з плейсхолдерами: "{name}", "{jobs}", "{sep}"'
    )
    delay = models.DurationField(
        default=timedelta(hours=24),
        help_text="Затримка перед першим follow-up (наприклад, 24h)"
    )
    open_from = models.TimeField(default=time(8,0), help_text="Час початку робочих годин (локальний час)")
    open_to = models.TimeField(default=time(20,0), help_text="Час закінчення робочих годин (локальний час)")
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (+{self.delay})"


class ScheduledMessage(models.Model):
    lead_id = models.CharField(max_length=64, db_index=True)
    template = models.ForeignKey(
        FollowUpTemplate,
        on_delete=models.CASCADE,
        help_text="Який шаблон FollowUpTemplate використати"
    )
    next_run = models.DateTimeField(
        help_text="Час наступного запуску повідомлення"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def schedule_next(self):
        # Оновлюємо next_run згідно з delay із шаблону
        self.next_run = timezone.now() + self.template.delay
        self.save(update_fields=['next_run'])

    def __str__(self):
        return f"#{self.pk} lead={self.lead_id} template={self.template.name} at {self.next_run}"


class ScheduledMessageHistory(models.Model):
    scheduled = models.ForeignKey(
        ScheduledMessage,
        on_delete=models.CASCADE,
        related_name='history'
    )
    executed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16)  # 'success' або 'error'
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"History for #{self.scheduled_id} at {self.executed_at}"


class LeadEvent(models.Model):
    event_id          = models.CharField(max_length=64, unique=True, db_index=True)
    lead_id           = models.CharField(max_length=64, db_index=True)
    event_type        = models.CharField(max_length=32)
    user_type         = models.CharField(max_length=32)
    user_id           = models.CharField(max_length=64)
    user_display_name = models.CharField(max_length=100, blank=True)
    text              = models.TextField(blank=True)
    cursor            = models.CharField(max_length=128, blank=True)
    time_created      = models.DateTimeField()
    raw               = models.JSONField()
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event_id} @ {self.lead_id}"


class LeadDetail(models.Model):
    lead_id                        = models.CharField(max_length=64, unique=True, db_index=True)
    business_id                    = models.CharField(max_length=64)
    conversation_id                = models.CharField(max_length=64, blank=True)
    temporary_email_address        = models.EmailField(max_length=200, blank=True)
    temporary_email_address_expiry = models.DateTimeField(null=True, blank=True)
    time_created                   = models.DateTimeField()
    last_event_time                = models.DateTimeField(null=True, blank=True)
    user_display_name              = models.CharField(max_length=100, blank=True)
    project                        = models.JSONField()
    phone_opt_in                   = models.BooleanField(default=False)
    created_at                     = models.DateTimeField(auto_now_add=True)
    updated_at                     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"LeadDetail({self.lead_id})"

class LeadScheduledMessage(models.Model):
    lead_id          = models.CharField(max_length=64, db_index=True)
    content          = models.TextField(help_text="Текст повідомлення")
    interval_minutes = models.PositiveIntegerField(help_text="Інтервал у хвилинах")
    next_run         = models.DateTimeField(help_text="Час наступного виконання")
    active           = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def schedule_next(self):
        self.next_run = timezone.now() + timedelta(minutes=self.interval_minutes)
        self.save(update_fields=['next_run'])

    def __str__(self):
        return f"LeadScheduledMessage #{self.pk} to {self.lead_id} every {self.interval_minutes}min → {self.next_run}"


class LeadScheduledMessageHistory(models.Model):
    scheduled   = models.ForeignKey(
        LeadScheduledMessage,
        on_delete=models.CASCADE,
        related_name='history'
    )
    executed_at = models.DateTimeField(auto_now_add=True)
    status      = models.CharField(max_length=16, help_text="'success' або 'error'")
    error       = models.TextField(blank=True, null=True, help_text="Текст помилки, якщо є")

    def __str__(self):
        return f"History #{self.pk} for msg {self.scheduled_id} at {self.executed_at}"


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
    business_id = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"{self.task_id} {self.name} {self.status}"


class AutoResponseSettingsTemplate(models.Model):
    """Stored presets for AutoResponseSettings."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    data = models.JSONField(help_text="Serialized AutoResponseSettings data")
    follow_up_templates = models.JSONField(
        default=list,
        blank=True,
        help_text="Serialized list of additional FollowUpTemplate objects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
