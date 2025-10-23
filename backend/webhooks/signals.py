from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import LeadDetail, NotificationSetting, YelpBusiness, LeadEvent
from .twilio_utils import send_sms
from .utils import get_time_based_greeting

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LeadDetail)
def notify_new_lead(sender, instance: LeadDetail, created: bool, **kwargs):
    """
    📱 Twilio SMS Notification Center
    Sends SMS notifications for 2 scenarios:
    1. 📞 Phone Number Found (phone_in_text or phone_in_additional_info)
    2. ✅ Phone Opt-in (phone_opt_in=True)
    
    Note: 💬 Customer Reply is handled by webhook_views.py, not here
    """
    logger.info(f"[SMS-NOTIFICATION] 📱 SIGNAL TRIGGERED: notify_new_lead")
    logger.info(f"[SMS-NOTIFICATION] - Lead ID: {instance.lead_id}")
    logger.info(f"[SMS-NOTIFICATION] - Business ID: {instance.business_id}")
    logger.info(f"[SMS-NOTIFICATION] - Created: {created}")
    
    # Step 1: Determine SMS scenario
    scenario = "Unknown"
    reason = ""
    
    if getattr(instance, 'phone_opt_in', False):
        scenario = "✅ Phone Opt-in"
        reason = "Phone Opt-In"
    elif getattr(instance, 'phone_in_text', False) or getattr(instance, 'phone_in_additional_info', False):
        scenario = "📞 Phone Number Found"
        phone_sources = []
        if getattr(instance, 'phone_in_text', False):
            phone_sources.append("phone_in_text")
        if getattr(instance, 'phone_in_additional_info', False):
            phone_sources.append("phone_in_additional_info")
        reason = f"Phone Number Found: {', '.join(phone_sources)}"
    
    logger.info(f"[SMS-NOTIFICATION] 🎯 Detected scenario: {scenario}")
    logger.info(f"[SMS-NOTIFICATION] - Reason: {reason}")
    
    # Step 2: Check if should send SMS
    should_send_sms = False
    
    if created:
        # New lead created - NO SMS
        logger.info(f"[SMS-NOTIFICATION] 🚫 NEW LEAD - SMS disabled for new leads")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
        return
    
    # Customer Reply is handled by webhook_views.py, not here
    
    if scenario == "📞 Phone Number Found":
        # Phone Number Found - check if already sent
        phone_sms_sent = getattr(instance, 'phone_sms_sent', False)
        if phone_sms_sent:
            logger.info(f"[SMS-NOTIFICATION] 🚫 Phone Number Found SMS already sent")
            logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
            return
        should_send_sms = True
    
    if scenario == "✅ Phone Opt-in":
        # Phone Opt-in - always send (first time)
        should_send_sms = True
    
    if scenario == "Unknown":
        # No recognized scenario - no SMS needed
        logger.info(f"[SMS-NOTIFICATION] 🚫 Unknown scenario - no SMS needed")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
        return
    
    if not should_send_sms:
        logger.info(f"[SMS-NOTIFICATION] 🚫 SMS not needed for this scenario")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
        return
    
    logger.info(f"[SMS-NOTIFICATION] ✅ SMS should be sent for scenario: {scenario}")
    
    # Step 3: Check business SMS settings
    business = YelpBusiness.objects.filter(business_id=instance.business_id).first()
    
    if not business:
        logger.warning(f"[SMS-NOTIFICATION] ⚠️ Business not found: {instance.business_id}")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
        return
    
    logger.info(f"[SMS-NOTIFICATION] Business: {business.name}")
    logger.info(f"[SMS-NOTIFICATION] - SMS notifications enabled: {business.sms_notifications_enabled}")
    
    if not business.sms_notifications_enabled:
        logger.info(f"[SMS-NOTIFICATION] 🚫 SMS NOTIFICATIONS DISABLED for business")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
        return
    
    # Step 4: Get NotificationSettings
    notification_settings = NotificationSetting.objects.filter(
        business=business
    ).exclude(phone_number="")
    
    if not notification_settings.exists():
        logger.warning(f"[SMS-NOTIFICATION] ⚠️ No NotificationSettings found for business")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN")
        return
    
    logger.info(f"[SMS-NOTIFICATION] Found {notification_settings.count()} notification settings")
    
    # Step 5: Prepare SMS message
    yelp_link = f"https://biz.yelp.com/inbox/{instance.conversation_id}"
    greetings = get_time_based_greeting(business.time_zone)
    
    # Step 6: Send SMS to each notification number
    for setting in notification_settings:
        logger.info(f"[SMS-NOTIFICATION] 📤 Sending SMS to {setting.phone_number}")
        
        try:
            message = setting.message_template.format(
                business_id=instance.business_id,
                lead_id=instance.lead_id,
                business_name=business.name,
                customer_name=getattr(instance, 'user_display_name', '') or 'Customer',
                timestamp=timezone.now().isoformat(),
                phone=instance.phone_number or '',
                yelp_link=yelp_link,
                reason=reason,
                greetings=greetings,
            )
            
            logger.info(f"[SMS-NOTIFICATION] Message: {message[:100]}...")
            
            sid = send_sms(
                setting.phone_number,
                message,
                lead_id=instance.lead_id,
                business_id=instance.business_id,
                purpose="notification"
            )
            
            # Mark SMS as sent for Phone Number Found scenario
            if scenario == "📞 Phone Number Found" and not getattr(instance, 'phone_sms_sent', False):
                instance.phone_sms_sent = True
                instance.save(update_fields=['phone_sms_sent'])
                logger.info(f"[SMS-NOTIFICATION] 🏁 Marked phone_sms_sent=True")
            
            logger.info(f"[SMS-NOTIFICATION] ✅ SMS sent successfully!")
            logger.info(f"[SMS-NOTIFICATION] - SID: {sid}")
            logger.info(f"[SMS-NOTIFICATION] - Scenario: {scenario}")
            
        except Exception as sms_error:
            logger.error(f"[SMS-NOTIFICATION] ❌ SMS sending failed: {sms_error}")
            logger.exception(f"[SMS-NOTIFICATION] SMS sending exception")
    
    logger.info(f"[SMS-NOTIFICATION] 🎉 SMS notification completed for scenario: {scenario}")
