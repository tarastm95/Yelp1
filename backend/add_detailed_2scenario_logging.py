#!/usr/bin/env python3
"""
Додає детальне логування для 2-сценарійної системи
"""

def add_detailed_logging():
    """
    Додає детальне логування для No Phone та Phone Available сценаріїв
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = []
    
    # 1. Покращуємо логування в handle_new_lead
    old_new_lead_log = '''            logger.info(f"[AUTO-RESPONSE] 🔄 SIMPLIFIED LOGIC: All new leads use No Phone scenario")
            logger.info(f"[AUTO-RESPONSE] Phone opt-in leads will also use No Phone templates and follow-ups")
            logger.info(f"[AUTO-RESPONSE] This creates unified experience for all leads without phone numbers")
            
            # Always use No Phone scenario for all new leads (including phone opt-in)
            logger.info(f"[AUTO-RESPONSE] 💬 SCENARIO: NO PHONE (includes phone opt-in leads)")
            logger.info(f"[AUTO-RESPONSE] Creating No Phone scenario tasks for lead")'''
    
    new_new_lead_log = '''            # Check if this is a phone opt-in lead for detailed logging
            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
            is_phone_optin = ld and ld.phone_opt_in
            
            logger.info(f"[AUTO-RESPONSE] 🔄 UNIFIED NO PHONE LOGIC")
            logger.info(f"[AUTO-RESPONSE] =================== NEW LEAD PROCESSING ===================")
            logger.info(f"[AUTO-RESPONSE] Lead type: {'📱 PHONE OPT-IN LEAD' if is_phone_optin else '💬 REGULAR LEAD'}")
            logger.info(f"[AUTO-RESPONSE] phone_opt_in flag: {is_phone_optin}")
            logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: NO PHONE / CUSTOMER REPLY (unified)")
            
            if is_phone_optin:
                logger.info(f"[AUTO-RESPONSE] 📱 PHONE OPT-IN LEAD PROCESSING:")
                logger.info(f"[AUTO-RESPONSE] - This lead agreed to provide phone number via Yelp")
                logger.info(f"[AUTO-RESPONSE] - Will use No Phone templates (unified logic)")
                logger.info(f"[AUTO-RESPONSE] - Frontend will show 'Phone Opt-In' badge for tracking")
                logger.info(f"[AUTO-RESPONSE] - Same follow-ups as regular no-phone leads")
            else:
                logger.info(f"[AUTO-RESPONSE] 💬 REGULAR NO PHONE LEAD PROCESSING:")
                logger.info(f"[AUTO-RESPONSE] - Standard lead without phone number")
                logger.info(f"[AUTO-RESPONSE] - Will use No Phone templates")
                logger.info(f"[AUTO-RESPONSE] - Standard follow-up sequence")
            
            logger.info(f"[AUTO-RESPONSE] Creating No Phone scenario tasks for lead")'''
    
    if old_new_lead_log in content:
        content = content.replace(old_new_lead_log, new_new_lead_log)
        changes_made.append("✅ Enhanced handle_new_lead logging")
    
    # 2. Покращуємо логування в CONSUMER_PHONE_NUMBER_OPT_IN_EVENT handler
    old_optin_event_log = '''                    logger.info(f"[WEBHOOK] 🔄 NEW LOGIC: Phone opt-in will use No Phone scenario")
                    logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True (for logging only)")'''
    
    new_optin_event_log = '''                    logger.info(f"[WEBHOOK] 🔄 UNIFIED LOGIC: Phone opt-in → No Phone scenario")
                    logger.info(f"[WEBHOOK] =================== PHONE OPT-IN EVENT DETAILS ===================")
                    logger.info(f"[WEBHOOK] 📱 Consumer agreed to provide phone number via Yelp interface")
                    logger.info(f"[WEBHOOK] 🎯 NEW BEHAVIOR: Will use No Phone scenario instead of separate logic")
                    logger.info(f"[WEBHOOK] 📋 What happens next:")
                    logger.info(f"[WEBHOOK] - LeadDetail.phone_opt_in set to True (for frontend badge)")
                    logger.info(f"[WEBHOOK] - No separate phone opt-in tasks created")
                    logger.info(f"[WEBHOOK] - Uses existing No Phone templates and follow-ups")
                    logger.info(f"[WEBHOOK] - Frontend shows 'Phone Opt-In' badge for identification")
                    logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True (for frontend display)")'''
    
    if old_optin_event_log in content:
        content = content.replace(old_optin_event_log, new_optin_event_log)
        changes_made.append("✅ Enhanced phone opt-in event logging")
    
    # 3. Покращуємо логування в _process_auto_response
    old_process_log = '''        # Determine scenario name and reason for SMS
        if phone_opt_in and phone_available:
            scenario_name = "📱📞 PHONE OPT-IN + PHONE AVAILABLE"
            reason = "Phone Opt-in with Number"
        elif phone_opt_in:
            scenario_name = "📱 PHONE OPT-IN ONLY"
            reason = "Phone Opt-in"
        elif phone_available:
            scenario_name = "📞 PHONE AVAILABLE ONLY"
            reason = "Phone Number Found"
        else:
            scenario_name = "💬 NO PHONE (Customer Reply)"
            reason = "Customer Reply"
        
        logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: {scenario_name}")
        logger.info(f"[AUTO-RESPONSE] SMS Reason: {reason}")
        logger.info(f"[AUTO-RESPONSE] This will look for AutoResponseSettings with:")
        logger.info(f"[AUTO-RESPONSE] - phone_opt_in={phone_opt_in}")
        logger.info(f"[AUTO-RESPONSE] - phone_available={phone_available}")'''
    
    new_process_log = '''        # Determine scenario name and reason for SMS (2-scenario system)
        if phone_available:
            scenario_name = "📞 PHONE AVAILABLE"
            reason = "Phone Number Found"
            scenario_description = "Lead provided phone number in text or consumer response"
        else:
            scenario_name = "💬 NO PHONE / CUSTOMER REPLY"
            reason = "Customer Reply"
            scenario_description = "Regular lead without phone OR phone opt-in lead (unified)"
        
        logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: {scenario_name}")
        logger.info(f"[AUTO-RESPONSE] Description: {scenario_description}")
        logger.info(f"[AUTO-RESPONSE] SMS Reason: {reason}")
        logger.info(f"[AUTO-RESPONSE] =================== SCENARIO DETAILS ===================")
        logger.info(f"[AUTO-RESPONSE] System now uses 2 scenarios instead of 3:")
        logger.info(f"[AUTO-RESPONSE] 1. 💬 No Phone/Customer Reply (phone_opt_in=False, phone_available=False)")
        logger.info(f"[AUTO-RESPONSE] 2. 📞 Phone Available (phone_opt_in=False, phone_available=True)")
        logger.info(f"[AUTO-RESPONSE] Current scenario parameters:")
        logger.info(f"[AUTO-RESPONSE] - phone_opt_in={phone_opt_in} (always False in new system)")
        logger.info(f"[AUTO-RESPONSE] - phone_available={phone_available}")
        logger.info(f"[AUTO-RESPONSE] Will look for AutoResponseSettings with these parameters")'''
    
    if old_process_log in content:
        content = content.replace(old_process_log, new_process_log)
        changes_made.append("✅ Enhanced _process_auto_response logging")
    
    # 4. Додаємо логування в consumer response для phone opt-in
    old_optin_response_log = '''                        logger.info(f"[WEBHOOK] 🔄 NEW BEHAVIOR: Phone opt-in responses use No Phone logic")
                        logger.info(f"[WEBHOOK] This unifies phone opt-in with regular no-phone responses")'''
    
    new_optin_response_log = '''                        logger.info(f"[WEBHOOK] 🔄 UNIFIED RESPONSE LOGIC: Phone opt-in → No Phone")
                        logger.info(f"[WEBHOOK] =================== PHONE OPT-IN CONSUMER RESPONSE ===================")
                        logger.info(f"[WEBHOOK] 📱 This is a phone opt-in lead that consumer is responding to")
                        logger.info(f"[WEBHOOK] 🎯 NEW SYSTEM: Phone opt-in responses treated as No Phone responses")
                        logger.info(f"[WEBHOOK] 📋 What this means:")
                        logger.info(f"[WEBHOOK] - Uses No Phone cancellation logic")
                        logger.info(f"[WEBHOOK] - Uses No Phone SMS templates")
                        logger.info(f"[WEBHOOK] - Frontend still shows 'Phone Opt-In' badge")
                        logger.info(f"[WEBHOOK] - Unified experience with regular no-phone responses")'''
    
    if old_optin_response_log in content:
        content = content.replace(old_optin_response_log, new_optin_response_log)
        changes_made.append("✅ Enhanced phone opt-in consumer response logging")
    
    # 5. Покращуємо логування в handle_phone_available
    old_phone_available_start = '''        logger.info(f"[AUTO-RESPONSE] 📞 STARTING handle_phone_available")
        logger.info(f"[AUTO-RESPONSE] ============== PHONE AVAILABLE HANDLER ==============")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone number provided (phone_opt_in=False, phone_available=True)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: Phone number found in consumer text")'''
    
    new_phone_available_start = '''        logger.info(f"[AUTO-RESPONSE] 📞 STARTING handle_phone_available")
        logger.info(f"[AUTO-RESPONSE] =================== PHONE AVAILABLE SCENARIO ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: Phone Available (1 of 2 scenarios)")
        logger.info(f"[AUTO-RESPONSE] Trigger: Phone number found in consumer text")
        logger.info(f"[AUTO-RESPONSE] Parameters: phone_opt_in=False, phone_available=True")
        logger.info(f"[AUTO-RESPONSE] Templates: Will use Phone Available templates and follow-ups")'''
    
    if old_phone_available_start in content:
        content = content.replace(old_phone_available_start, new_phone_available_start)
        changes_made.append("✅ Enhanced handle_phone_available logging")
    
    # Записуємо оновлений файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return changes_made

if __name__ == "__main__":
    changes = add_detailed_logging()
    
    if changes:
        print("🎉 ДЕТАЛЬНЕ ЛОГУВАННЯ ДЛЯ 2 СЦЕНАРІЇВ ДОДАНО!")
        print("=" * 50)
        for change in changes:
            print(change)
        
        print("\n🔍 ТЕПЕР ЛОГИ ПОКАЗУВАТИМУТЬ:")
        print("✅ Чіткий розподіл між 2 сценаріями")
        print("✅ Детальну інформацію про phone opt-in ліди")
        print("✅ Пояснення що phone opt-in використовує No Phone логіку")
        print("✅ Інформацію про frontend badge відображення")
        print("✅ Покрокове відстеження обробки кожного типу ліда")
        
    else:
        print("❌ Не вдалося додати детальне логування")
