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
    NotificationSetting,
    SMSLog,
    WhatsAppLog,
    WhatsAppNotificationSetting,
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
            # AI fields - maximally simplified
            "use_ai_greeting", 
            # All AI behavior controlled via Custom Instructions (location, response time, business data, style)
            "ai_custom_prompt",
            # Business data controlled via Custom Instructions (individual fields removed)
            "ai_max_message_length",
            # Business-specific AI Model Settings
            "ai_model",
            "ai_temperature",
            # Vector Search Settings
            "vector_similarity_threshold",
            "vector_search_limit", 
            "vector_chunk_types",
            # Sample Replies Settings (режим 2: AI Generated)
            "use_sample_replies",
            "sample_replies_content",
            "sample_replies_filename",
            "sample_replies_priority",
            # SMS Notification Settings
            "sms_on_phone_found",
            "sms_on_customer_reply", 
            "sms_on_phone_opt_in",
            # WhatsApp Notification Settings
            "whatsapp_on_phone_found",
            "whatsapp_on_customer_reply", 
            "whatsapp_on_phone_opt_in",
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

    def validate(self, data):
        """✅ Валідація: Custom Instructions обов'язкові для AI режиму"""
        
        use_ai_greeting = data.get('use_ai_greeting', False)
        ai_custom_prompt = data.get('ai_custom_prompt', '')
        
        if use_ai_greeting and not ai_custom_prompt.strip():
            raise serializers.ValidationError({
                'ai_custom_prompt': 'Custom Instructions are required when AI Generation is enabled. Please provide fallback instructions to ensure quality responses.'
            })
        
        return data
    
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
            "representative_name",
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
    text = serializers.SerializerMethodField()
    
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
            "sent_at",
            "status",
            "result",
            "traceback",
            "business_id",
            "text",  # Add text field
        ]
        read_only_fields = fields
    
    def get_text(self, obj):
        """Extract message text from args or kwargs - same logic as MessageTaskSerializer"""
        args = obj.args or []
        kwargs = obj.kwargs or {}
        
        if obj.name == "send_follow_up":
            # Check args first (positional parameters)
            if len(args) >= 2:
                return args[1]
            # Check kwargs (named parameters from generate_and_send_follow_up)
            elif 'text' in kwargs:
                return kwargs['text']
        elif obj.name == "generate_and_send_greeting":
            # For generate_and_send_greeting: args = [lead_id, business_id, phone_available, within_hours, use_sample_replies]
            lead_id = args[0] if len(args) >= 1 else None
            business_id = args[1] if len(args) >= 2 else None
            
            phone_available = None
            use_sample_replies = False
            
            if len(args) >= 5:
                phone_available = args[2]
                use_sample_replies = args[4]
            elif len(args) >= 4:
                # Legacy format without explicit phone_available argument
                use_sample_replies = args[3]
            
            if phone_available is None:
                from .models import LeadPendingTask
                pending = LeadPendingTask.objects.filter(task_id=obj.task_id).first()
                if pending is not None:
                    phone_available = getattr(pending, "phone_available", False)
                else:
                    phone_available = False
            
            scenario = "phone_available=True (Phone Number in Message)" if phone_available else "phone_available=False (No Phone / Phone Opt-in)"
            
            if obj.status == 'GENERATING':
                mode = "Sample Replies AI" if use_sample_replies else "Custom Instructions AI"
                return f"🤖 Generating greeting with {mode} · {scenario}"
            elif obj.status == 'SCHEDULED':
                mode = "Sample Replies AI" if use_sample_replies else "Custom Instructions AI"
                return f"🤖 AI Greeting ({mode} · {scenario})"
            else:
                # For completed/failed - try to find the actual message
                from .models import LeadEvent
                if lead_id:
                    event = LeadEvent.objects.filter(
                        lead_id=lead_id,
                        user_type='BIZ',
                        from_backend=True
                    ).order_by('-time_created').first()
                    if event:
                        prefix = f"[{scenario}] "
                        return (prefix + event.text)[:200] if event.text else f"[AI Greeting Sent · {scenario}]"
                return f"[AI Greeting · {scenario}]"
        elif obj.name == "generate_and_send_follow_up" and len(args) >= 2:
            # For generate_and_send_follow_up: args[1] is template_id
            template_id = args[1]
            # Try to get the actual generated text from LeadPendingTask by task_id
            from .models import LeadPendingTask
            task = LeadPendingTask.objects.filter(task_id=obj.task_id).first()
            if task and task.text:
                return task.text
            # If no task found or no text yet, try by lead_id + template_id (fallback)
            lead_id = args[0] if len(args) >= 1 else None
            if lead_id:
                task = LeadPendingTask.objects.filter(
                    lead_id=lead_id, 
                    template_id=template_id
                ).order_by('-created_at').first()  # Get latest task
                if task and task.text:
                    return task.text
            # If no text yet, show template info
            from .models import FollowUpTemplate
            template = FollowUpTemplate.objects.filter(id=template_id).first()
            if template:
                return f"[Template: {template.name}] {template.template[:100]}"
            return f"[Template ID: {template_id}]"
        
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
        kwargs = obj.kwargs or {}
        
        if obj.name == "send_follow_up":
            # Check args first (positional parameters)
            if len(args) >= 2:
                return args[1]
            # Check kwargs (named parameters from generate_and_send_follow_up)
            elif 'text' in kwargs:
                return kwargs['text']
        elif obj.name == "generate_and_send_greeting":
            # For generate_and_send_greeting: args = [lead_id, business_id, phone_available, within_hours, use_sample_replies]
            # Text will be generated, so show status
            lead_id = args[0] if len(args) >= 1 else None
            business_id = args[1] if len(args) >= 2 else None
            
            phone_available = None
            use_sample_replies = False
            
            if len(args) >= 5:
                phone_available = args[2]
                use_sample_replies = args[4]
            elif len(args) >= 4:
                use_sample_replies = args[3]
            
            if phone_available is None:
                from .models import LeadPendingTask
                pending = LeadPendingTask.objects.filter(task_id=obj.task_id).first()
                if pending is not None:
                    phone_available = getattr(pending, "phone_available", False)
                else:
                    phone_available = False
            
            scenario = "phone_available=True (Phone Number in Message)" if phone_available else "phone_available=False (No Phone / Phone Opt-in)"
            
            if obj.status == 'GENERATING':
                mode = "Sample Replies AI" if use_sample_replies else "Custom Instructions AI"
                return f"🤖 Generating greeting with {mode} · {scenario}"
            elif obj.status == 'SCHEDULED':
                mode = "Sample Replies AI" if use_sample_replies else "Custom Instructions AI"
                return f"🤖 AI Greeting ({mode} · {scenario})"
            else:
                # For completed/failed - try to find the actual message
                from .models import LeadEvent
                if lead_id:
                    event = LeadEvent.objects.filter(
                        lead_id=lead_id,
                        user_type='BIZ',
                        from_backend=True
                    ).order_by('-time_created').first()
                    if event:
                        prefix = f"[{scenario}] "
                        return (prefix + event.text)[:200] if event.text else f"[AI Greeting Sent · {scenario}]"
                return f"[AI Greeting · {scenario}]"
        elif obj.name == "generate_and_send_follow_up" and len(args) >= 2:
            # For generate_and_send_follow_up: args[1] is template_id
            template_id = args[1]
            # Try to get the actual generated text from LeadPendingTask by task_id
            from .models import LeadPendingTask
            task = LeadPendingTask.objects.filter(task_id=obj.task_id).first()
            if task and task.text:
                return task.text
            # If no task found or no text yet, try by lead_id + template_id (fallback)
            lead_id = args[0] if len(args) >= 1 else None
            if lead_id:
                task = LeadPendingTask.objects.filter(
                    lead_id=lead_id, 
                    template_id=template_id
                ).order_by('-created_at').first()  # Get latest task
                if task and task.text:
                    return task.text
            # If no text yet, show template info
            from .models import FollowUpTemplate
            template = FollowUpTemplate.objects.filter(id=template_id).first()
            if template:
                return f"[Template: {template.name}] {template.template[:100]}"
            return f"[Template ID: {template_id}]"
        # Other task types were removed
        return ""

    def get_business_name(self, obj):
        biz = YelpBusiness.objects.filter(business_id=obj.business_id).first()
        return biz.name if biz else None

    def get_task_type(self, obj):
        mapping = {
            "send_follow_up": "Follow-up",
            "generate_and_send_follow_up": "Follow-up (AI)",
            "generate_and_send_greeting": "Greeting (AI)",
        }
        return mapping.get(obj.name, obj.name)


