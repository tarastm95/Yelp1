import os
import django
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.conf import settings
settings.MIGRATION_MODULES = {"webhooks": None}
django.setup()

from webhooks.models import (
    YelpBusiness,
    ProcessedLead,
    LeadDetail,
    NotificationSetting,
    AutoResponseSettings,
)
from webhooks.webhook_views import WebhookView


class PhoneNumberFoundSMSTests(TestCase):
    def setUp(self):
        self.biz = YelpBusiness.objects.create(business_id="b1", name="Biz")
        NotificationSetting.objects.create(
            business=self.biz,
            phone_number="+15555550123",
            message_template="Test {lead_id}"
        )
        AutoResponseSettings.objects.create(
            business=self.biz,
            phone_available=True,
            enabled=True,
        )
        ProcessedLead.objects.create(business_id="b1", lead_id="l1")
        self.lead = LeadDetail.objects.create(
            lead_id="l1",
            business_id="b1",
            conversation_id="c1",
            time_created=timezone.now(),
            project={},
        )

    def test_twilio_called_once_for_phone_number_found(self):
        view = WebhookView()
        with patch("webhooks.twilio_utils.send_sms", return_value="sid") as mock_send, \
             patch("webhooks.signals.send_sms", new=mock_send), \
             patch("webhooks.webhook_views.get_valid_business_token", side_effect=ValueError("no token")):
            # Update lead with phone number to trigger signal
            self.lead.phone_number = "+1234567890"
            self.lead.phone_in_text = True
            self.lead.phone_sms_sent = False
            self.lead.save(update_fields=["phone_number", "phone_in_text", "phone_sms_sent"])

            # Process auto-response which would attempt to send another SMS
            view._process_auto_response(self.lead.lead_id, phone_opt_in=False, phone_available=True)

            # Ensure send_sms was called only once (by the signal)
            self.assertEqual(mock_send.call_count, 1)
