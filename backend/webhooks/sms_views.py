from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from .serializers import SendSMSSerializer
from .twilio_utils import send_sms

logger = logging.getLogger(__name__)


class SendSMSAPIView(APIView):
    """POST endpoint to send an SMS message via Twilio."""

    def post(self, request, *args, **kwargs):
        logger.info(f"[SMS-API] 📱 RECEIVED SMS API REQUEST")
        logger.info(f"[SMS-API] Request details:")
        logger.info(f"[SMS-API] - Method: {request.method}")
        logger.info(f"[SMS-API] - User: {getattr(request.user, 'username', 'Anonymous')}")
        logger.info(f"[SMS-API] - User authenticated: {request.user.is_authenticated}")
        logger.info(f"[SMS-API] - Content type: {request.content_type}")
        logger.info(f"[SMS-API] - Raw data: {request.data}")
        
        # Step 1: Validate request data
        logger.info(f"[SMS-API] 📝 STEP 1: Validating request data")
        try:
            serializer = SendSMSSerializer(data=request.data)
            logger.info(f"[SMS-API] ✅ Serializer created successfully")
            
            is_valid = serializer.is_valid(raise_exception=True)
            logger.info(f"[SMS-API] ✅ Request data validation passed")
            logger.info(f"[SMS-API] Validation result: {is_valid}")
            
        except Exception as validation_error:
            logger.error(f"[SMS-API] ❌ VALIDATION ERROR: {validation_error}")
            logger.error(f"[SMS-API] Validation errors: {getattr(serializer, 'errors', 'No details')}")
            logger.error(f"[SMS-API] Raw request data: {request.data}")
            logger.exception(f"[SMS-API] Validation exception details")
            raise
            
        # Step 2: Extract validated data
        logger.info(f"[SMS-API] 📋 STEP 2: Extracting validated data")
        to = serializer.validated_data["to"]
        body = serializer.validated_data["body"]
        
        logger.info(f"[SMS-API] Validated data:")
        logger.info(f"[SMS-API] - To: {to}")
        logger.info(f"[SMS-API] - Body: {body[:100]}..." + ("" if len(body) <= 100 else " (truncated)"))
        logger.info(f"[SMS-API] - Body length: {len(body)} characters")
        
        # Step 3: Send SMS
        logger.info(f"[SMS-API] 📤 STEP 3: Sending SMS via Twilio")
        logger.info("Sending SMS via Twilio", extra={"to": to, "body": body})
        
        try:
            logger.info(f"[SMS-API] 🚀 Calling send_sms function...")
            sid = send_sms(to, body)
            logger.info(f"[SMS-API] ✅ SMS sent successfully!")
            logger.info(f"[SMS-API] Twilio response SID: {sid}")
            
            # Log success with extra details
            logger.info("SMS sent", extra={"to": to, "sid": sid})
            
            # Step 4: Prepare response
            logger.info(f"[SMS-API] 📋 STEP 4: Preparing API response")
            response_data = {"sid": sid}
            logger.info(f"[SMS-API] Response data: {response_data}")
            logger.info(f"[SMS-API] Response status: {status.HTTP_200_OK}")
            
            logger.info(f"[SMS-API] 🎉 SMS API REQUEST COMPLETED SUCCESSFULLY")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as sms_error:
            logger.error(f"[SMS-API] ❌ SMS SENDING ERROR: {sms_error}")
            logger.error(f"[SMS-API] Error type: {type(sms_error).__name__}")
            logger.error(f"[SMS-API] Error details: {str(sms_error)}")
            logger.error(f"[SMS-API] Target phone: {to}")
            logger.error(f"[SMS-API] Message: {body[:100]}...")
            logger.exception(f"[SMS-API] SMS sending exception details")
            
            # Re-raise the exception to let DRF handle the error response
            raise

