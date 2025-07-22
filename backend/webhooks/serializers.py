from rest_framework import serializers
from datetime import timedelta
from .models import (
    Event,
    AutoResponseSettings,
    ProcessedLead,
    FollowUpTemplate,
    LeadEvent,
    LeadDetail,
    YelpToken,
    YelpBusiness,
    CeleryTaskLog,
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
            "phone_opt_in",
            "phone_available",
            "enabled",
            "greeting_template",
            "greeting_off_hours_template",
            "greeting_delay",
            "greeting_open_from",
            "greeting_open_to",
            "include_name",
            "include_jobs",
            "export_to_sheets",
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
    phone_opt_in = serializers.BooleanField(required=False)
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
            "phone_opt_in",
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
        phone_opt_in = validated_data.pop("phone_opt_in", False)
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
        validated_data["phone_opt_in"] = phone_opt_in
        validated_data["phone_available"] = phone_available
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "delay" in validated_data:
            secs = validated_data.pop("delay")
            validated_data["delay"] = timedelta(seconds=secs)
        biz_info = validated_data.pop("business", None)
        phone_opt_in = validated_data.pop("phone_opt_in", None)
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
        if phone_opt_in is not None:
            instance.phone_opt_in = phone_opt_in
        if phone_available is not None:
            instance.phone_available = phone_available
        return super().update(instance, validated_data)




class ProcessedLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessedLead
        fields = ["lead_id", "business_id", "processed_at"]
        read_only_fields = ["lead_id", "business_id", "processed_at"]


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



