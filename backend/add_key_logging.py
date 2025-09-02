#!/usr/bin/env python3
"""
Простий скрипт для додавання ключового логування
"""

def add_key_logging():
    """
    Додає ключові логи для відстеження сценаріїв
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Додаємо логування перед phone opt-in перевіркою
    old_line = "                    ld_flags = LeadDetail.objects.filter(lead_id=lid).values(\"phone_opt_in\", \"phone_number\").first()"
    
    new_lines = """                    logger.info(f"[WEBHOOK] 🔍 CHECKING FOR PHONE OPT-IN CONSUMER RESPONSE")
                    ld_flags = LeadDetail.objects.filter(lead_id=lid).values("phone_opt_in", "phone_number").first()
                    logger.info(f"[WEBHOOK] LeadDetail flags: {ld_flags}")
                    
                    # Show existing tasks before any processing
                    all_existing_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                    logger.info(f"[WEBHOOK] 📊 ALL EXISTING ACTIVE TASKS: {all_existing_tasks.count()}")
                    for task in all_existing_tasks:
                        logger.info(f"[WEBHOOK] - Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}")"""
    
    if old_line in content:
        content = content.replace(old_line, new_lines)
        print("✅ Додано логування для phone opt-in detection")
    
    # 2. Додаємо логування після скасування завдань
    old_cancel_line = "                            self._cancel_pre_phone_tasks(lid, reason=reason)"
    
    new_cancel_lines = """                            self._cancel_pre_phone_tasks(lid, reason=reason)
                            
                            # Check what tasks remain after cancellation
                            remaining_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                            logger.info(f"[WEBHOOK] 📊 TASKS AFTER CANCELLATION: {remaining_tasks.count()}")
                            for task in remaining_tasks:
                                logger.info(f"[WEBHOOK] - Remaining: {task.task_id}, phone_opt_in={task.phone_opt_in}")"""
    
    if old_cancel_line in content:
        content = content.replace(old_cancel_line, new_cancel_lines)
        print("✅ Додано логування після скасування завдань")
    
    # 3. Додаємо логування для regular consumer responses
    old_regular = "                        self._cancel_no_phone_tasks(lid, reason=reason)"
    
    new_regular = """                        logger.info(f"[WEBHOOK] 💬 REGULAR CONSUMER RESPONSE - cancelling no-phone tasks")
                        self._cancel_no_phone_tasks(lid, reason=reason)
                        
                        # Check what tasks remain after no-phone cancellation
                        remaining_after_regular = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                        logger.info(f"[WEBHOOK] 📊 TASKS AFTER NO-PHONE CANCELLATION: {remaining_after_regular.count()}")"""
    
    if old_regular in content:
        content = content.replace(old_regular, new_regular)
        print("✅ Додано логування для regular consumer responses")
    
    # Записуємо оновлений файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🎉 КЛЮЧОВЕ ЛОГУВАННЯ ДОДАНО!")
    print("\nТепер ви побачите:")
    print("• Стан LeadDetail flags (phone_opt_in, phone_number)")
    print("• Всі активні завдання перед обробкою")
    print("• Які завдання залишилися після скасування")
    print("• Чітке розділення phone opt-in vs regular responses")

if __name__ == "__main__":
    add_key_logging()
