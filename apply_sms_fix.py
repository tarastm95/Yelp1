#!/usr/bin/env python3
"""
Safe SMS fix application script
Applies changes step by step to fix the New Lead vs Customer Reply SMS issue
"""
import re
import sys

def apply_sms_fix():
    file_path = "backend/webhooks/webhook_views.py"
    
    print("🔧 Reading webhook_views.py...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("📝 Applying changes...")
    
    # CHANGE 1: Function signature - add is_new_lead parameter
    old_signature = """    def _process_auto_response(
        self, lead_id: str, phone_opt_in: bool, phone_available: bool
    ):"""
    
    new_signature = """    def _process_auto_response(
        self, lead_id: str, phone_opt_in: bool, phone_available: bool, is_new_lead: bool = False
    ):"""
    
    if old_signature in content:
        content = content.replace(old_signature, new_signature)
        print("✅ CHANGE 1: Updated function signature")
    else:
        print("⚠️ CHANGE 1: Function signature not found - already changed?")
    
    # CHANGE 2: Add is_new_lead logging
    old_logging = """        logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
        
        # Determine reason for SMS based on scenario"""
    
    new_logging = """        logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
        logger.info(f"[AUTO-RESPONSE] - is_new_lead: {is_new_lead}")
        
        # Determine reason for SMS based on scenario"""
    
    if old_logging in content:
        content = content.replace(old_logging, new_logging)
        print("✅ CHANGE 2: Added is_new_lead logging")
    else:
        print("⚠️ CHANGE 2: Logging section not found - already changed?")
    
    # CHANGE 3: Update reason determination logic
    old_reason_logic = """        # Determine reason for SMS based on scenario
        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        else:
            reason = "Customer Reply" """
    
    new_reason_logic = """        # Determine reason for SMS based on scenario
        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        elif is_new_lead:
            reason = "New Lead"
        else:
            reason = "Customer Reply" """
    
    if old_reason_logic in content:
        content = content.replace(old_reason_logic, new_reason_logic)
        print("✅ CHANGE 3: Updated reason determination logic")
    else:
        print("⚠️ CHANGE 3: Reason logic not found - already changed?")
    
    # CHANGE 4: Update handle_new_lead call
    old_call = """            self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)"""
    new_call = """            self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False, is_new_lead=True)"""
    
    if old_call in content:
        content = content.replace(old_call, new_call)
        print("✅ CHANGE 4: Updated handle_new_lead call")
    else:
        print("⚠️ CHANGE 4: handle_new_lead call not found - already changed?")
    
    # CHANGE 5: Add SMS skip logic for new leads
    old_sms_decision = """            final_sms_decision = should_send_sms and auto_settings.enabled
            logger.info(f"[AUTO-RESPONSE] 📲 SMS PROCESSING FOR SCENARIO '{reason}':")"""
    
    new_sms_decision = """            # Disable SMS for new leads regardless of AutoResponseSettings
            if is_new_lead:
                logger.info(f"[AUTO-RESPONSE] 🚫 SMS DISABLED for New Lead scenario")
                logger.info(f"[AUTO-RESPONSE] - New leads should not trigger SMS notifications")
                final_sms_decision = False
            else:
                final_sms_decision = should_send_sms and auto_settings.enabled
            
            logger.info(f"[AUTO-RESPONSE] 📲 SMS PROCESSING FOR SCENARIO '{reason}':")"""
    
    if old_sms_decision in content:
        content = content.replace(old_sms_decision, new_sms_decision)
        print("✅ CHANGE 5: Added SMS skip logic for new leads")
    else:
        print("⚠️ CHANGE 5: SMS decision logic not found - already changed?")
    
    # Write the updated content
    print("💾 Writing updated file...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🎉 SMS fix applied successfully!")
    print("📋 Summary of changes:")
    print("  1. Added is_new_lead parameter to _process_auto_response")
    print("  2. Added is_new_lead logging")
    print("  3. Updated reason determination logic")
    print("  4. Updated handle_new_lead call with is_new_lead=True")
    print("  5. Added SMS skip logic for new leads")
    print("\n✅ New Lead SMS issue should now be fixed!")

if __name__ == "__main__":
    apply_sms_fix()
