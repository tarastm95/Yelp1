#!/usr/bin/env python3
"""
Скрипт для додавання детального логування consumer responses
"""

def add_consumer_response_logging():
    """
    Додає детальне логування для consumer responses та phone opt-in detection
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = []
    
    # 1. Покращуємо логування phone opt-in consumer response detection
    old_optin_detection = '''                    # 🔥 КРИТИЧНИЙ ФІХ: Перевіряємо phone opt-in ПЕРШИМ, перед перевіркою pending tasks
                    ld_flags = LeadDetail.objects.filter(lead_id=lid).values("phone_opt_in", "phone_number").first()
                    if (ld_flags and ld_flags.get("phone_opt_in")):
                        logger.info(f"[WEBHOOK] 📱 ВИЯВЛЕНО ВІДПОВІДЬ СПОЖИВАЧА НА PHONE OPT-IN")
                        logger.info(f"[WEBHOOK] ========== ВІДПОВІДЬ НА PHONE OPT-IN ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Текст події: '{text[:100]}...'" + ("" if len(text) <= 100 else " (обрізано)"))
                        logger.info(f"[WEBHOOK] Phone opt-in прапор: {ld_flags.get('phone_opt_in')}")
                        logger.info(f"[WEBHOOK] Збережений номер телефону: {ld_flags.get('phone_number')}")
                        logger.info(f"[WEBHOOK] Телефон знайдено в поточній відповіді: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ Споживач відповів на phone opt-in потік - скасовуємо phone opt-in завдання")'''
    
    new_optin_detection = '''                    # 🔥 КРИТИЧНИЙ ФІХ: Перевіряємо phone opt-in ПЕРШИМ, перед перевіркою pending tasks
                    logger.info(f"[WEBHOOK] 🔍 CHECKING FOR PHONE OPT-IN CONSUMER RESPONSE")
                    ld_flags = LeadDetail.objects.filter(lead_id=lid).values("phone_opt_in", "phone_number").first()
                    logger.info(f"[WEBHOOK] LeadDetail flags: {ld_flags}")
                    
                    if (ld_flags and ld_flags.get("phone_opt_in")):
                        logger.info(f"[WEBHOOK] 📱 ✅ PHONE OPT-IN CONSUMER RESPONSE DETECTED!")
                        logger.info(f"[WEBHOOK] =================== PHONE OPT-IN CONSUMER RESPONSE ===================")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (обрізано)"))
                        logger.info(f"[WEBHOOK] Phone opt-in flag: {ld_flags.get('phone_opt_in')}")
                        logger.info(f"[WEBHOOK] Stored phone number: {ld_flags.get('phone_number')}")
                        logger.info(f"[WEBHOOK] Phone found in current response: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ Consumer replied to phone opt-in flow - processing cancellation")
                        
                        # Show existing phone opt-in tasks before cancellation
                        existing_optin_tasks = LeadPendingTask.objects.filter(
                            lead_id=lid, phone_opt_in=True, active=True
                        )
                        logger.info(f"[WEBHOOK] 📋 EXISTING PHONE OPT-IN TASKS BEFORE CANCELLATION:")
                        logger.info(f"[WEBHOOK] - Total phone opt-in tasks: {existing_optin_tasks.count()}")
                        
                        for task in existing_optin_tasks:
                            logger.info(f"[WEBHOOK] - Task {task.task_id}: '{task.text[:50]}...', created: {task.created_at}")'''
    
    if old_optin_detection in content:
        content = content.replace(old_optin_detection, new_optin_detection)
        changes_made.append("✅ Enhanced phone opt-in consumer response detection")
    
    # 2. Покращуємо логування після скасування завдань
    old_after_cancel = '''                            logger.info(f"[WEBHOOK] 🚀 ВИКЛИКАЄМО _cancel_pre_phone_tasks для phone opt-in відповіді")
                            self._cancel_pre_phone_tasks(lid, reason=reason)
                            
                            # Надсилаємо SMS сповіщення для відповіді споживача на phone opt-in
                            logger.info(f"[WEBHOOK] 📱 НАДСИЛАЄМО SMS для відповіді на Phone Opt-in")
                            self._send_customer_reply_sms_only(lid)'''
    
    new_after_cancel = '''                            logger.info(f"[WEBHOOK] 🚀 CALLING _cancel_pre_phone_tasks for phone opt-in response")
                            self._cancel_pre_phone_tasks(lid, reason=reason)
                            
                            # Check what tasks remain after cancellation
                            remaining_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                            logger.info(f"[WEBHOOK] 📊 TASKS REMAINING AFTER CANCELLATION:")
                            logger.info(f"[WEBHOOK] - Total remaining active tasks: {remaining_tasks.count()}")
                            
                            for task in remaining_tasks:
                                logger.info(f"[WEBHOOK] - Remaining task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}")
                            
                            # Send SMS notification for phone opt-in consumer reply
                            logger.info(f"[WEBHOOK] 📱 SENDING Phone Opt-in Consumer Reply SMS")
                            self._send_customer_reply_sms_only(lid)'''
    
    if old_after_cancel in content:
        content = content.replace(old_after_cancel, new_after_cancel)
        changes_made.append("✅ Enhanced post-cancellation logging")
    
    # 3. Додаємо логування для звичайних consumer responses
    old_regular_response = '''                    elif pending:
                        logger.info(f"[WEBHOOK] 🚫 CLIENT RESPONDED WITHOUT PHONE NUMBER")
                        logger.info(f"[WEBHOOK] ========== CUSTOMER REPLY SCENARIO (NO PHONE) ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                        logger.info(f"[WEBHOOK] Has pending no-phone tasks: {pending}")
                        logger.info(f"[WEBHOOK] Phone number found in text: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ Customer Reply scenario - cancelling tasks + sending Customer Reply SMS")
                        logger.info(f"[WEBHOOK] 🎯 SMS DECISION ANALYSIS:")
                        logger.info(f"[WEBHOOK] - Scenario: Customer Reply (phone_opt_in=False, phone_available=False)")
                        logger.info(f"[WEBHOOK] - Current behavior: Cancel pending tasks + Customer Reply SMS")
                        
                        reason = "Client responded, but no number was found"
                        self._cancel_no_phone_tasks(lid, reason=reason)'''
    
    new_regular_response = '''                    elif pending:
                        logger.info(f"[WEBHOOK] 💬 REGULAR CONSUMER RESPONSE (NO PHONE OPT-IN)")
                        logger.info(f"[WEBHOOK] =================== REGULAR CUSTOMER REPLY ===================")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                        logger.info(f"[WEBHOOK] Has pending no-phone tasks: {pending}")
                        logger.info(f"[WEBHOOK] Phone number found in text: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ Regular customer reply - processing standard cancellation")
                        
                        # Show existing no-phone tasks before cancellation
                        existing_no_phone_tasks = LeadPendingTask.objects.filter(
                            lead_id=lid, phone_opt_in=False, phone_available=False, active=True
                        )
                        logger.info(f"[WEBHOOK] 📋 EXISTING NO-PHONE TASKS BEFORE CANCELLATION:")
                        logger.info(f"[WEBHOOK] - Total no-phone tasks: {existing_no_phone_tasks.count()}")
                        
                        for task in existing_no_phone_tasks:
                            logger.info(f"[WEBHOOK] - Task {task.task_id}: '{task.text[:50]}...', created: {task.created_at}")
                        
                        logger.info(f"[WEBHOOK] 🎯 SCENARIO: Regular Customer Reply (phone_opt_in=False, phone_available=False)")
                        logger.info(f"[WEBHOOK] 🎯 ACTION: Cancel no-phone tasks + Send Customer Reply SMS")
                        
                        reason = "Client responded, but no number was found"
                        self._cancel_no_phone_tasks(lid, reason=reason)
                        
                        # Check what tasks remain after cancellation
                        remaining_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                        logger.info(f"[WEBHOOK] 📊 TASKS REMAINING AFTER NO-PHONE CANCELLATION:")
                        logger.info(f"[WEBHOOK] - Total remaining active tasks: {remaining_tasks.count()}")
                        
                        for task in remaining_tasks:
                            logger.info(f"[WEBHOOK] - Remaining task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}")'''
    
    if old_regular_response in content:
        content = content.replace(old_regular_response, new_regular_response)
        changes_made.append("✅ Enhanced regular consumer response logging")
    
    # 4. Додаємо логування на початку consumer event processing
    old_consumer_start = '''                if is_new and e.get("user_type") == "CONSUMER":
                    logger.info(f"[WEBHOOK] 👤 PROCESSING CONSUMER EVENT as TRULY NEW")
                    logger.info(f"[WEBHOOK] Event ID: {eid}")
                    logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                    logger.info(f"[WEBHOOK] Has phone in text: {has_phone}")
                    if has_phone:
                        logger.info(f"[WEBHOOK] Extracted phone: {phone}")'''
    
    new_consumer_start = '''                if is_new and e.get("user_type") == "CONSUMER":
                    logger.info(f"[WEBHOOK] 👤 PROCESSING CONSUMER EVENT as TRULY NEW")
                    logger.info(f"[WEBHOOK] =================== CONSUMER EVENT ANALYSIS ===================")
                    logger.info(f"[WEBHOOK] Event ID: {eid}")
                    logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                    logger.info(f"[WEBHOOK] Has phone in text: {has_phone}")
                    if has_phone:
                        logger.info(f"[WEBHOOK] Extracted phone: {phone}")
                    
                    # Show current lead state
                    current_lead = LeadDetail.objects.filter(lead_id=lid).first()
                    if current_lead:
                        logger.info(f"[WEBHOOK] 📊 CURRENT LEAD STATE:")
                        logger.info(f"[WEBHOOK] - phone_opt_in: {current_lead.phone_opt_in}")
                        logger.info(f"[WEBHOOK] - phone_number: {current_lead.phone_number}")
                        logger.info(f"[WEBHOOK] - phone_in_text: {getattr(current_lead, 'phone_in_text', 'Not set')}")
                    else:
                        logger.info(f"[WEBHOOK] ⚠️ No LeadDetail found for {lid}")'''
    
    if old_consumer_start in content:
        content = content.replace(old_consumer_start, new_consumer_start)
        changes_made.append("✅ Enhanced consumer event start logging")
    
    # Записуємо оновлений файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return changes_made

if __name__ == "__main__":
    changes = add_consumer_response_logging()
    
    if changes:
        print("🎉 ДЕТАЛЬНЕ ЛОГУВАННЯ CONSUMER RESPONSES ДОДАНО!")
        print("=" * 50)
        for change in changes:
            print(change)
        
        print("\n🔍 ДОДАТКОВЕ ЛОГУВАННЯ ВКЛЮЧАЄ:")
        print("✅ Поточний стан LeadDetail при consumer response")
        print("✅ Детальну інформацію про існуючі завдання перед скасуванням")
        print("✅ Список завдань, що залишилися після скасування")
        print("✅ Чіткі мітки для phone opt-in vs regular consumer responses")
        print("✅ Покрокове відстеження процесу скасування завдань")
        
        print("\n📋 ТЕПЕР ВИ ПОБАЧИТЕ:")
        print("• Чи є phone_opt_in=True в LeadDetail")
        print("• Які phone opt-in завдання існують")
        print("• Які завдання скасовуються")
        print("• Які завдання залишаються активними")
        print("• Точну послідовність обробки events")
    else:
        print("❌ Не вдалося додати consumer response логування")
