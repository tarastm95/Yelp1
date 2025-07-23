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
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to = serializer.validated_data["to"]
        body = serializer.validated_data["body"]
        logger.info("Sending SMS via Twilio", extra={"to": to, "body": body})
        sid = send_sms(to, body)
        logger.info("SMS sent", extra={"to": to, "sid": sid})
        return Response({"sid": sid}, status=status.HTTP_200_OK)

