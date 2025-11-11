from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import LeadDetail, NotificationSetting, YelpBusiness, LeadEvent, WhatsAppNotificationSetting
from .twilio_utils import send_sms, send_whatsapp_with_content_template
from .twilio_content_api import build_content_variables
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
    
    # Step 7: Send WhatsApp notifications
    logger.info(f"[WHATSAPP-NOTIFICATION] 📱 Starting WhatsApp notifications for {scenario}")
    
    whatsapp_settings = WhatsAppNotificationSetting.objects.filter(
        business=business
    ).exclude(phone_number="")
    
    if not whatsapp_settings.exists():
        logger.warning(f"[WHATSAPP-NOTIFICATION] ⚠️ No WhatsApp settings found for business")
    else:
        logger.info(f"[WHATSAPP-NOTIFICATION] Found {whatsapp_settings.count()} WhatsApp settings")
        
        # Prepare data for WhatsApp
        yelp_link = f"https://biz.yelp.com/inbox/{instance.conversation_id}"
        
        for setting in whatsapp_settings:
            logger.info(f"[WHATSAPP-NOTIFICATION] 📤 Sending WhatsApp to {setting.phone_number}")
            
            try:
                if setting.use_content_template and setting.content_sid:
                    # Use Content Template
                    logger.info(f"[WHATSAPP-NOTIFICATION] Using Content Template: {setting.content_sid}")
                    
                    # Build content variables from mapping
                    # Updated data structure to match Twilio WhatsApp Content Template format
                    # Example: "Your business (ID: {{1}}) has registered a new lead (Lead ID: {{3}}) for reason: "{{2}}". Phone: {{4}}."
                    data = {
                        'business_id': instance.business_id,      # {{1}} - Business ID
                        'reason': reason,                          # {{2}} - Reason for notification
                        'lead_id': instance.lead_id,              # {{3}} - Lead ID
                        'phone': instance.phone_number or '',     # {{4}} - Customer phone number
                        'business_name': business.name,            # {{5}} - Business name
                        'customer_name': getattr(instance, 'user_display_name', '') or 'Customer',  # {{6}} - Customer display name
                        'yelp_link': yelp_link,                   # {{7}} - Yelp conversation link
                        'timestamp': timezone.now().isoformat(),   # {{8}} - Current date and time
                    }
                    
                    content_vars = build_content_variables(setting.variable_mapping, data)
                    logger.info(f"[WHATSAPP-NOTIFICATION] Content variables: {content_vars}")
                    
                    sid = send_whatsapp_with_content_template(
                        to=setting.phone_number,
                        content_sid=setting.content_sid,
                        content_variables=content_vars,
                        lead_id=instance.lead_id,
                        business_id=instance.business_id,
                        purpose="notification"
                    )
                    
                else:
                    # Use simple template
                    logger.info(f"[WHATSAPP-NOTIFICATION] Using simple template")
                    
                    message = setting.message_template.format(
                        business_id=instance.business_id,
                        lead_id=instance.lead_id,
                        business_name=business.name,
                        customer_name=getattr(instance, 'user_display_name', '') or 'Customer',
                        timestamp=timezone.now().isoformat(),
                        phone=instance.phone_number or '',
                        yelp_link=yelp_link,
                        reason=reason,
                    )
                    
                    logger.info(f"[WHATSAPP-NOTIFICATION] Message: {message[:100]}...")
                    
                    from .twilio_utils import send_whatsapp
                    sid = send_whatsapp(
                        to=setting.phone_number,
                        body=message,
                        lead_id=instance.lead_id,
                        business_id=instance.business_id,
                        purpose="notification"
                    )
                
                logger.info(f"[WHATSAPP-NOTIFICATION] ✅ WhatsApp sent successfully! SID: {sid}")
                
            except Exception as e:
                logger.error(f"[WHATSAPP-NOTIFICATION] ❌ WhatsApp sending failed: {e}")
                logger.exception(f"[WHATSAPP-NOTIFICATION] WhatsApp sending exception details")
    
    logger.info(f"[SMS-NOTIFICATION] 🎉 SMS notification completed for scenario: {scenario}")
