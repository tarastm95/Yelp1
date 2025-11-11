"""
Twilio Content API integration for WhatsApp Content Templates.

This module provides functions to interact with Twilio's Content API
to fetch and manage Content Templates for WhatsApp notifications.
"""
import os
import logging
import requests
import re
from typing import List, Dict, Optional
from twilio.rest import Client

logger = logging.getLogger(__name__)


def get_twilio_client() -> Client:
    """Get configured Twilio client."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        raise ValueError("Twilio credentials not configured")
    
    return Client(account_sid, auth_token)


def fetch_content_templates() -> List[Dict]:
    """
    Fetch all Content Templates from Twilio.
    
    GET https://content.twilio.com/v1/Content
    
    Returns:
        List of template dictionaries with keys:
        - sid: Content SID (HX...)
        - friendly_name: Human-readable name
        - types: Content types (text, media, etc.)
        - language: Template language
        - status: Approval status
    """
    logger.info("[TWILIO-CONTENT-API] Fetching Content Templates from Twilio")
    
    try:
        client = get_twilio_client()
        
        # Use Twilio SDK to fetch content
        content_items = client.content.v1.contents.list()
        
        templates = []
        for item in content_items:
            template_data = {
                'sid': item.sid,
                'friendly_name': item.friendly_name,
                'types': item.types,
                'language': item.language,
                'status': getattr(item, 'status', 'unknown'),
                'date_created': item.date_created.isoformat() if item.date_created else None,
                'date_updated': item.date_updated.isoformat() if item.date_updated else None,
            }
            templates.append(template_data)
            
        logger.info(f"[TWILIO-CONTENT-API] ✅ Fetched {len(templates)} Content Templates")
        return templates
        
    except Exception as e:
        logger.error(f"[TWILIO-CONTENT-API] ❌ Error fetching Content Templates: {e}")
        raise


def get_content_template_details(content_sid: str) -> Dict:
    """
    Get specific template details including variables.
    
    Args:
        content_sid: Twilio Content SID (HX...)
        
    Returns:
        Dictionary with template details:
        - sid: Content SID
        - friendly_name: Template name
        - body: Template text with variables {{1}}, {{2}}, etc.
        - variables: List of variable numbers found
        - types: Content types
        - language: Template language
    """
    logger.info(f"[TWILIO-CONTENT-API] Getting details for Content Template: {content_sid}")
    
    try:
        client = get_twilio_client()
        
        # Fetch specific content item
        content_item = client.content.v1.contents(content_sid).fetch()
        
        # Extract template body (text content)
        template_body = ""
        if hasattr(content_item, 'types') and content_item.types:
            # Look for text content in types
            for content_type in content_item.types:
                if hasattr(content_type, 'text') and content_type.text:
                    template_body = content_type.text
                    break
        
        # Extract variables from template body
        variables = extract_template_variables(template_body)
        
        details = {
            'sid': content_item.sid,
            'friendly_name': content_item.friendly_name,
            'body': template_body,
            'variables': variables,
            'types': content_item.types,
            'language': content_item.language,
            'status': getattr(content_item, 'status', 'unknown'),
            'date_created': content_item.date_created.isoformat() if content_item.date_created else None,
            'date_updated': content_item.date_updated.isoformat() if content_item.date_updated else None,
        }
        
        logger.info(f"[TWILIO-CONTENT-API] ✅ Got details for template: {content_item.friendly_name}")
        logger.info(f"[TWILIO-CONTENT-API] - Variables found: {variables}")
        
        return details
        
    except Exception as e:
        logger.error(f"[TWILIO-CONTENT-API] ❌ Error getting template details for {content_sid}: {e}")
        raise


def extract_template_variables(template_body: str) -> List[str]:
    """
    Extract {{1}}, {{2}}, etc. from template body.
    
    Args:
        template_body: Template text with variables
        
    Returns:
        List of variable numbers as strings: ['1', '2', '3', ...]
    """
    if not template_body:
        return []
    
    # Find all {{number}} patterns
    pattern = r'\{\{(\d+)\}\}'
    matches = re.findall(pattern, template_body)
    
    # Remove duplicates and sort
    variables = sorted(list(set(matches)), key=int)
    
    logger.info(f"[TWILIO-CONTENT-API] Extracted variables: {variables}")
    return variables


def get_suggested_variable_mapping(variables: List[str]) -> Dict[str, str]:
    """
    Suggest mapping based on common patterns for Twilio WhatsApp Content Templates.
    
    Args:
        variables: List of variable numbers ['1', '2', '3', ...]
        
    Returns:
        Dictionary mapping variable numbers to field names:
        {'1': 'business_id', '2': 'lead_id', '3': 'business_name', ...}
    """
    # Updated field mappings based on Twilio WhatsApp Content Template requirements
    # This matches the example: "Your business (ID: {{1}}) has registered a new lead (Lead ID: {{3}}) for reason: "{{2}}". Phone: {{4}}."
    field_mapping = {
        '1': 'business_id',      # Business ID
        '2': 'reason',          # Reason for notification
        '3': 'lead_id',         # Lead ID
        '4': 'phone',           # Customer phone number
        '5': 'business_name',   # Business name
        '6': 'customer_name',   # Customer display name
        '7': 'yelp_link',       # Yelp conversation link
        '8': 'timestamp',       # Current date and time
        '9': 'location',        # Business location
        '10': 'service_type',   # Service type
    }
    
    # Create mapping for provided variables
    suggested_mapping = {}
    for var_num in variables:
        if var_num in field_mapping:
            suggested_mapping[var_num] = field_mapping[var_num]
        else:
            # For additional variables, use generic naming
            suggested_mapping[var_num] = f'field_{var_num}'
    
    logger.info(f"[TWILIO-CONTENT-API] Suggested mapping: {suggested_mapping}")
    return suggested_mapping


def create_default_variable_mapping() -> Dict[str, str]:
    """
    Create default variable mapping for Twilio WhatsApp Content Templates.
    
    Returns:
        Dictionary with default mapping for common notification template:
        {'1': 'business_id', '2': 'reason', '3': 'lead_id', '4': 'phone', ...}
    """
    return {
        '1': 'business_id',      # Business ID
        '2': 'reason',          # Reason for notification
        '3': 'lead_id',         # Lead ID
        '4': 'phone',           # Customer phone number
        '5': 'business_name',   # Business name
        '6': 'customer_name',   # Customer display name
        '7': 'yelp_link',       # Yelp conversation link
        '8': 'timestamp',       # Current date and time
    }


def validate_variable_mapping(variable_mapping: Dict[str, str], template_variables: List[str]) -> Dict[str, str]:
    """
    Validate and fix variable mapping to ensure all template variables are mapped.
    
    Args:
        variable_mapping: Current mapping {'1': 'business_id', ...}
        template_variables: Variables found in template ['1', '2', '3', ...]
        
    Returns:
        Validated and completed mapping
    """
    validated_mapping = variable_mapping.copy()
    default_mapping = create_default_variable_mapping()
    
    # Ensure all template variables are mapped
    for var_num in template_variables:
        if var_num not in validated_mapping:
            if var_num in default_mapping:
                validated_mapping[var_num] = default_mapping[var_num]
            else:
                validated_mapping[var_num] = f'field_{var_num}'
    
    logger.info(f"[TWILIO-CONTENT-API] Validated mapping: {validated_mapping}")
    return validated_mapping


def build_content_variables(variable_mapping: Dict[str, str], data: Dict[str, str]) -> Dict[str, str]:
    """
    Build content_variables dict for Twilio API from variable mapping and data.
    
    Args:
        variable_mapping: Maps template variables to field names {'1': 'business_id', '2': 'lead_id'}
        data: Actual data values {'business_id': '12345', 'lead_id': '67890'}
        
    Returns:
        Dictionary for Twilio content_variables: {'1': '12345', '2': '67890'}
    """
    content_variables = {}
    
    # Validate mapping to ensure all required variables are mapped
    template_variables = list(variable_mapping.keys())
    validated_mapping = validate_variable_mapping(variable_mapping, template_variables)
    
    for var_num, field_name in validated_mapping.items():
        value = data.get(field_name, f'[{field_name}]')
        content_variables[var_num] = str(value)
    
    logger.info(f"[TWILIO-CONTENT-API] Built content variables: {content_variables}")
    return content_variables


def validate_content_template(content_sid: str) -> bool:
    """
    Validate that a Content Template exists and is approved for WhatsApp.
    
    Args:
        content_sid: Twilio Content SID to validate
        
    Returns:
        True if template is valid and approved, False otherwise
    """
    try:
        details = get_content_template_details(content_sid)
        
        # Check if template has WhatsApp approval
        if details.get('types'):
            for content_type in details['types']:
                if hasattr(content_type, 'whatsapp') and content_type.whatsapp:
                    whatsapp_status = getattr(content_type.whatsapp, 'status', 'unknown')
                    if whatsapp_status in ['approved', 'pending']:
                        logger.info(f"[TWILIO-CONTENT-API] ✅ Template {content_sid} is valid for WhatsApp")
                        return True
        
        logger.warning(f"[TWILIO-CONTENT-API] ⚠️ Template {content_sid} not approved for WhatsApp")
        return False
        
    except Exception as e:
        logger.error(f"[TWILIO-CONTENT-API] ❌ Error validating template {content_sid}: {e}")
        return False
