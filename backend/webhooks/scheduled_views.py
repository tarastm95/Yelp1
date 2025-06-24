import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics

from .models import LeadScheduledMessage, LeadScheduledMessageHistory
from .serializers import (
    LeadScheduledMessageSerializer,
    LeadScheduledMessageHistorySerializer,
)

logger = logging.getLogger(__name__)


class ScheduledMessageListCreate(generics.ListCreateAPIView):
    serializer_class = LeadScheduledMessageSerializer

    def get_queryset(self):
        return LeadScheduledMessage.objects.filter(lead_id=self.kwargs["lead_id"]) 

    def perform_create(self, serializer):
        interval = serializer.validated_data["interval_minutes"]
        serializer.save(
            lead_id=self.kwargs["lead_id"],
            next_run=timezone.now() + timedelta(minutes=interval),
        )


class ScheduledMessageDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeadScheduledMessageSerializer

    def get_queryset(self):
        return LeadScheduledMessage.objects.filter(lead_id=self.kwargs["lead_id"]) 


class ScheduledMessageHistoryList(generics.ListAPIView):
    serializer_class = LeadScheduledMessageHistorySerializer

    def get_queryset(self):
        return (
            LeadScheduledMessageHistory.objects.filter(
                scheduled__lead_id=self.kwargs["lead_id"]
            ).order_by("-executed_at")
        )