class SendSMSSerializer(serializers.Serializer):
    """Validate data for sending an SMS message."""

    to = serializers.CharField()
    body = serializers.CharField()


class SendWhatsAppSerializer(serializers.Serializer):
    """Validate data for sending a WhatsApp message."""
    to = serializers.CharField()
    body = serializers.CharField()


class WhatsAppNotificationSettingSerializer(serializers.ModelSerializer):
    business_id = serializers.SerializerMethodField()
    phone_number = serializers.CharField(required=False, allow_blank=True, default='')
    
    def get_business_id(self, obj):
        return obj.business.business_id if obj.business else None
    
    def validate(self, data):
        """Custom validation for Content Templates vs Simple Templates"""
        use_content_template = data.get('use_content_template', False)
        
        # Phone number is always required
        if not data.get('phone_number') or data.get('phone_number', '').strip() == '':
            raise serializers.ValidationError({
                'phone_number': 'Phone number is required'
            })
        
        if use_content_template:
            # For Content Templates, content_sid is required
            if not data.get('content_sid'):
                raise serializers.ValidationError({
                    'content_sid': 'Content SID is required when using Content Template'
                })
            # message_template can be empty for Content Templates
            if not data.get('message_template'):
                data['message_template'] = ''  # Allow empty for Content Templates
        else:
            # For Simple Templates, message_template is required
            if not data.get('message_template'):
                raise serializers.ValidationError({
                    'message_template': 'Message template is required for Simple Template'
                })
        
        return data
    
    class Meta:
        model = WhatsAppNotificationSetting
        fields = [
            "id", 
            "business_id",
            "phone_number", 
            "message_template",  # Legacy
            "use_content_template",  # NEW
            "content_sid",  # NEW
            "content_name",  # NEW
            "variable_mapping",  # NEW
            "enabled",  # NEW
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "business_id", "created_at", "updated_at"]


class WhatsAppLogSerializer(serializers.ModelSerializer):
    business_name = serializers.SerializerMethodField()
    
    class Meta:
        model = WhatsAppLog
        fields = '__all__'
    
    def get_business_name(self, obj):
        if obj.business_id:
            business = YelpBusiness.objects.filter(business_id=obj.business_id).first()
            return business.name if business else None
        return None


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



