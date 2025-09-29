"""
🎯 Pydantic Contracts для ExtractThinker
Structured extraction of Sample Replies документів
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class CustomerInquiry(BaseModel):
    """📋 Контракт для клієнтських запитів (Inquiry information)"""
    
    customer_name: Optional[str] = Field(
        None, 
        description="Customer's full name (e.g., 'Beau S.', 'Jenny Z', 'Melinda C.')"
    )
    
    service_type: Optional[str] = Field(
        None,
        description="Type of service requested (e.g., 'Roof replacement', 'New roof installation', 'Reroofing')"
    )
    
    location: Optional[str] = Field(
        None,
        description="Service location including city, state, and ZIP code (e.g., 'San Fernando Valley, CA 91331')"
    )
    
    lead_created: Optional[str] = Field(
        None,
        description="When the lead was created (e.g., '8/27/2025, 4:02 PM')"
    )
    
    roof_covering_type: Optional[str] = Field(
        None,
        description="What kind of roof covering the customer wants (e.g., 'Asphalt shingles', 'Concrete tile')"
    )
    
    building_stories: Optional[str] = Field(
        None,
        description="How many stories tall is the building (e.g., '1 story', '3 stories')"
    )
    
    service_urgency: Optional[str] = Field(
        None,
        description="When the customer requires the service (e.g., 'As soon as possible', 'I'm flexible')"
    )
    
    zip_code: Optional[str] = Field(
        None,
        description="ZIP code where service is needed (e.g., '91331', '90266')"
    )
    
    additional_details: Optional[str] = Field(
        None,
        description="Any additional details or specific requirements from the customer"
    )
    
    raw_text: str = Field(
        ...,
        description="Complete original inquiry text as extracted from the document"
    )


class BusinessResponse(BaseModel):
    """💬 Контракт для бізнес відповідей (Response)"""
    
    greeting_type: Optional[str] = Field(
        None,
        description="Type of greeting used (e.g., 'Good afternoon', 'Good morning', 'Hello')"
    )
    
    customer_name_mentioned: Optional[str] = Field(
        None,
        description="Customer name mentioned in the response (e.g., 'Beau', 'Jenny', 'Melinda')"
    )
    
    acknowledgment_phrase: Optional[str] = Field(
        None,
        description="How the business acknowledges the request (e.g., 'Thanks for reaching out', 'Thank you for')"
    )
    
    service_acknowledgment: Optional[str] = Field(
        None,
        description="How the business acknowledges the specific service request"
    )
    
    questions_asked: Optional[List[str]] = Field(
        default_factory=list,
        description="Questions the business asks the customer"
    )
    
    availability_mention: Optional[str] = Field(
        None,
        description="Business hours or availability mentioned (e.g., 'Monday to Friday between 9am and 6pm')"
    )
    
    next_steps: Optional[str] = Field(
        None,
        description="Proposed next steps or actions (e.g., 'set up a time to meet', 'come out and take a look')"
    )
    
    closing_phrase: Optional[str] = Field(
        None,
        description="How the response ends (e.g., 'Talk soon', 'Let me know', 'Looking forward')"
    )
    
    signature: Optional[str] = Field(
        None,
        description="Person who signed the response (e.g., 'Norma')"
    )
    
    tone: Optional[str] = Field(
        None,
        description="Overall tone of the response (friendly, professional, casual, formal)"
    )
    
    raw_text: str = Field(
        ...,
        description="Complete original response text as extracted from the document"
    )


class SampleReplyExample(BaseModel):
    """📄 Повний приклад Sample Reply (Inquiry + Response пара)"""
    
    example_number: Optional[int] = Field(
        None,
        description="Example number from the document (e.g., 1, 2, 3)"
    )
    
    inquiry: CustomerInquiry = Field(
        ...,
        description="Structured customer inquiry data"
    )
    
    response: BusinessResponse = Field(
        ...,
        description="Structured business response data"
    )
    
    context_match_score: Optional[float] = Field(
        None,
        description="How well the inquiry and response match contextually (0.0 to 1.0)"
    )


class SampleRepliesDocument(BaseModel):
    """📚 Повний Sample Replies документ"""
    
    document_title: Optional[str] = Field(
        None,
        description="Title of the document (e.g., 'Sample Replies – Rafael and Iris Roofing')"
    )
    
    business_name: Optional[str] = Field(
        None,
        description="Name of the business from the document"
    )
    
    examples: List[SampleReplyExample] = Field(
        default_factory=list,
        description="List of all inquiry/response examples found in the document"
    )
    
    total_examples: int = Field(
        0,
        description="Total number of examples found"
    )
    
    extraction_quality: Optional[str] = Field(
        None,
        description="Quality of extraction (excellent, good, fair, poor)"
    )
    
    raw_document_text: str = Field(
        ...,
        description="Complete original document text"
    )
