#!/usr/bin/env python3
"""
Скрипт для додавання детального логування для всіх сценаріїв
"""

def add_detailed_logging():
    """
    Додає детальне логування для відстеження сценаріїв та завдань
    """
    
    file_path = "webhooks/webhook_views.py"
    
    # Читаємо файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = []
    
    # 1. Покращуємо логування в handle_new_lead
    old_new_lead = '''        logger.info(f"[AUTO-RESPONSE] About to call _process_auto_response with phone_opt_in=False, phone_available=False")
        
        try:
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
                self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)'''
    
    new_new_lead = '''        logger.info(f"[AUTO-RESPONSE] About to determine scenario for new lead")
        
        try:
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
                logger.info(f"[AUTO-RESPONSE] ✅ No-phone scenario tasks created")'''
    
    if old_new_lead in content:
        content = content.replace(old_new_lead, new_new_lead)
        changes_made.append("✅ Enhanced handle_new_lead logging")
    
    # 2. Покращуємо логування в handle_phone_opt_in
    old_phone_optin = '''        logger.info(f"[AUTO-RESPONSE] Step 1: Cancelling no-phone tasks")
        
        try:
            # Only cancel no-phone tasks if this is a direct phone opt-in event, not from handle_new_lead
            if reason and ("consumer response" not in reason.lower() and "new lead" not in reason.lower()):
                logger.info(f"[AUTO-RESPONSE] Cancelling no-phone tasks (direct phone opt-in event)")
                self._cancel_no_phone_tasks(lead_id, reason)
            else:
                logger.info(f"[AUTO-RESPONSE] Skipping task cancellation (tasks already handled correctly)")
            
            logger.info(f"[AUTO-RESPONSE] Step 2: Starting auto-response for phone opt-in scenario")
            self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)'''
    
    new_phone_optin = '''        logger.info(f"[AUTO-RESPONSE] 🔍 PHONE OPT-IN SCENARIO ANALYSIS:")
        logger.info(f"[AUTO-RESPONSE] - Trigger reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] - Is consumer response: {'consumer response' in (reason or '').lower()}")
        logger.info(f"[AUTO-RESPONSE] - Is new lead: {'new lead' in (reason or '').lower()}")
        
        # Check existing tasks before making changes
        existing_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📋 EXISTING ACTIVE TASKS BEFORE PROCESSING:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {existing_tasks.count()}")
        
        for task in existing_tasks:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}, text='{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] Step 1: Determining task cancellation strategy")
        
        try:
            # Only cancel no-phone tasks if this is a direct phone opt-in event, not from handle_new_lead
            if reason and ("consumer response" not in reason.lower() and "new lead" not in reason.lower()):
                logger.info(f"[AUTO-RESPONSE] 🚫 CANCELLING NO-PHONE TASKS (direct phone opt-in event)")
                logger.info(f"[AUTO-RESPONSE] This is a standalone phone opt-in event - need to cancel conflicting tasks")
                self._cancel_no_phone_tasks(lead_id, reason)
            else:
                logger.info(f"[AUTO-RESPONSE] ⏭️ SKIPPING TASK CANCELLATION")
                logger.info(f"[AUTO-RESPONSE] Reason: Tasks already handled correctly by previous handler")
            
            logger.info(f"[AUTO-RESPONSE] Step 2: Creating phone opt-in tasks")
            logger.info(f"[AUTO-RESPONSE] 📱 CREATING PHONE OPT-IN SCENARIO TASKS")
            self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)
            
            # Log final state
            final_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
            logger.info(f"[AUTO-RESPONSE] 📋 FINAL ACTIVE TASKS AFTER PROCESSING:")
            logger.info(f"[AUTO-RESPONSE] - Total active tasks: {final_tasks.count()}")
            
            for task in final_tasks:
                logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}, text='{task.text[:50]}...'")'''
    
    if old_phone_optin in content:
        content = content.replace(old_phone_optin, new_phone_optin)
        changes_made.append("✅ Enhanced handle_phone_opt_in logging")
    
    # 3. Додаємо логування в handle_phone_available (якщо є)
    phone_available_pattern = '''    def handle_phone_available(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 📞 STARTING handle_phone_available")
        logger.info(f"[AUTO-RESPONSE] ============== PHONE AVAILABLE HANDLER ==============")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone number provided (phone_opt_in=False, phone_available=True)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: Phone number found in consumer text")'''
    
    enhanced_phone_available = '''    def handle_phone_available(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 📞 STARTING handle_phone_available")
        logger.info(f"[AUTO-RESPONSE] ============== PHONE AVAILABLE HANDLER ==============")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone number provided (phone_opt_in=False, phone_available=True)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: Phone number found in consumer text")
        
        # Check existing tasks before making changes
        existing_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📋 EXISTING ACTIVE TASKS BEFORE PHONE AVAILABLE PROCESSING:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {existing_tasks.count()}")
        
        for task in existing_tasks:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}, text='{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] 📞 SCENARIO SELECTED: PHONE AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] ========== PHONE NUMBER PROVIDED SCENARIO ==========")'''
    
    if phone_available_pattern in content:
        content = content.replace(phone_available_pattern, enhanced_phone_available)
        changes_made.append("✅ Enhanced handle_phone_available logging")
    
    # 4. Покращуємо логування в _process_auto_response
    old_process_auto = '''    def _process_auto_response(
        self, lead_id: str, phone_opt_in: bool, phone_available: bool
    ):
        logger.info(f"[AUTO-RESPONSE] 🔧 STARTING _process_auto_response")
        logger.info(f"[AUTO-RESPONSE] Parameters:")
        logger.info(f"[AUTO-RESPONSE] - Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {phone_opt_in}")
        logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
        
        # Determine reason for SMS based on scenario
        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        else:
            reason = "Customer Reply"
        
        logger.info(f"[AUTO-RESPONSE] SMS Reason: {reason}")'''
    
    new_process_auto = '''    def _process_auto_response(
        self, lead_id: str, phone_opt_in: bool, phone_available: bool
    ):
        logger.info(f"[AUTO-RESPONSE] 🔧 STARTING _process_auto_response")
        logger.info(f"[AUTO-RESPONSE] =================== SCENARIO PROCESSING ===================")
        logger.info(f"[AUTO-RESPONSE] Parameters:")
        logger.info(f"[AUTO-RESPONSE] - Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {phone_opt_in}")
        logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
        
        # Determine scenario name and reason for SMS
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
    
    if old_process_auto in content:
        content = content.replace(old_process_auto, new_process_auto)
        changes_made.append("✅ Enhanced _process_auto_response logging")
    
    # 5. Покращуємо логування в _cancel_no_phone_tasks
    old_cancel = '''    def _cancel_no_phone_tasks(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_no_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Looking for pending tasks with: phone_opt_in=False, phone_available=False, active=True")'''
    
    new_cancel = '''    def _cancel_no_phone_tasks(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_no_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] =================== TASK CANCELLATION ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] TARGET: Tasks with phone_opt_in=False, phone_available=False, active=True")
        
        # Show all active tasks first
        all_active = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📊 ALL ACTIVE TASKS BEFORE CANCELLATION:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {all_active.count()}")
        
        for task in all_active:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}, active={task.active}")
            logger.info(f"[AUTO-RESPONSE]   Text: '{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] 🔍 FILTERING FOR CANCELLATION TARGET:")'''
    
    if old_cancel in content:
        content = content.replace(old_cancel, new_cancel)
        changes_made.append("✅ Enhanced _cancel_no_phone_tasks logging")
    
    # 6. Покращуємо логування в _cancel_pre_phone_tasks
    old_cancel_pre = '''    def _cancel_pre_phone_tasks(self, lead_id: str, reason: str | None = None):
        """Cancel all pre-phone tasks including phone opt-in tasks."""
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_pre_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Looking for pending tasks with: (phone_available=False OR phone_opt_in=True) AND active=True")'''
    
    new_cancel_pre = '''    def _cancel_pre_phone_tasks(self, lead_id: str, reason: str | None = None):
        """Cancel all pre-phone tasks including phone opt-in tasks."""
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_pre_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] =================== PRE-PHONE TASK CANCELLATION ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] TARGET: Tasks with (phone_available=False OR phone_opt_in=True) AND active=True")
        
        # Show all active tasks first
        all_active = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📊 ALL ACTIVE TASKS BEFORE PRE-PHONE CANCELLATION:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {all_active.count()}")
        
        for task in all_active:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}, active={task.active}")
            logger.info(f"[AUTO-RESPONSE]   Text: '{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] 🔍 FILTERING FOR PRE-PHONE CANCELLATION TARGET:")'''
    
    if old_cancel_pre in content:
        content = content.replace(old_cancel_pre, new_cancel_pre)
        changes_made.append("✅ Enhanced _cancel_pre_phone_tasks logging")
    
    # Записуємо оновлений файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return changes_made

if __name__ == "__main__":
    changes = add_detailed_logging()
    
    if changes:
        print("🎉 ДЕТАЛЬНЕ ЛОГУВАННЯ ДОДАНО УСПІШНО!")
        print("=" * 50)
        for change in changes:
            print(change)
        
        print("\n📋 ЩО ТЕПЕР БУДЕ ЛОГУВАТИСЯ:")
        print("✅ Визначення сценарію в handle_new_lead")
        print("✅ Аналіз існуючих завдань перед обробкою")
        print("✅ Детальна інформація про кожне завдання")
        print("✅ Причини скасування завдань")
        print("✅ Фінальний стан завдань після обробки")
        print("✅ Чіткі мітки для кожного сценарію")
        
        print("\n🔍 ТЕПЕР ВИ ЗМОЖЕТЕ БАЧИТИ:")
        print("• Який сценарій обрано (📱 Phone Opt-in / 📞 Phone Available / 💬 No Phone)")
        print("• Які завдання існують до обробки")
        print("• Які завдання скасовуються і чому")
        print("• Які завдання створюються")
        print("• Фінальний стан усіх завдань")
    else:
        print("❌ Не вдалося додати логування - код можливо вже змінений")
