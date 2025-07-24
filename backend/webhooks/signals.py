from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import LeadDetail, NotificationSetting, YelpBusiness
from .twilio_utils import send_sms

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LeadDetail)
def notify_new_lead(sender, instance: LeadDetail, created: bool, **kwargs):
    logger.info(f"[SMS-NOTIFICATION] 📱 SIGNAL TRIGGERED: notify_new_lead")
    logger.info(f"[SMS-NOTIFICATION] Signal parameters:")
    logger.info(f"[SMS-NOTIFICATION] - Sender: {sender}")
    logger.info(f"[SMS-NOTIFICATION] - Instance: LeadDetail(id={instance.id})")
    logger.info(f"[SMS-NOTIFICATION] - Lead ID: {instance.lead_id}")
    logger.info(f"[SMS-NOTIFICATION] - Business ID: {instance.business_id}")
    logger.info(f"[SMS-NOTIFICATION] - Created: {created}")
    logger.info(f"[SMS-NOTIFICATION] - Phone number: {'***PROVIDED***' if instance.phone_number else 'NOT PROVIDED'}")
    
    # Step 1: Check if this is a new record creation
    if not created:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ NOT A NEW RECORD - LeadDetail was updated, not created")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - SMS notifications only for new records")
        return
        
    logger.info(f"[SMS-NOTIFICATION] ✅ NEW RECORD confirmed - proceeding with notification check")
    
    # Step 2: Check if phone number is available
    logger.info(f"[SMS-NOTIFICATION] 📞 STEP 1: Checking phone number availability")
    if not instance.phone_number:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ NO PHONE NUMBER - cannot send SMS notifications")
        logger.info(f"[SMS-NOTIFICATION] Phone number field value: '{instance.phone_number}'")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - SMS requires phone number")
        return
        
    logger.info(f"[SMS-NOTIFICATION] ✅ Phone number available - can proceed with notifications")
    logger.debug(f"[SMS-NOTIFICATION] Phone number: {instance.phone_number}")

    # Step 3: Look up business information
    logger.info(f"[SMS-NOTIFICATION] 🏢 STEP 2: Looking up business information")
    business = YelpBusiness.objects.filter(business_id=instance.business_id).first()
    logger.info(f"[SMS-NOTIFICATION] Business lookup result: {business is not None}")
    
    if business:
        logger.info(f"[SMS-NOTIFICATION] Business details:")
        logger.info(f"[SMS-NOTIFICATION] - Business ID: {business.business_id}")
        logger.info(f"[SMS-NOTIFICATION] - Business name: {business.name}")
        logger.info(f"[SMS-NOTIFICATION] - Time zone: {business.time_zone}")
    else:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ Business not found for business_id: {instance.business_id}")
        logger.info(f"[SMS-NOTIFICATION] Will look for global notification settings only")

    # Step 4: Look up notification settings
    logger.info(f"[SMS-NOTIFICATION] ⚙️ STEP 3: Looking up notification settings")
    logger.info(f"[SMS-NOTIFICATION] Filtering criteria:")
    logger.info(f"[SMS-NOTIFICATION] - Exclude empty phone numbers")
    logger.info(f"[SMS-NOTIFICATION] - Exclude empty message templates")
    
    settings = NotificationSetting.objects.exclude(phone_number="").exclude(message_template="")
    initial_count = settings.count()
    logger.info(f"[SMS-NOTIFICATION] Initial settings count (with phone & template): {initial_count}")
    
    if business:
        logger.info(f"[SMS-NOTIFICATION] Applying business filter (business-specific OR global)")
        settings = settings.filter(models.Q(business=business) | models.Q(business__isnull=True))
    else:
        logger.info(f"[SMS-NOTIFICATION] Applying global-only filter (no business)")
        settings = settings.filter(business__isnull=True)
        
    final_count = settings.count()
    logger.info(f"[SMS-NOTIFICATION] Final settings count after business filter: {final_count}")
    
    if not settings.exists():
        logger.info(f"[SMS-NOTIFICATION] ⚠️ NO NOTIFICATION SETTINGS found")
        logger.info(f"[SMS-NOTIFICATION] Criteria checked:")
        logger.info(f"[SMS-NOTIFICATION] - Has phone number: ✓")
        logger.info(f"[SMS-NOTIFICATION] - Has message template: ✓")
        logger.info(f"[SMS-NOTIFICATION] - Business match: {business is not None}")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - no settings to process")
        return
        
    logger.info(f"[SMS-NOTIFICATION] ✅ Found {final_count} notification setting(s) to process")
    
    # Log details about each setting
    for i, setting in enumerate(settings):
        logger.info(f"[SMS-NOTIFICATION] Setting {i+1}:")
        logger.info(f"[SMS-NOTIFICATION] - ID: {setting.id}")
        logger.info(f"[SMS-NOTIFICATION] - Phone: {setting.phone_number}")
        logger.info(f"[SMS-NOTIFICATION] - Business: {setting.business.name if setting.business else 'Global'}")
        logger.info(f"[SMS-NOTIFICATION] - Template: {setting.message_template[:50]}...")

    # Step 5: Process each notification setting
    logger.info(f"[SMS-NOTIFICATION] 📨 STEP 4: Processing notification settings")
    sent_count = 0
    error_count = 0
    
    for i, setting in enumerate(settings):
        logger.info(f"[SMS-NOTIFICATION] 📤 Processing setting {i+1}/{final_count}")
        logger.info(f"[SMS-NOTIFICATION] Setting details:")
        logger.info(f"[SMS-NOTIFICATION] - ID: {setting.id}")
        logger.info(f"[SMS-NOTIFICATION] - Target phone: {setting.phone_number}")
        logger.info(f"[SMS-NOTIFICATION] - Business context: {setting.business.name if setting.business else 'Global'}")
        
        # Format the message
        logger.info(f"[SMS-NOTIFICATION] 📝 Formatting message template")
        try:
            message = setting.message_template.format(
                business_id=instance.business_id,
                lead_id=instance.lead_id,
                business_name=business.name if business else "",
                timestamp=timezone.now().isoformat(),
                phone=instance.phone_number,
            )
            logger.info(f"[SMS-NOTIFICATION] ✅ Message formatted successfully")
            logger.info(f"[SMS-NOTIFICATION] Formatted message: {message[:100]}..." + ("" if len(message) <= 100 else " (truncated)"))
            logger.info(f"[SMS-NOTIFICATION] Message length: {len(message)} characters")
            
        except Exception as format_exc:
            logger.error(f"[SMS-NOTIFICATION] ❌ MESSAGE FORMATTING ERROR: {format_exc}")
            logger.error(f"[SMS-NOTIFICATION] Template: {setting.message_template}")
            logger.error(f"[SMS-NOTIFICATION] Variables: business_id={instance.business_id}, lead_id={instance.lead_id}, business_name={business.name if business else ''}, phone={instance.phone_number}")
            logger.exception(f"[SMS-NOTIFICATION] Message formatting exception")
            error_count += 1
            continue

        logger.info(
            f"[SMS-NOTIFICATION] 📤 Sending SMS notification",
            extra={
                "to": setting.phone_number,
                "lead_id": instance.lead_id,
                "business_id": instance.business_id,
                "body": message,
                "setting_id": setting.id,
            },
        )
        
        # Send the SMS
        try:
            logger.info(f"[SMS-NOTIFICATION] 🚀 Calling send_sms function")
            sid = send_sms(setting.phone_number, message)
            logger.info(f"[SMS-NOTIFICATION] ✅ SMS sent successfully!")
            logger.info(
                f"[SMS-NOTIFICATION] SMS delivery details",
                extra={
                    "to": setting.phone_number,
                    "lead_id": instance.lead_id,
                    "business_id": instance.business_id,
                    "sid": sid,
                    "setting_id": setting.id,
                },
            )
            sent_count += 1
            
        except Exception as sms_exc:
            logger.error(f"[SMS-NOTIFICATION] ❌ SMS SENDING ERROR: {sms_exc}")
            logger.exception(
                f"[SMS-NOTIFICATION] Failed to send notification SMS",
                extra={
                    "to": setting.phone_number,
                    "lead_id": instance.lead_id,
                    "business_id": instance.business_id,
                    "setting_id": setting.id,
                },
            )
            error_count += 1
            
    # Final summary
    logger.info(f"[SMS-NOTIFICATION] 📊 NOTIFICATION SUMMARY for lead {instance.lead_id}:")
    logger.info(f"[SMS-NOTIFICATION] - Total settings processed: {final_count}")
    logger.info(f"[SMS-NOTIFICATION] - SMS sent successfully: {sent_count}")
    logger.info(f"[SMS-NOTIFICATION] - Errors encountered: {error_count}")
    logger.info(f"[SMS-NOTIFICATION] - Success rate: {(sent_count/final_count*100) if final_count > 0 else 0:.1f}%")
    logger.info(f"[SMS-NOTIFICATION] 🎉 SIGNAL PROCESSING COMPLETED")

