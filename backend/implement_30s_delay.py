#!/usr/bin/env python3
"""
Реалізує 30-секундну затримку в handle_new_lead
"""

def implement_30s_delay():
    """
    Додає 30-секундну затримку в handle_new_lead для phone opt-in detection
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Старий код для заміни
    old_code = '''        try:
            # Check if this lead has phone opt-in before creating tasks
            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
            logger.info(f"[AUTO-RESPONSE] 🔍 SCENARIO DETERMINATION:")
            logger.info(f"[AUTO-RESPONSE] - LeadDetail exists: {ld is not None}")
            
            if ld:
                logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {ld.phone_opt_in}")
                logger.info(f"[AUTO-RESPONSE] - phone_number: {ld.phone_number}")
                logger.info(f"[AUTO-RESPONSE] - phone_in_text: {getattr(ld, 'phone_in_text', 'Not set')}")
            
            if ld and ld.phone_opt_in:
                logger.info(f"[AUTO-RESPONSE] 📱 SCENARIO SELECTED: PHONE OPT-IN")
                logger.info(f"[AUTO-RESPONSE] ========== NEW LEAD → PHONE OPT-IN SCENARIO ==========")
                logger.info(f"[AUTO-RESPONSE] Lead has phone_opt_in=True - creating phone opt-in tasks")
                logger.info(f"[AUTO-RESPONSE] Phone opt-in handler will create additional tasks if needed")
                # Create phone opt-in tasks for new lead
                self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)
                logger.info(f"[AUTO-RESPONSE] ✅ Phone opt-in scenario tasks created")
            else:
                logger.info(f"[AUTO-RESPONSE] 💬 SCENARIO SELECTED: NO PHONE")
                logger.info(f"[AUTO-RESPONSE] ========== NEW LEAD → NO PHONE SCENARIO ==========")
                logger.info(f"[AUTO-RESPONSE] Lead has phone_opt_in=False - creating no-phone tasks")
                logger.info(f"[AUTO-RESPONSE] This will create standard follow-up sequence")
                # Call _process_auto_response to create LeadDetail but disable SMS for new leads
                self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)
                logger.info(f"[AUTO-RESPONSE] ✅ No-phone scenario tasks created")
            logger.info(f"[AUTO-RESPONSE] ✅ handle_new_lead completed successfully for {lead_id}")'''
    
    # Новий код з 30-секундною затримкою
    new_code = '''        try:
            import time
            from django.utils import timezone
            
            # 30-second delay to allow phone opt-in events to be processed
            delay_seconds = 30
            
            logger.info(f"[AUTO-RESPONSE] ⏰ IMPLEMENTING 30-SECOND DELAY for phone opt-in detection")
            logger.info(f"[AUTO-RESPONSE] This prevents no-phone tasks from being created for phone opt-in leads")
            logger.info(f"[AUTO-RESPONSE] Delay started at: {timezone.now()}")
            logger.info(f"[AUTO-RESPONSE] Waiting {delay_seconds} seconds for CONSUMER_PHONE_NUMBER_OPT_IN_EVENT...")
            
            time.sleep(delay_seconds)
            
            logger.info(f"[AUTO-RESPONSE] ⏰ 30-SECOND DELAY COMPLETED")
            logger.info(f"[AUTO-RESPONSE] Delay ended at: {timezone.now()}")
            logger.info(f"[AUTO-RESPONSE] Now checking final phone_opt_in status after delay")
            
            # Check final status after delay
            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
            logger.info(f"[AUTO-RESPONSE] 🔍 FINAL SCENARIO DETERMINATION AFTER 30s DELAY:")
            logger.info(f"[AUTO-RESPONSE] - LeadDetail exists: {ld is not None}")
            
            if ld:
                logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {ld.phone_opt_in}")
                logger.info(f"[AUTO-RESPONSE] - phone_number: {ld.phone_number}")
                logger.info(f"[AUTO-RESPONSE] - phone_in_text: {getattr(ld, 'phone_in_text', 'Not set')}")
            
            if ld and ld.phone_opt_in:
                logger.info(f"[AUTO-RESPONSE] 📱 FINAL DECISION: PHONE OPT-IN DETECTED AFTER DELAY")
                logger.info(f"[AUTO-RESPONSE] ========== PHONE OPT-IN LEAD → SKIP NO-PHONE TASKS ==========")
                logger.info(f"[AUTO-RESPONSE] Phone opt-in was set during the 30-second delay period")
                logger.info(f"[AUTO-RESPONSE] Phone opt-in handler will create appropriate phone opt-in tasks")
                logger.info(f"[AUTO-RESPONSE] ✅ Successfully prevented no-phone task creation for phone opt-in lead")
                logger.info(f"[AUTO-RESPONSE] 🚫 NO TASKS CREATED - avoiding duplicate scenarios")
            else:
                logger.info(f"[AUTO-RESPONSE] 💬 FINAL DECISION: REGULAR LEAD (NO PHONE OPT-IN)")
                logger.info(f"[AUTO-RESPONSE] ========== REGULAR LEAD → CREATE NO-PHONE TASKS ==========")
                logger.info(f"[AUTO-RESPONSE] No phone opt-in detected after 30-second delay")
                logger.info(f"[AUTO-RESPONSE] Creating standard no-phone follow-up sequence")
                # Call _process_auto_response to create LeadDetail but disable SMS for new leads
                self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)
                logger.info(f"[AUTO-RESPONSE] ✅ No-phone scenario tasks created")
            
            logger.info(f"[AUTO-RESPONSE] ✅ handle_new_lead completed successfully for {lead_id}")'''
    
    # Виконуємо заміну
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Записуємо назад
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("🎉 30-СЕКУНДНА ЗАТРИМКА УСПІШНО РЕАЛІЗОВАНА!")
        print("=" * 50)
        print("✅ Додано 30-секундну затримку в handle_new_lead")
        print("✅ Додано детальне логування процесу")
        print("✅ Додано перевірку phone_opt_in після затримки")
        print("✅ Додано запобігання створенню no-phone завдань для phone opt-in лідів")
        
        print("\n🎯 ЯК ЦЕ ПРАЦЮВАТИМЕ:")
        print("📱 Phone Opt-In ліди:")
        print("  1. handle_new_lead чекає 30 секунд")
        print("  2. phone opt-in подія встановлює phone_opt_in=True")
        print("  3. handle_new_lead виявляє phone_opt_in=True → НЕ створює no-phone завдання")
        print("  4. handle_phone_opt_in створює ТІЛЬКИ phone opt-in завдання")
        print("  5. Результат: Тільки phone opt-in повідомлення ✅")
        
        print("\n💬 Звичайні ліди:")
        print("  1. handle_new_lead чекає 30 секунд")
        print("  2. phone_opt_in залишається False")
        print("  3. handle_new_lead створює no-phone завдання")
        print("  4. Результат: Тільки no-phone повідомлення ✅")
        
        print("\n🔍 ЛОГУВАННЯ:")
        print("• Точний час початку і кінця затримки")
        print("• Стан LeadDetail до і після затримки")
        print("• Чітке рішення про сценарій")
        print("• Запобігання дублюванню завдань")
        
        return True
    else:
        print("❌ Не вдалося знайти код для заміни")
        print("🔍 Можливо структура коду змінилася")
        
        # Спробуємо знайти альтернативний патерн
        if "# Check if this lead has phone opt-in before creating tasks" in content:
            print("✅ Знайдено початок блоку для заміни")
            print("📝 Потрібно замінити вручну - код частково відрізняється")
        
        return False

if __name__ == "__main__":
    implement_30s_delay()
