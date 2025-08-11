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
    logger.info(f"[SMS-NOTIFICATION] 📱 SIGNAL TRIGGERED: notify_new_lead")
    logger.info(f"[SMS-NOTIFICATION] Signal parameters:")
    logger.info(f"[SMS-NOTIFICATION] - Sender: {sender}")
    logger.info(f"[SMS-NOTIFICATION] - Instance: LeadDetail(id={instance.id})")
    logger.info(f"[SMS-NOTIFICATION] - Lead ID: {instance.lead_id}")
    logger.info(f"[SMS-NOTIFICATION] - Business ID: {instance.business_id}")
    logger.info(f"[SMS-NOTIFICATION] - Created: {created}")
    logger.info(f"[SMS-NOTIFICATION] - Phone number: {'***PROVIDED***' if instance.phone_number else 'NOT PROVIDED'}")
    
    # Step 1: Check if this should trigger SMS
    logger.info(f"[SMS-NOTIFICATION] 🔍 STEP 1: Determining if SMS should be sent")
    
    should_send_sms = False
    sms_trigger_reason = ""
    
    if not created and (instance.phone_number or getattr(instance, 'phone_in_text', False) or getattr(instance, 'phone_in_additional_info', False)):
        # Record updated and now has phone number OR phone detected in text/additional_info
        # Check if we already sent Phone Number Found SMS
        phone_sms_sent = getattr(instance, 'phone_sms_sent', False)
        
        if not phone_sms_sent:
            should_send_sms = True
            phone_sources = []
            if instance.phone_number:
                phone_sources.append("phone_number set")
            if getattr(instance, 'phone_in_text', False):
                phone_sources.append("phone_in_text=True")
            if getattr(instance, 'phone_in_additional_info', False):
                phone_sources.append("phone_in_additional_info=True")
            
            sms_trigger_reason = f"Phone Number Found: {', '.join(phone_sources)}"
            logger.info(f"[SMS-NOTIFICATION] ✅ PHONE NUMBER FOUND (FIRST TIME) - triggering SMS notification")
            logger.info(f"[SMS-NOTIFICATION] Phone sources detected: {phone_sources}")
            logger.info(f"[SMS-NOTIFICATION] This handles the 'Phone Number Found' scenario (first time only)")
            
        else:
            should_send_sms = False
            sms_trigger_reason = "Phone Number Found (SMS already sent)"
            logger.info(f"[SMS-NOTIFICATION] 🚫 PHONE NUMBER FOUND SMS SKIPPED - already sent before")
            logger.info(f"[SMS-NOTIFICATION] phone_sms_sent={phone_sms_sent} - preventing duplicate Phone Number Found SMS")
            logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - Phone Number Found SMS already sent")
            return
    else:
        # Record updated but no phone - this could be Customer Reply scenario
        has_phone_flags = (getattr(instance, 'phone_in_text', False) or 
                          getattr(instance, 'phone_in_additional_info', False) or 
                          getattr(instance, 'phone_opt_in', False))
        
        if not created and not instance.phone_number and not has_phone_flags:
            # This is a Customer Reply scenario - customer responded without providing phone
            # Ensure that an actual consumer event exists to avoid false positives from
            # the immediate save after lead creation
            has_consumer_event = LeadEvent.objects.filter(
                lead_id=instance.lead_id, user_type="CONSUMER"
            ).exists()
            if not has_consumer_event:
                should_send_sms = False
                sms_trigger_reason = "Customer Reply (no consumer events)"
                logger.info(
                    f"[SMS-NOTIFICATION] 🚫 CUSTOMER REPLY SKIPPED - no CONSUMER events recorded"
                )
                logger.info(
                    f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - awaiting real customer reply"
                )
                return

            # Check if customer has already replied before
            has_already_replied = getattr(instance, 'customer_replied', False)

            if not has_already_replied:
                should_send_sms = True
                sms_trigger_reason = "Customer Reply (first time)"
                logger.info(f"[SMS-NOTIFICATION] ✅ CUSTOMER REPLY (FIRST TIME) - triggering SMS notification")
                logger.info(f"[SMS-NOTIFICATION] This handles the '💬 Customer Reply' scenario (first reply only)")
                logger.info(f"[SMS-NOTIFICATION] Customer responded for the first time without phone number")

                # Mark that customer has replied to prevent future Customer Reply SMS
                instance.customer_replied = True
                instance.save(update_fields=['customer_replied'])
                logger.info(f"[SMS-NOTIFICATION] 🏃 Marked customer_replied=True to prevent repeated SMS")
            else:
                should_send_sms = False
                sms_trigger_reason = "Customer Reply (already replied before)"
                logger.info(f"[SMS-NOTIFICATION] 🚫 CUSTOMER REPLY SKIPPED - customer has already replied before")
                logger.info(f"[SMS-NOTIFICATION] customer_replied={has_already_replied} - preventing repeated Customer Reply SMS")
                logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - Customer Reply SMS already sent")
                return
        else:
            # Record updated but conditions not met for any SMS scenario OR new record created
            should_send_sms = False
            if created:
                sms_trigger_reason = "New lead created - SMS disabled for new leads without phone"
                logger.info(f"[SMS-NOTIFICATION] 🚫 NEW LEAD - SMS disabled for new leads without phone numbers")
                logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - new lead SMS notifications are disabled")
            else:
                sms_trigger_reason = "Updated record - no SMS trigger conditions met"
                logger.info(f"[SMS-NOTIFICATION] ⚠️ UPDATED RECORD - no SMS trigger conditions met")
                logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - no valid SMS scenario detected")
            return
    
    logger.info(f"[SMS-NOTIFICATION] 📋 SMS TRIGGER ANALYSIS:")
    logger.info(f"[SMS-NOTIFICATION] - Should send SMS: {should_send_sms}")
    logger.info(f"[SMS-NOTIFICATION] - Reason: {sms_trigger_reason}")
    logger.info(f"[SMS-NOTIFICATION] - Created: {created}")
    logger.info(f"[SMS-NOTIFICATION] - Has phone: {bool(instance.phone_number)}")
    logger.info(f"[SMS-NOTIFICATION] ✅ PROCEEDING with notification check")
    
    # Step 2: Check if phone number is available
    logger.info(f"[SMS-NOTIFICATION] 📞 STEP 1: Checking phone number availability")
    logger.info(f"[SMS-NOTIFICATION] ========== PHONE NUMBER CHECK ==========")
    logger.info(f"[SMS-NOTIFICATION] LeadDetail fields:")
    logger.info(f"[SMS-NOTIFICATION] - phone_number: '{instance.phone_number}'")
    logger.info(f"[SMS-NOTIFICATION] - phone_in_text: {getattr(instance, 'phone_in_text', 'Not set')}")
    logger.info(f"[SMS-NOTIFICATION] - phone_in_additional_info: {getattr(instance, 'phone_in_additional_info', 'Not set')}")
    logger.info(f"[SMS-NOTIFICATION] - phone_opt_in: {getattr(instance, 'phone_opt_in', 'Not set')}")
    logger.info(f"[SMS-NOTIFICATION] - user_display_name: '{getattr(instance, 'user_display_name', 'Not set')}'")
    
    # 📊 Determine which SMS scenario this is
    scenario = "Unknown"
    if getattr(instance, 'phone_opt_in', False):
        scenario = "✅ Phone Opt-in"
    elif getattr(instance, 'phone_in_text', False) or getattr(instance, 'phone_in_additional_info', False):
        scenario = "📞 Phone Number Found"
    elif not instance.phone_number:
        scenario = "💬 Customer Reply"
    
    logger.info(f"[SMS-NOTIFICATION] 🎯 Detected SMS scenario: {scenario}")
    
    # For Customer Reply scenario, we don't need phone_number (SMS will be sent to business, not customer)
    is_customer_reply = scenario == "💬 Customer Reply"
    
    if not instance.phone_number and not is_customer_reply:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ NO PHONE NUMBER - cannot send SMS notifications")
        logger.info(f"[SMS-NOTIFICATION] Phone number field value: '{instance.phone_number}'")
        logger.info(f"[SMS-NOTIFICATION] ❗ CRITICAL: NotificationSetting SMS requires phone_number to be set")
        logger.info(f"[SMS-NOTIFICATION] 💡 Exception: Customer Reply SMS can work without customer phone")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - SMS requires phone number (except Customer Reply)")
        return
    elif is_customer_reply and not instance.phone_number:
        logger.info(f"[SMS-NOTIFICATION] ℹ️ Customer Reply scenario - SMS will be sent to business notification numbers")
        logger.info(f"[SMS-NOTIFICATION] Customer phone not required for this scenario")
        
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
        logger.info(f"[SMS-NOTIFICATION] - SMS notifications enabled: {business.sms_notifications_enabled}")
    else:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ Business not found for business_id: {instance.business_id}")
        logger.info(f"[SMS-NOTIFICATION] Will look for global notification settings only")

    # Step 3.5: Check if SMS notifications are enabled for this business
    logger.info(f"[SMS-NOTIFICATION] 🔔 STEP 2.5: Checking SMS notifications status")
    if business and not business.sms_notifications_enabled:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ SMS NOTIFICATIONS DISABLED for business: {business.business_id}")
        logger.info(f"[SMS-NOTIFICATION] Business admin has turned off SMS notifications")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - SMS notifications disabled for this business")
        return
    elif business and business.sms_notifications_enabled:
        logger.info(f"[SMS-NOTIFICATION] ✅ SMS NOTIFICATIONS ENABLED for business: {business.business_id}")
    else:
        logger.info(f"[SMS-NOTIFICATION] ✅ No business context - proceeding with global settings check")

    # Step 4: Look up business-specific notification settings only
    logger.info(f"[SMS-NOTIFICATION] ⚙️ STEP 3: Looking up notification settings")
    logger.info(f"[SMS-NOTIFICATION] ========== NOTIFICATION SETTINGS LOOKUP ==========")
    
    # Debug: Show all NotificationSetting in database
    all_notification_settings = NotificationSetting.objects.all()
    logger.info(f"[SMS-NOTIFICATION] 📊 ALL NotificationSettings in database:")
    if all_notification_settings.exists():
        for setting in all_notification_settings:
            logger.info(f"[SMS-NOTIFICATION] - ID={setting.id}, business={setting.business}, phone={setting.phone_number}, template_length={len(setting.message_template)}")
    else:
        logger.info(f"[SMS-NOTIFICATION] ❌ NO NotificationSettings found in database!")
    
    logger.info(f"[SMS-NOTIFICATION] Filtering criteria:")
    logger.info(f"[SMS-NOTIFICATION] - Exclude empty phone numbers")
    logger.info(f"[SMS-NOTIFICATION] - Exclude empty message templates")
    logger.info(f"[SMS-NOTIFICATION] - Only business-specific settings (no global settings)")
    logger.info(f"[SMS-NOTIFICATION] - SMS notifications require valid business")
    
    settings = NotificationSetting.objects.exclude(phone_number="").exclude(message_template="")
    initial_count = settings.count()
    logger.info(f"[SMS-NOTIFICATION] Initial settings count (with phone & template): {initial_count}")
    
    if business:
        logger.info(f"[SMS-NOTIFICATION] Applying business-only filter (no global settings)")
        logger.info(f"[SMS-NOTIFICATION] Looking for business: {business.business_id} (ID: {business.id})")
        
        # Only get business-specific settings
        business_settings = settings.filter(business=business)
        business_count = business_settings.count()
        logger.info(f"[SMS-NOTIFICATION] Business-specific settings: {business_count}")
        
        if business_count > 0:
            logger.info(f"[SMS-NOTIFICATION] ✅ Found {business_count} NotificationSettings for business {business.business_id}")
            for setting in business_settings:
                logger.info(f"[SMS-NOTIFICATION] - Setting ID={setting.id}, phone={setting.phone_number}")
        else:
            logger.error(f"[SMS-NOTIFICATION] ❌ NO NotificationSettings found for business {business.business_id}")
            logger.error(f"[SMS-NOTIFICATION] This means no SMS will be sent!")
        
        settings = list(business_settings)
        logger.info(f"[SMS-NOTIFICATION] Using only business-specific SMS settings")
        
        # LIMIT TO FIRST SETTING ONLY to prevent duplicate SMS
        if len(settings) > 1:
            logger.info(f"[SMS-NOTIFICATION] ⚠️ Multiple NotificationSettings found ({len(settings)}), using only the first one")
            logger.info(f"[SMS-NOTIFICATION] This prevents duplicate SMS notifications")
            logger.info(f"[SMS-NOTIFICATION] Available settings:")
            for i, s in enumerate(settings, 1):
                logger.info(f"[SMS-NOTIFICATION] - Setting #{i}: ID={s.id}, phone={s.phone_number}")
            settings = settings[:1]  # Take only the first setting
            logger.info(f"[SMS-NOTIFICATION] Selected setting: ID={settings[0].id}, phone={settings[0].phone_number}")
    else:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ NO BUSINESS found - SMS notifications disabled")
        logger.info(f"[SMS-NOTIFICATION] Global SMS settings are not supported")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - SMS only for specific businesses")
        return
        
    final_count = len(settings)
    logger.info(f"[SMS-NOTIFICATION] Final business-specific settings count: {final_count}")
    logger.info(f"[SMS-NOTIFICATION] ==============================================")
    
    if final_count == 0:
        logger.info(f"[SMS-NOTIFICATION] ⚠️ NO NOTIFICATION SETTINGS found")
        logger.info(f"[SMS-NOTIFICATION] Criteria checked:")
        logger.info(f"[SMS-NOTIFICATION] - Has phone number: ✓")
        logger.info(f"[SMS-NOTIFICATION] - Has message template: ✓")
        logger.info(f"[SMS-NOTIFICATION] - Business match: {business is not None}")
        logger.info(f"[SMS-NOTIFICATION] 🛑 EARLY RETURN - no settings to process")
        return
        
    logger.info(f"[SMS-NOTIFICATION] ✅ Found {final_count} unique notification setting(s) to process")
    
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
            # Generate Yelp Business Lead Center link
            yelp_link = f"https://biz.yelp.com/leads_center/{instance.business_id}/leads/{instance.lead_id}"
            logger.info(f"[SMS-NOTIFICATION] 🔗 Generated Yelp link: {yelp_link}")
            
            # Determine reason for contact based on lead context
            logger.info(f"[SMS-NOTIFICATION] 🎯 REASON DETERMINATION:")
            logger.info(f"[SMS-NOTIFICATION] - phone_opt_in: {getattr(instance, 'phone_opt_in', False)}")
            logger.info(f"[SMS-NOTIFICATION] - phone_number: '{instance.phone_number}'")
            logger.info(f"[SMS-NOTIFICATION] - created: {created}")
            logger.info(f"[SMS-NOTIFICATION] - sms_trigger_reason: {sms_trigger_reason}")
            
            if getattr(instance, 'phone_opt_in', False):
                reason = "Phone Opt-in"
            elif instance.phone_number:
                reason = "Phone Number Found"
            elif not created:
                reason = "Customer Reply"
            else:
                # This shouldn't happen since we return early for new leads without phone
                reason = "New Lead (unexpected)"
                
            logger.info(f"[SMS-NOTIFICATION] - Final SMS reason: {reason}")
            
            # Get time-based greeting
            greetings = get_time_based_greeting(business_id=instance.business_id)
            logger.info(f"[SMS-NOTIFICATION] 🕐 Time-based greeting: {greetings}")
            
            # 🔍 DETAILED PHONE NUMBER DEBUG AND RESOLUTION
            logger.info(f"[SMS-NOTIFICATION] 🔍 PHONE NUMBER DEBUG:")
            logger.info(f"[SMS-NOTIFICATION] - instance.phone_number VALUE: '{instance.phone_number}'")
            logger.info(f"[SMS-NOTIFICATION] - instance.phone_number TYPE: {type(instance.phone_number)}")
            logger.info(f"[SMS-NOTIFICATION] - instance.phone_number BOOL: {bool(instance.phone_number)}")
            logger.info(f"[SMS-NOTIFICATION] - phone_in_text: {getattr(instance, 'phone_in_text', False)}")
            logger.info(f"[SMS-NOTIFICATION] - phone_in_additional_info: {getattr(instance, 'phone_in_additional_info', False)}")
            logger.info(f"[SMS-NOTIFICATION] - SMS trigger scenario: {sms_trigger_reason}")
            
            # SMART PHONE RESOLUTION: Get actual phone number for SMS
            actual_phone = instance.phone_number or ""
            if not actual_phone and getattr(instance, 'phone_in_text', False):
                # Try to get phone from recent LeadEvent if phone_in_text=True but phone_number is empty
                recent_events = LeadEvent.objects.filter(
                    lead_id=instance.lead_id,
                    from_backend=False
                ).order_by('-event_time')[:5]  # Check last 5 events
                
                logger.info(f"[SMS-NOTIFICATION] 🔍 SEARCHING for phone in recent events (phone_in_text=True but phone_number empty)")
                for event in recent_events:
                    if event.text:
                        from .webhook_views import WebhookView
                        phone_in_event = WebhookView()._extract_phone(event.text)
                        if phone_in_event:
                            actual_phone = phone_in_event
                            logger.info(f"[SMS-NOTIFICATION] ✅ FOUND phone in event {event.id}: '{phone_in_event}'")
                            break
                        else:
                            logger.info(f"[SMS-NOTIFICATION] - Event {event.id}: no phone found in '{event.text[:50]}...'")
            
            logger.info(f"[SMS-NOTIFICATION] - Final phone for SMS: '{actual_phone}'")
            logger.info(f"[SMS-NOTIFICATION] - This SMS will have reason: {reason}")
            
            message = setting.message_template.format(
                business_id=instance.business_id,
                lead_id=instance.lead_id,
                business_name=business.name if business else "",
                customer_name=getattr(instance, 'user_display_name', '') or 'Customer',
                timestamp=timezone.now().isoformat(),
                phone=actual_phone,  # Use resolved phone number
                yelp_link=yelp_link,
                reason=reason,
                greetings=greetings,
            )
            logger.info(f"[SMS-NOTIFICATION] ✅ Message formatted successfully")
            logger.info(f"[SMS-NOTIFICATION] Formatted message: {message[:100]}..." + ("" if len(message) <= 100 else " (truncated)"))
            logger.info(f"[SMS-NOTIFICATION] Message length: {len(message)} characters")
            
        except Exception as format_exc:
            logger.error(f"[SMS-NOTIFICATION] ❌ MESSAGE FORMATTING ERROR: {format_exc}")
            logger.error(f"[SMS-NOTIFICATION] Template: {setting.message_template}")
            yelp_link_debug = f"https://biz.yelp.com/leads_center/{instance.business_id}/leads/{instance.lead_id}"
            logger.error(f"[SMS-NOTIFICATION] Variables: business_id={instance.business_id}, lead_id={instance.lead_id}, business_name={business.name if business else ''}, phone={instance.phone_number}, yelp_link={yelp_link_debug}")
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
            sid = send_sms(
                setting.phone_number, 
                message, 
                lead_id=instance.lead_id, 
                business_id=instance.business_id, 
                purpose="notification"
            )
            if 'Phone Number Found' in sms_trigger_reason and not getattr(instance, 'phone_sms_sent', False):
                instance.phone_sms_sent = True
                instance.save(update_fields=['phone_sms_sent'])
                logger.info(
                    f"[SMS-NOTIFICATION] 🏁 Marked phone_sms_sent=True for lead {instance.lead_id} after notification SMS"
                )
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

