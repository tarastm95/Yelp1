from __future__ import annotations

import os
import logging
from datetime import datetime
from twilio.rest import Client
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_sms(
    to: str, 
    body: str, 
    lead_id: str | None = None, 
    business_id: str | None = None, 
    purpose: str = ""
) -> str:
    """Send an SMS using Twilio and return the message SID."""
    logger.info(f"[TWILIO] 📱 STARTING send_sms function")
    logger.info(f"[TWILIO] Parameters:")
    logger.info(f"[TWILIO] - To: {to}")
    logger.info(f"[TWILIO] - Body: {body[:100]}..." + ("" if len(body) <= 100 else " (truncated)"))
    logger.info(f"[TWILIO] - Body length: {len(body)} characters")
    logger.info(f"[TWILIO] - Lead ID: {lead_id or 'None'}")
    logger.info(f"[TWILIO] - Business ID: {business_id or 'None'}")
    logger.info(f"[TWILIO] - Purpose: {purpose or 'None'}")
    
    # Step 1: Get Twilio credentials from environment
    logger.info(f"[TWILIO] 🔐 STEP 1: Loading Twilio credentials from environment")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    logger.info(f"[TWILIO] Credential check:")
    logger.info(f"[TWILIO] - TWILIO_ACCOUNT_SID: {'✓ SET' if account_sid else '❌ MISSING'}")
    logger.info(f"[TWILIO] - TWILIO_AUTH_TOKEN: {'✓ SET' if auth_token else '❌ MISSING'}")
    logger.info(f"[TWILIO] - TWILIO_PHONE_NUMBER: {'✓ SET' if from_number else '❌ MISSING'}")
    
    if account_sid:
        logger.debug(f"[TWILIO] Account SID: {account_sid[:10]}...")
    if from_number:
        logger.info(f"[TWILIO] From phone number: {from_number}")

    # Step 2: Validate credentials
    logger.info(f"[TWILIO] ✅ STEP 2: Validating credentials")
    if not all([account_sid, auth_token, from_number]):
        missing_vars = []
        if not account_sid:
            missing_vars.append("TWILIO_ACCOUNT_SID")
        if not auth_token:
            missing_vars.append("TWILIO_AUTH_TOKEN")
        if not from_number:
            missing_vars.append("TWILIO_PHONE_NUMBER")
            
        logger.error(f"[TWILIO] ❌ CREDENTIAL ERROR: Missing environment variables: {', '.join(missing_vars)}")
        logger.error(f"[TWILIO] Cannot proceed without complete Twilio configuration")
        raise RuntimeError("Twilio credentials are not fully configured")
        
    logger.info(f"[TWILIO] ✅ All credentials present - proceeding with SMS")

    # Step 3: Initialize Twilio client
    logger.info(f"[TWILIO] 🔧 STEP 3: Initializing Twilio client")
    try:
        client = Client(account_sid, auth_token)
        logger.info(f"[TWILIO] ✅ Twilio client initialized successfully")
        logger.debug(f"[TWILIO] Client account SID: {client.account_sid}")
    except Exception as e:
        logger.error(f"[TWILIO] ❌ CLIENT INITIALIZATION ERROR: {e}")
        logger.exception(f"[TWILIO] Failed to create Twilio client")
        raise

    # Step 4: Send SMS message
    logger.info(f"[TWILIO] 📤 STEP 4: Sending SMS message")
    logger.info(f"[TWILIO] Message details:")
    logger.info(f"[TWILIO] - From: {from_number}")
    logger.info(f"[TWILIO] - To: {to}")
    logger.info(f"[TWILIO] - Body preview: {body[:50]}...")
    
    try:
        logger.info(f"[TWILIO] 🚀 Calling Twilio API...")
        message = client.messages.create(from_=from_number, to=to, body=body)
        
        logger.info(f"[TWILIO] ✅ SMS sent successfully!")
        logger.info(f"[TWILIO] Response details:")
        logger.info(f"[TWILIO] - Message SID: {message.sid}")
        logger.info(f"[TWILIO] - Status: {getattr(message, 'status', 'Unknown')}")
        logger.info(f"[TWILIO] - Direction: {getattr(message, 'direction', 'Unknown')}")
        logger.info(f"[TWILIO] - Price: {getattr(message, 'price', 'Unknown')}")
        logger.info(f"[TWILIO] - Price unit: {getattr(message, 'price_unit', 'Unknown')}")
        
        # Log using the old format for compatibility
        logger.info("Twilio message sent", extra={"to": to, "sid": message.sid})
        
        # Step 5: Save SMS to database
        logger.info(f"[TWILIO] 💾 STEP 5: Saving SMS log to database")
        try:
            from .models import SMSLog
            
            # Parse Twilio timestamp if available
            twilio_created_at = None
            if hasattr(message, 'date_created') and message.date_created:
                twilio_created_at = message.date_created
            
            # Create SMS log entry
            sms_log = SMSLog.objects.create(
                sid=message.sid,
                to_phone=to,
                from_phone=from_number,
                body=body,
                lead_id=lead_id,
                business_id=business_id,
                purpose=purpose,
                status=getattr(message, 'status', 'sent'),
                price=getattr(message, 'price', None),
                price_unit=getattr(message, 'price_unit', None),
                direction=getattr(message, 'direction', 'outbound-api'),
                twilio_created_at=twilio_created_at,
            )
            
            logger.info(f"[TWILIO] ✅ SMS log saved successfully!")
            logger.info(f"[TWILIO] - SMS Log ID: {sms_log.id}")
            logger.info(f"[TWILIO] - SID: {sms_log.sid}")
            logger.info(f"[TWILIO] - Status: {sms_log.status}")
            logger.info(f"[TWILIO] - Purpose: {sms_log.purpose}")
            
        except Exception as db_error:
            # Don't fail the SMS sending if database save fails
            logger.error(f"[TWILIO] ⚠️ DATABASE SAVE ERROR: {db_error}")
            logger.error(f"[TWILIO] SMS was sent successfully but failed to save to database")
            logger.exception(f"[TWILIO] Database save exception details")
        
        logger.info(f"[TWILIO] 🎉 send_sms COMPLETED - returning SID: {message.sid}")
        return message.sid
        
    except Exception as e:
        logger.error(f"[TWILIO] ❌ SMS SENDING ERROR: {e}")
        logger.error(f"[TWILIO] Error type: {type(e).__name__}")
        logger.error(f"[TWILIO] Error message: {str(e)}")
        
        # Try to extract more details from Twilio errors
        if hasattr(e, 'msg'):
            logger.error(f"[TWILIO] Twilio error message: {e.msg}")
        if hasattr(e, 'code'):
            logger.error(f"[TWILIO] Twilio error code: {e.code}")
        if hasattr(e, 'status'):
            logger.error(f"[TWILIO] HTTP status: {e.status}")
            
        logger.exception(f"[TWILIO] Exception details for SMS send failure")
        
        # Step 5: Save failed SMS to database
        logger.info(f"[TWILIO] 💾 Saving failed SMS log to database")
        try:
            from .models import SMSLog
            
            # Create failed SMS log entry
            sms_log = SMSLog.objects.create(
                sid=f"FAILED_{timezone.now().timestamp()}",  # Generate unique ID for failed SMS
                to_phone=to,
                from_phone=from_number,
                body=body,
                lead_id=lead_id,
                business_id=business_id,
                purpose=purpose,
                status='failed',
                error_message=str(e),
                direction='outbound-api',
            )
            
            logger.info(f"[TWILIO] ✅ Failed SMS log saved!")
            logger.info(f"[TWILIO] - SMS Log ID: {sms_log.id}")
            logger.info(f"[TWILIO] - Error: {sms_log.error_message}")
            
        except Exception as db_error:
            logger.error(f"[TWILIO] ⚠️ Failed to save failed SMS to database: {db_error}")
            logger.exception(f"[TWILIO] Database save exception for failed SMS")
        
        raise
