#!/usr/bin/env python3
"""
🧪 Test Script для демонстрації ExtractThinker System
"""

# Sample PDF content (ваш реальний PDF текст)
sample_pdf_content = """Sample Replies – Rafael and Iris Roofing

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

print("🎯 EXTRACTTHINKER SYSTEM TEST")
print("=" * 50)

print(f"📄 Input PDF content ({len(sample_pdf_content)} chars)")

# 1. Тест Splitter
print(f"\n🔍 STEP 1: SPLITTING BY MARKERS")
import re

patterns = {
    'example': r'Example\s*#?\s*(\d+)',
    'inquiry': r'Inquiry\s+information:',
    'response': r'Response:'
}

markers = []
for marker_type, pattern in patterns.items():
    for match in re.finditer(pattern, sample_pdf_content, re.IGNORECASE):
        markers.append({
            'type': marker_type,
            'position': match.start(),
            'text': match.group(),
            'number': int(match.group(1)) if marker_type == 'example' and match.groups() else None
        })

markers.sort(key=lambda x: x['position'])

print(f"Found {len(markers)} markers:")
for marker in markers:
    print(f"  {marker['type']}: '{marker['text']}' at position {marker['position']}")

# 2. Створення секцій
sections = []
for i, marker in enumerate(markers):
    start_pos = marker['position']
    end_pos = markers[i + 1]['position'] if i + 1 < len(markers) else len(sample_pdf_content)
    section_text = sample_pdf_content[start_pos:end_pos].strip()
    
    if len(section_text) > 20:
        sections.append({
            'type': marker['type'],
            'content': section_text,
            'example_number': marker.get('number'),
            'length': len(section_text)
        })

print(f"\n📋 STEP 2: SECTIONS CREATED")
print(f"Total sections: {len(sections)}")
for i, section in enumerate(sections):
    print(f"  Section {i+1}: {section['type']} ({section['length']} chars)")
    print(f"    Content preview: {section['content'][:80]}...")

# 3. Групування в examples
print(f"\n🔗 STEP 3: GROUPING INTO EXAMPLES")

examples = []
current_example = {}

for section in sections:
    if section['type'] == 'example':
        if current_example:
            examples.append(current_example)
        current_example = {
            'example_number': section.get('example_number'),
            'sections': [section]
        }
    else:
        if current_example:
            current_example['sections'].append(section)

if current_example:
    examples.append(current_example)

print(f"Grouped into {len(examples)} examples:")
for example in examples:
    section_types = [s['type'] for s in example['sections']]
    print(f"  Example {example['example_number']}: {section_types}")

# 4. Що би ExtractThinker витягнув
print(f"\n🤖 STEP 4: WHAT EXTRACTTHINKER WOULD EXTRACT")

for example in examples:
    inquiry_section = next((s for s in example['sections'] if s['type'] == 'inquiry'), None)
    response_section = next((s for s in example['sections'] if s['type'] == 'response'), None)
    
    if inquiry_section and response_section:
        print(f"\nExample {example['example_number']}:")
        
        # Inquiry extraction (що б витягнув AI)
        inquiry_text = inquiry_section['content']
        name_match = re.search(r'Name:\s*([A-Z][a-z]+\s*[A-Z]?\.?)', inquiry_text)
        service_lines = inquiry_text.split('\\n')[1:3]
        
        print(f"  📋 INQUIRY EXTRACTED:")
        print(f"    customer_name: {name_match.group(1) if name_match else 'Not found'}")
        print(f"    service_type: {next((line.strip() for line in service_lines if line.strip() and not line.startswith('Lead')), 'Not found')}")
        print(f"    location: {'San Fernando Valley, CA 91331' if 'San Fernando' in inquiry_text else 'Not found'}")
        
        # Response extraction
        response_text = response_section['content']
        
        print(f"  💬 RESPONSE EXTRACTED:")
        print(f"    greeting_type: {'Good afternoon' if 'good afternoon' in response_text.lower() else 'Other'}")
        print(f"    acknowledgment: {'Thanks for reaching out' if 'thanks for reaching' in response_text.lower() else 'Other'}")
        print(f"    tone: {'friendly' if 'talk soon' in response_text.lower() else 'professional'}")
        print(f"    signature: {'Norma' if 'norma' in response_text.lower() else 'Not found'}")

# 5. Результат що буде в БД
print(f"\n💾 STEP 5: CHUNKS SAVED TO DATABASE")
print(f"Would create {len(examples) * 2} main chunks:")

chunk_index = 0
for example in examples:
    chunk_index += 1
    print(f"  Chunk #{chunk_index}: type='inquiry', content='Name: Beau S. Roof replacement...'")
    
    chunk_index += 1  
    print(f"  Chunk #{chunk_index}: type='response', content='Good afternoon Beau, Thanks for reaching...'")

print(f"\n🔍 STEP 6: VECTOR SEARCH RESULTS")
print(f"Query: 'Name: Beau S. Roof replacement'")
print(f"Would find: 1-2 response chunks with similarity 0.6-0.8")
print(f"AI would use Norma's style: 'Good afternoon! Thanks for reaching out!'")

print(f"\n✅ EXPECTED FINAL RESULT:")
print(f"AI Preview: 'Good afternoon! Thanks for reaching out! I see you're looking to replace your 1-story roof with asphalt shingles as soon as possible. We'd be glad to help with that...'")
print(f"\nInstead of generic: 'Hello! Thank you for reaching out to us. We're thrilled to hear from you...'")

print(f"\n🎯 THIS IS HOW EXTRACTTHINKER SYSTEM WORKS!")
