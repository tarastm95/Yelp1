import re

# Read the current AutoResponseSettings.tsx
with open('frontend/src/AutoResponseSettings.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the default value from 0.6 to 0.4 in state
updated_content = re.sub(
    r'(const \[vectorSimilarityThreshold, setVectorSimilarityThreshold\] = useState\()0\.6(\);)',
    r'\g<1>0.4\g<2>',
    content
)

# Write back to the file
with open('frontend/src/AutoResponseSettings.tsx', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("✅ Updated frontend vectorSimilarityThreshold default from 0.6 to 0.4")
