#!/usr/bin/env python3

# Read file
with open("src/AutoResponseSettings.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Update labels to reflect new logic
old_no_phone_label = 'label="No Phone"'
new_no_phone_label = 'label="No Phone / Customer Reply"'

old_real_phone_label = 'label="Real Phone"'
new_real_phone_label = 'label="Phone Available"'

content = content.replace(old_no_phone_label, new_no_phone_label)
content = content.replace(old_real_phone_label, new_real_phone_label)

# Write back
with open("src/AutoResponseSettings.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Updated tab labels to reflect new logic")
print("📝 'No Phone' → 'No Phone / Customer Reply'") 
print("📝 'Real Phone' → 'Phone Available'")
print("🎯 Labels now clearly show that Phone Opt-In is included in No Phone scenario")
