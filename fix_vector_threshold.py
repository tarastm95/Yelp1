import re

# Read the current models.py
with open('backend/webhooks/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the default value from 0.6 to 0.4
updated_content = re.sub(
    r'(vector_similarity_threshold = models\.FloatField\(\s*default=)0\.6',
    r'\g<1>0.4',
    content
)

# Write back to the file
with open('backend/webhooks/models.py', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("✅ Updated vector_similarity_threshold default from 0.6 to 0.4")
