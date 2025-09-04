#!/usr/bin/env python3

# Read file
with open("webhooks/webhook_views.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix indentation for handle_phone_available
old_line = "        def handle_phone_available(self, lead_id: str, reason: str | None = None):"
new_line = "    def handle_phone_available(self, lead_id: str, reason: str | None = None):"

if old_line in content:
    content = content.replace(old_line, new_line)
    
    # Write back
    with open("webhooks/webhook_views.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ Fixed indentation for handle_phone_available")
else:
    print("❌ Could not find indentation issue to fix")

print("🎉 PHONE OPT-IN MERGE COMPLETED!")
