from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging
import requests

from .models import LeadDetail, NotificationSetting, YelpBusiness

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LeadDetail)
def notify_new_lead(sender, instance: LeadDetail, created: bool, **kwargs):
    if not created:
        return
    if not instance.phone_number:
        return

    setting = NotificationSetting.objects.first()
    if not setting or not setting.phone_number or not setting.message_template:
        return

    business = YelpBusiness.objects.filter(business_id=instance.business_id).first()
    message = setting.message_template.format(
        business_id=instance.business_id,
        lead_id=instance.lead_id,
        business_name=business.name if business else "",
        timestamp=timezone.now().isoformat(),
    )

    payload = {"to": setting.phone_number, "body": message}
    try:
        requests.post("http://46.62.139.177:8000/api/send-sms/", json=payload, timeout=10)
    except Exception:
        logger.exception("Failed to send notification SMS")

