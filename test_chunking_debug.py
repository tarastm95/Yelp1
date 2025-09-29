#!/usr/bin/env python3
"""
🧪 Test Script для діагностики chunking проблем
"""

# Симулюємо ваш PDF content
sample_pdf_text = """Sample Replies – Rafael and Iris
Roofing
Example #1
Inquiry information:
Name: Beau S.
Roof replacement
San Fernando Valley, CA 91331
Lead created: 8/27/2025, 4:02 PM
What kind of roof covering do you want?
Asphalt shingles
How many stories tall is your building?
1 story
When do you require this service?
As soon as possible
In what location do you need the service?
91331
Response:
Good afternoon Beau,
Thanks for reaching out! I see you're looking to replace your 1-story roof with asphalt shingles
as soon as possible. We'd be glad to help with that. Do you happen to know the approximate
square footage of your roof, or would you like us to come out and take a look to measure?
We could set up a time to meet — we're available Monday to Friday between 9am and 6pm, but
if another time works better for you, just let me know.
Talk soon,
Norma"""

print("🧪 ТЕСТ CHUNKING СИСТЕМИ")
print("=" * 50)

print(f"📄 Sample PDF text ({len(sample_pdf_text)} chars):")
print(sample_pdf_text[:200] + "...")

print(f"\n🔍 QUICK ANALYSIS:")
text_lower = sample_pdf_text.lower()

markers = {
    'inquiry_information': 'inquiry information:' in text_lower,
    'response_marker': 'response:' in text_lower,
    'name_marker': 'name:' in text_lower,
    'good_afternoon': 'good afternoon' in text_lower,
    'thanks_reaching': 'thanks for reaching' in text_lower,
    'talk_soon': 'talk soon' in text_lower,
    'norma': 'norma' in text_lower
}

for marker, found in markers.items():
    status = "✅" if found else "❌"
    print(f"  {status} {marker}: {found}")

print(f"\n🧩 MANUAL CHUNKING TEST:")

# Пробуємо розділити manually
import re

# Test patterns
patterns = [
    r'Example\s*#\d+',
    r'Inquiry information:',
    r'Response:',
]

sections = [sample_pdf_text]

for pattern in patterns:
    print(f"\n🔄 Applying pattern: {pattern}")
    new_sections = []
    for section in sections:
        parts = re.split(f'({pattern})', section, flags=re.IGNORECASE)
        print(f"  Split into {len(parts)} parts")
        for i, part in enumerate(parts):
            if part.strip():
                print(f"    Part {i+1}: {len(part)} chars - '{part[:50]}...'")
                new_sections.append(part.strip())
    sections = new_sections

print(f"\n📋 FINAL SECTIONS: {len(sections)}")
for i, section in enumerate(sections):
    print(f"\nSection {i+1} ({len(section)} chars):")
    print(f"  Content: {section[:100]}...")
    
    # Що б це було класифіковано як?
    section_lower = section.lower()
    if 'response:' in section_lower:
        predicted = 'response (explicit marker)'
    elif 'inquiry information:' in section_lower:
        predicted = 'inquiry (explicit marker)'
    elif any(phrase in section_lower for phrase in ['good afternoon', 'thanks for reaching', 'talk soon']):
        predicted = 'response (business phrases)'
    elif any(phrase in section_lower for phrase in ['name:', 'lead created:']):
        predicted = 'inquiry (customer data)'
    else:
        predicted = 'general (no matches)'
    
    print(f"  Would classify as: {predicted}")

print(f"\n🎯 RECOMMENDED ACTION:")
print(f"If you see sections that should be 'response' but are classified as 'general',")
print(f"the problem is in the classification logic, not the PDF parsing.")
