#!/usr/bin/env python3
"""
Скрипт для виправлення handle_new_lead логіки
"""

def fix_handle_new_lead():
    """
    Виправляє handle_new_lead щоб не створювати no-phone завдання для phone opt-in лідів
    """
    
    file_path = "webhooks/webhook_views.py"  # Виправлений шлях
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Знаходимо та замінюємо проблемну частину
    old_text = '''        try:
            # Call _process_auto_response to create LeadDetail but disable SMS for new leads
            self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)
            logger.info(f"[AUTO-RESPONSE] ✅ handle_new_lead completed successfully for {lead_id}")'''
    
    new_text = '''        try:
            # Check if this lead has phone opt-in before creating tasks
            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
            if ld and ld.phone_opt_in:
                logger.info(f"[AUTO-RESPONSE] Lead has phone_opt_in=True - skipping no-phone task creation")
                logger.info(f"[AUTO-RESPONSE] Phone opt-in handler will create appropriate tasks")
                # Just create LeadDetail without no-phone tasks - phone opt-in handler will handle tasks
                self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)
            else:
                logger.info(f"[AUTO-RESPONSE] Lead has phone_opt_in=False - creating no-phone tasks")
                # Call _process_auto_response to create LeadDetail but disable SMS for new leads
                self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)
            logger.info(f"[AUTO-RESPONSE] ✅ handle_new_lead completed successfully for {lead_id}")'''
    
    if old_text in content:
        content = content.replace(old_text, new_text)
        
        # Записуємо назад
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Виправлення handle_new_lead застосовано успішно!")
        print("📝 Тепер handle_new_lead перевіряє phone_opt_in перед створенням завдань")
        print("🎯 Це запобігає створенню no-phone завдань для phone opt-in лідів")
        return True
    else:
        print("❌ Не вдалося знайти код для заміни")
        print("🔍 Спробуємо знайти альтернативний варіант...")
        
        # Спробуємо знайти частину коду
        if "self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)" in content:
            print("✅ Знайдено цільовий рядок для заміни")
            
            # Замінимо тільки цей рядок
            old_line = "            self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)"
            new_lines = '''            # Check if this lead has phone opt-in before creating tasks
            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
            if ld and ld.phone_opt_in:
                logger.info(f"[AUTO-RESPONSE] Lead has phone_opt_in=True - skipping no-phone task creation")
                logger.info(f"[AUTO-RESPONSE] Phone opt-in handler will create appropriate tasks")
                # Just create LeadDetail without no-phone tasks - phone opt-in handler will handle tasks
                self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)
            else:
                logger.info(f"[AUTO-RESPONSE] Lead has phone_opt_in=False - creating no-phone tasks")
                # Call _process_auto_response to create LeadDetail but disable SMS for new leads
                self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)'''
            
            content = content.replace(old_line, new_lines)
            
            # Записуємо назад
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Альтернативне виправлення застосовано успішно!")
            return True
        else:
            print("❌ Не вдалося знайти жодний варіант для заміни")
            return False

if __name__ == "__main__":
    fix_handle_new_lead()
