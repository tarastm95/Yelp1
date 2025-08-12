#!/usr/bin/env python3
"""
Fix the remaining reason logic that wasn't updated
"""

def fix_reason_logic():
    file_path = "backend/webhooks/webhook_views.py"
    
    print("🔧 Fixing reason logic...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update reason determination logic
    old_reason_block = """        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        else:
            reason = "Customer Reply" """
    
    new_reason_block = """        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        elif is_new_lead:
            reason = "New Lead"
        else:
            reason = "Customer Reply" """
    
    if old_reason_block in content:
        content = content.replace(old_reason_block, new_reason_block)
        print("✅ Updated reason determination logic")
    else:
        print("⚠️ Reason logic not found - checking alternative format...")
        
        # Try without trailing space
        old_reason_block_alt = """        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        else:
            reason = "Customer Reply\""""
        
        new_reason_block_alt = """        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        elif is_new_lead:
            reason = "New Lead"
        else:
            reason = "Customer Reply\""""
        
        if old_reason_block_alt in content:
            content = content.replace(old_reason_block_alt, new_reason_block_alt)
            print("✅ Updated reason determination logic (alternative format)")
        else:
            print("❌ Could not find reason logic block to update")
            return False
    
    # Write the updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Reason logic fix completed!")
    return True

if __name__ == "__main__":
    fix_reason_logic()
