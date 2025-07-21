from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import SendSMSSerializer
from .twilio_utils import send_sms


class SendSMSAPIView(APIView):
    """POST endpoint to send an SMS message via Twilio."""

    def post(self, request, *args, **kwargs):
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sid = send_sms(serializer.validated_data["to"], serializer.validated_data["body"])
        return Response({"sid": sid}, status=status.HTTP_200_OK)

