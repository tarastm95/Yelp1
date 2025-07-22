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


