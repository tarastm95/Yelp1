#!/usr/bin/env python3
"""
Додає перевірку sms_notifications_enabled в _process_auto_response
"""

def fix_auto_response_sms_check():
    """
    Додає перевірку YelpBusiness.sms_notifications_enabled в _process_auto_response
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо місце після final_sms_decision
    old_code = '''            if final_sms_decision:
                logger.info(f"[AUTO-RESPONSE] 🚀 SENDING SMS for {reason} scenario")
                
                # Get NotificationSettings for this business to send SMS
                from .models import NotificationSetting'''
    
    new_code = '''            if final_sms_decision:
                logger.info(f"[AUTO-RESPONSE] 🚀 PRELIMINARY SMS DECISION: True for {reason} scenario")
                
                # 🔒 CRITICAL: Check if SMS notifications are globally enabled for this business
                logger.info(f"[AUTO-RESPONSE] 🔔 CHECKING BUSINESS SMS NOTIFICATIONS STATUS")
                business = YelpBusiness.objects.filter(business_id=pl.business_id).first()
                
                if business:
                    logger.info(f"[AUTO-RESPONSE] Business found: {business.name}")
                    logger.info(f"[AUTO-RESPONSE] SMS notifications enabled: {business.sms_notifications_enabled}")
                    
                    if not business.sms_notifications_enabled:
                        logger.info(f"[AUTO-RESPONSE] 🚫 SMS NOTIFICATIONS DISABLED for business: {pl.business_id}")
                        logger.info(f"[AUTO-RESPONSE] Business admin has turned off SMS notifications")
                        logger.info(f"[AUTO-RESPONSE] 🛑 CANCELLING SMS - business SMS disabled")
                        logger.info(f"[AUTO-RESPONSE] AutoResponseSettings SMS will be skipped")
                        final_sms_decision = False
                    else:
                        logger.info(f"[AUTO-RESPONSE] ✅ SMS NOTIFICATIONS ENABLED - proceeding with SMS")
                else:
                    logger.warning(f"[AUTO-RESPONSE] ⚠️ Business not found for business_id: {pl.business_id}")
                    logger.warning(f"[AUTO-RESPONSE] Cannot verify SMS enable status - proceeding with caution")
                
                logger.info(f"[AUTO-RESPONSE] 🎯 FINAL SMS DECISION AFTER BUSINESS CHECK: {final_sms_decision}")
                
                if final_sms_decision:
                    logger.info(f"[AUTO-RESPONSE] 📤 SENDING SMS for {reason} scenario")
                
                    # Get NotificationSettings for this business to send SMS
                    from .models import NotificationSetting'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Записуємо назад
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ SMS BUSINESS CHECK ДОДАНО В _process_auto_response!")
        print("🔒 Тепер AutoResponseSettings SMS також перевіряє business enable status")
        return True
    else:
        print("❌ Не вдалося знайти код для заміни в _process_auto_response")
        return False

if __name__ == "__main__":
    fix_auto_response_sms_check()
