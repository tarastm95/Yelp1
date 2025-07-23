from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import LeadDetail, NotificationSetting, YelpBusiness
from .twilio_utils import send_sms

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LeadDetail)
def notify_new_lead(sender, instance: LeadDetail, created: bool, **kwargs):
    if not created:
        return
    if not instance.phone_number:
        return

    settings = NotificationSetting.objects.exclude(phone_number="").exclude(message_template="")
    if not settings.exists():
        return

    business = YelpBusiness.objects.filter(business_id=instance.business_id).first()

    for setting in settings:
        message = setting.message_template.format(
            business_id=instance.business_id,
            lead_id=instance.lead_id,
            business_name=business.name if business else "",
            timestamp=timezone.now().isoformat(),
            phone=instance.phone_number,
        )

        logger.info(
            "Sending notification SMS",
            extra={
                "to": setting.phone_number,
                "lead_id": instance.lead_id,
                "business_id": instance.business_id,
                "body": message,
            },
        )
        try:
            sid = send_sms(setting.phone_number, message)
            logger.info(
                "Notification SMS sent",
                extra={
                    "to": setting.phone_number,
                    "lead_id": instance.lead_id,
                    "business_id": instance.business_id,
                    "sid": sid,
                },
            )
        except Exception:
            logger.exception(
                "Failed to send notification SMS",
                extra={
                    "to": setting.phone_number,
                    "lead_id": instance.lead_id,
                    "business_id": instance.business_id,
                },
            )

