#!/usr/bin/env python3
"""
Скрипт для виправлення handle_phone_opt_in логіки
"""

def fix_phone_opt_in_handler():
    """
    Виправляє handle_phone_opt_in щоб не скасовувати завдання непотрібно
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо та замінюємо проблемну частину
    old_text = '''        try:
            self._cancel_no_phone_tasks(lead_id, reason)
            logger.info(f"[AUTO-RESPONSE] Step 2: Starting auto-response for phone opt-in scenario")
            self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)'''
    
    new_text = '''        try:
            # Only cancel no-phone tasks if this is a direct phone opt-in event, not from handle_new_lead
            if reason and ("consumer response" not in reason.lower() and "new lead" not in reason.lower()):
                logger.info(f"[AUTO-RESPONSE] Cancelling no-phone tasks (direct phone opt-in event)")
                self._cancel_no_phone_tasks(lead_id, reason)
            else:
                logger.info(f"[AUTO-RESPONSE] Skipping task cancellation (tasks already handled correctly)")
            
            logger.info(f"[AUTO-RESPONSE] Step 2: Starting auto-response for phone opt-in scenario")
            self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)'''
    
    if old_text in content:
        content = content.replace(old_text, new_text)
        
        # Записуємо назад
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Виправлення handle_phone_opt_in застосовано успішно!")
        print("📝 Тепер handle_phone_opt_in не скасовує завдання непотрібно")
        print("🎯 Це запобігає конфліктам між різними handlers")
        return True
    else:
        print("❌ Не вдалося знайти код для заміни")
        print("🔍 Можливо код вже був змінений")
        return False

if __name__ == "__main__":
    fix_phone_opt_in_handler()
