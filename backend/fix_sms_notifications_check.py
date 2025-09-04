#!/usr/bin/env python3
"""
Додає перевірку sms_notifications_enabled в _send_customer_reply_sms_only
"""

def fix_sms_notifications_check():
    """
    Додає перевірку YelpBusiness.sms_notifications_enabled перед надсиланням SMS
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо місце після отримання business_id
    old_code = '''        logger.info(f"[CUSTOMER-REPLY-SMS] Business ID: {pl.business_id}")
        logger.info(f"[CUSTOMER-REPLY-SMS] ✅ SMS allowed - no previous SMS sent for this lead")
        
        # Get NotificationSettings for SMS'''
    
    new_code = '''        logger.info(f"[CUSTOMER-REPLY-SMS] Business ID: {pl.business_id}")
        
        # 🔒 CRITICAL: Check if SMS notifications are enabled for this business
        logger.info(f"[CUSTOMER-REPLY-SMS] 🔔 CHECKING SMS NOTIFICATIONS STATUS")
        business = YelpBusiness.objects.filter(business_id=pl.business_id).first()
        
        if business:
            logger.info(f"[CUSTOMER-REPLY-SMS] Business found: {business.name}")
            logger.info(f"[CUSTOMER-REPLY-SMS] SMS notifications enabled: {business.sms_notifications_enabled}")
            
            if not business.sms_notifications_enabled:
                logger.info(f"[CUSTOMER-REPLY-SMS] 🚫 SMS NOTIFICATIONS DISABLED for business: {pl.business_id}")
                logger.info(f"[CUSTOMER-REPLY-SMS] Business admin has turned off SMS notifications")
                logger.info(f"[CUSTOMER-REPLY-SMS] 🛑 EARLY RETURN - SMS disabled for this business")
                logger.info(f"[CUSTOMER-REPLY-SMS] This prevents unwanted SMS messages")
                return
            else:
                logger.info(f"[CUSTOMER-REPLY-SMS] ✅ SMS NOTIFICATIONS ENABLED for business: {pl.business_id}")
                logger.info(f"[CUSTOMER-REPLY-SMS] Proceeding with SMS sending")
        else:
            logger.warning(f"[CUSTOMER-REPLY-SMS] ⚠️ Business not found for business_id: {pl.business_id}")
            logger.warning(f"[CUSTOMER-REPLY-SMS] Cannot check SMS enable status - proceeding with caution")
        
        logger.info(f"[CUSTOMER-REPLY-SMS] ✅ SMS allowed - no previous SMS sent for this lead")
        
        # Get NotificationSettings for SMS'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Записуємо назад
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("🎉 SMS NOTIFICATIONS CHECK ДОДАНО!")
        print("=" * 50)
        print("✅ Додано перевірку YelpBusiness.sms_notifications_enabled")
        print("✅ Додано детальне логування SMS статусу")
        print("✅ Додано early return якщо SMS вимкнені")
        print("✅ Запобігання небажаних SMS повідомлень")
        
        print("\n🔍 ЩО ТЕПЕР ПЕРЕВІРЯЄТЬСЯ:")
        print("1. 🔒 YelpBusiness.sms_notifications_enabled (глобально для бізнесу)")
        print("2. 📱 phone_sms_sent (чи вже надсилалося SMS для цього ліда)")
        print("3. ⚙️ NotificationSetting існує для бізнесу")
        print("4. 📋 Шаблон повідомлення налаштований")
        
        print("\n🛡️ ЗАХИСТ ВІД НЕБАЖАНИХ SMS:")
        print("• Якщо admin вимкнув SMS для бізнесу → SMS НЕ надсилається")
        print("• Якщо SMS вже надсилалося для ліда → SMS НЕ дублюється")
        print("• Детальне логування для діагностики проблем")
        
        return True
    else:
        print("❌ Не вдалося знайти код для заміни")
        print("🔍 Можливо структура _send_customer_reply_sms_only змінилася")
        return False

if __name__ == "__main__":
    fix_sms_notifications_check()
