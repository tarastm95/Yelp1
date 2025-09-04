from rest_framework import serializers
from datetime import timedelta
from .models import (
    Event,
    AutoResponseSettings,
    ProcessedLead,
    FollowUpTemplate,
    JobMapping,
    LeadEvent,
    LeadDetail,
    YelpToken,
    YelpBusiness,
    CeleryTaskLog,
    LeadPendingTask,
    NotificationSetting,
    SMSLog,
    AISettings,
    TimeBasedGreeting,
)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "created_at", "payload"]


class AutoResponseSettingsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    business_id = serializers.CharField(
        source="business.business_id", allow_null=True, required=False
    )

    class Meta:
        model = AutoResponseSettings
        fields = [
            "id",
            "business_id",
            "phone_available",
            "enabled",
            "greeting_template",
            "greeting_off_hours_template",
            "greeting_delay",
            "greeting_open_from",
            "greeting_open_to",
            "greeting_open_days",
            "export_to_sheets",
            # AI fields
            "use_ai_greeting",
            "ai_response_style",
            "ai_include_location",
            "ai_mention_response_time",
            "ai_custom_prompt",
            # AI Business Data Settings
            "ai_include_rating",
            "ai_include_categories",
            "ai_include_phone",
            "ai_include_website",
            "ai_include_price_range",
            "ai_include_hours",
            "ai_include_reviews_count",
            "ai_include_address",
            "ai_include_transactions",
            "ai_max_message_length",
            # Business-specific AI Model Settings
            "ai_model",
            "ai_temperature",
            # SMS Notification Settings
            "sms_on_phone_found",
            "sms_on_customer_reply", 
            "sms_on_phone_opt_in",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        business_id = (
            validated_data.pop("business", {}).get("business_id")
            if "business" in validated_data
            else None
        )
        business = None
        if business_id:
            business = YelpBusiness.objects.filter(business_id=business_id).first()
        validated_data["business"] = business
        return super().create(validated_data)

    def update(self, instance, validated_data):
        biz_info = validated_data.pop("business", None)
        if biz_info is not None:
            bid = biz_info.get("business_id")
            instance.business = (
                YelpBusiness.objects.filter(business_id=bid).first() if bid else None
            )
        return super().update(instance, validated_data)


class DurationSecondsField(serializers.IntegerField):
    """
    IntegerField, який при виведенні конвертує timedelta → число секунд,
    а при записі приймає int (секунди) і не конвертує нічого.
    """

    def to_representation(self, value):
        # value може бути або timedelta (коли читаємо з instance.delay),
        # або вже int (якщо десь проміжно).
        if hasattr(value, "total_seconds"):
            return int(value.total_seconds())
        return super().to_representation(value)


class FollowUpTemplateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    business_id = serializers.CharField(
        source="business.business_id", allow_null=True, required=False
    )
    phone_available = serializers.BooleanField(required=False)
    delay = DurationSecondsField(
        help_text="Затримка перед першим follow-up в секундах",
        write_only=False,  # дозволяємо як читати, так і писати
    )

    class Meta:
        model = FollowUpTemplate
        fields = [
            "id",
            "business_id",
            "phone_available",
            "name",
            "template",
            "delay",
            "open_from",
            "open_to",
            "active",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        secs = validated_data.pop("delay")
        biz_info = validated_data.pop("business", None)
        phone_available = validated_data.pop("phone_available", False)
        if isinstance(biz_info, dict):
            bid = biz_info.get("business_id")
            validated_data["business"] = (
                YelpBusiness.objects.filter(business_id=bid).first() if bid else None
            )
        elif isinstance(biz_info, YelpBusiness) or biz_info is None:
            validated_data["business"] = biz_info
        else:
            validated_data["business"] = None
        validated_data["delay"] = timedelta(seconds=secs)
        validated_data["phone_available"] = phone_available
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "delay" in validated_data:
            secs = validated_data.pop("delay")
            validated_data["delay"] = timedelta(seconds=secs)
        biz_info = validated_data.pop("business", None)
        phone_available = validated_data.pop("phone_available", None)
        if biz_info is not None:
            if isinstance(biz_info, dict):
                bid = biz_info.get("business_id")
                instance.business = (
                    YelpBusiness.objects.filter(business_id=bid).first()
                    if bid
                    else None
                )
            elif isinstance(biz_info, YelpBusiness):
                instance.business = biz_info
            else:
                instance.business = None
        if phone_available is not None:
            instance.phone_available = phone_available
        return super().update(instance, validated_data)


class JobMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobMapping
        fields = [
            'id',
            'original_name',
            'custom_name',
            'active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProcessedLeadSerializer(serializers.ModelSerializer):
    business_name = serializers.SerializerMethodField()

    class Meta:
        model = ProcessedLead
        fields = ["lead_id", "business_id", "business_name", "processed_at"]
        read_only_fields = ["lead_id", "business_id", "business_name", "processed_at"]

    def get_business_name(self, obj):
        """Get business name from YelpBusiness model if it exists"""
        try:
            from .models import YelpBusiness
            # Use a class-level cache to avoid repeated queries for the same business
            if not hasattr(self.__class__, '_business_cache'):
                self.__class__._business_cache = {}
            
            if obj.business_id not in self.__class__._business_cache:
                business = YelpBusiness.objects.filter(business_id=obj.business_id).first()
                self.__class__._business_cache[obj.business_id] = business.name if business else obj.business_id
            
            return self.__class__._business_cache[obj.business_id]
        except Exception:
            return obj.business_id


class LeadEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadEvent
        fields = [
            "id",
            "event_id",
            "lead_id",
            "event_type",
            "user_type",
            "user_id",
            "user_display_name",
            "text",
            "cursor",
            "time_created",
            "raw",
            "from_backend",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "event_id", "created_at", "updated_at", "from_backend"]


class LeadDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadDetail
        fields = [
            "lead_id",
            "business_id",
            "conversation_id",
            "temporary_email_address",
            "temporary_email_address_expiry",
            "time_created",
            "last_event_time",
            "user_display_name",
            "project",
            "phone_opt_in",
            "phone_in_text",
            "phone_in_additional_info",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields




class YelpBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = YelpBusiness
        fields = [
            "business_id",
            "name",
            "location",
            "time_zone",
            "open_days",
            "open_hours",
            "details",
        ]
        read_only_fields = fields


class YelpTokenInfoSerializer(serializers.ModelSerializer):
    business = serializers.SerializerMethodField()

    class Meta:
        model = YelpToken
        fields = [
            "business_id",
            "expires_at",
            "updated_at",
            "business",
        ]

    def get_business(self, obj):
        biz = YelpBusiness.objects.filter(business_id=obj.business_id).first()
        if not biz:
            return None
        return YelpBusinessSerializer(biz).data


class CeleryTaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryTaskLog
        fields = [
            "task_id",
            "name",
            "args",
            "kwargs",
            "eta",
            "started_at",
            "finished_at",
            "status",
            "result",
            "traceback",
            "business_id",
        ]
        read_only_fields = fields


class LeadPendingTaskSerializer(serializers.ModelSerializer):
    """
    Серіалізер для LeadPendingTask, сумісний з CeleryTaskLogSerializer
    для відображення scheduled та canceled завдань у dashboard
    """
    name = serializers.SerializerMethodField()
    args = serializers.SerializerMethodField()
    kwargs = serializers.SerializerMethodField()
    eta = serializers.SerializerMethodField()
    started_at = serializers.SerializerMethodField()
    finished_at = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    traceback = serializers.SerializerMethodField()
    business_id = serializers.SerializerMethodField()
    
    class Meta:
        model = LeadPendingTask
        fields = [
            "task_id",
            "name", 
            "args",
            "kwargs",
            "eta",
            "started_at",
            "finished_at",
            "status",
            "result", 
            "traceback",
            "business_id",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return "send_follow_up"
    
    def get_args(self, obj):
        # Отримуємо business_id через ProcessedLead
        try:
            from .models import ProcessedLead
            pl = ProcessedLead.objects.filter(lead_id=obj.lead_id).first()
            business_id = pl.business_id if pl else None
            return [obj.lead_id, obj.text, business_id]
        except:
            return [obj.lead_id, obj.text, None]
    
    def get_kwargs(self, obj):
        return {}
    
    def get_eta(self, obj):
        # Для scheduled завдань - спробувати отримати ETA з RQ, або використати created_at
        if obj.active and obj.task_id:
            try:
                import django_rq
                queue = django_rq.get_queue("default")
                job = queue.fetch_job(obj.task_id)
                if job and hasattr(job, 'scheduled_for'):
                    return job.scheduled_for
            except:
                pass
        # Fallback - використовуємо created_at як ETA
        return obj.created_at
    
    def get_started_at(self, obj):
        return None if obj.active else obj.created_at
    
    def get_finished_at(self, obj):
        return None
    
    def get_status(self, obj):
        return "SCHEDULED" if obj.active else "CANCELED"
    
    def get_result(self, obj):
        return None
    
    def get_traceback(self, obj):
        return None
    
    def get_business_id(self, obj):
        try:
            from .models import ProcessedLead
            pl = ProcessedLead.objects.filter(lead_id=obj.lead_id).first()
            return pl.business_id if pl else None
        except:
            return None


class MessageTaskSerializer(serializers.ModelSerializer):
    executed_at = serializers.DateTimeField(source="finished_at")
    text = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    task_type = serializers.SerializerMethodField()

    class Meta:
        model = CeleryTaskLog
        fields = ["executed_at", "text", "business_name", "task_type"]

    def get_text(self, obj):
        args = obj.args or []
        if obj.name == "send_follow_up" and len(args) >= 2:
            return args[1]
        # Other task types were removed
        return ""

    def get_business_name(self, obj):
        biz = YelpBusiness.objects.filter(business_id=obj.business_id).first()
        return biz.name if biz else None

    def get_task_type(self, obj):
        mapping = {
            "send_follow_up": "Follow-up",
        }
        return mapping.get(obj.name, obj.name)


class SendSMSSerializer(serializers.Serializer):
    """Validate data for sending an SMS message."""

    to = serializers.CharField()
    body = serializers.CharField()


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = ["id", "phone_number", "message_template"]
        read_only_fields = ["id"]


class SMSLogSerializer(serializers.ModelSerializer):
    business_name = serializers.SerializerMethodField()

    class Meta:
        model = SMSLog
        fields = [
            "id",
            "sid",
            "to_phone",
            "from_phone",
            "body",
            "lead_id",
            "business_id",
            "business_name",
            "purpose",
            "status",
            "error_message",
            "price",
            "price_unit",
            "direction",
            "sent_at",
            "twilio_created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sid",
            "sent_at",
            "twilio_created_at",
            "updated_at",
            "business_name"
        ]

    def get_business_name(self, obj):
        """Get business name from business_id."""
        if not obj.business_id:
            return None
        try:
            from .models import YelpBusiness
            business = YelpBusiness.objects.filter(business_id=obj.business_id).first()
            return business.name if business else obj.business_id
        except Exception:
            return obj.business_id


class AISettingsSerializer(serializers.ModelSerializer):
    """Serializer для глобальних AI налаштувань"""

    class Meta:
        model = AISettings
        fields = [
            "id",
            "openai_model",
            "base_system_prompt",
            "max_message_length",
            "default_temperature",
            "always_include_business_name",
            "always_use_customer_name",
            "fallback_to_template",
            "requests_per_minute",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # Note: openai_api_key is intentionally excluded from serialization for security


class AIGlobalSettingsSerializer(serializers.ModelSerializer):
    """Спрощений serializer для Global AI Settings UI - тільки системні налаштування"""

    class Meta:
        model = AISettings
        fields = [
            "id",
            # 🔑 Критичні системні налаштування
            "base_system_prompt",          # Fallback промпт
            "always_include_business_name", # Глобальне правило
            "always_use_customer_name",     # Глобальне правило
            "fallback_to_template",         # Fallback поведінка
            "requests_per_minute",          # Rate limiting
            "created_at",
            "updated_at",
            # 🚫 Приховані поля (тепер доступні per-business):
            # "openai_model",           # → Business AI Settings
            # "max_message_length",     # → Business AI Settings  
            # "default_temperature",    # → Business AI Settings
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # Note: openai_api_key налаштовується через admin або .env


class TimeBasedGreetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeBasedGreeting
        fields = [
            "id",
            "business",
            "morning_start",
            "morning_end", 
            "afternoon_start",
            "afternoon_end",
            "evening_start",
            "evening_end",
            "morning_greeting",
            "afternoon_greeting",
            "evening_greeting",
            "night_greeting",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



