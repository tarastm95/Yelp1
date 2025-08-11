import os
import django
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from webhooks.models import YelpBusiness, NotificationSetting, LeadDetail, LeadEvent

class CustomerReplySMSTests(TestCase):
    def setUp(self):
        self.biz = YelpBusiness.objects.create(
            business_id="b1",
            name="Biz",
            sms_notifications_enabled=True,
        )
        NotificationSetting.objects.create(
            business=self.biz,
            phone_number="+15555550123",
            message_template="Test {lead_id}"
        )
        self.lead = LeadDetail.objects.create(
            lead_id="l1",
            business_id="b1",
            conversation_id="c1",
            time_created=timezone.now(),
            project={},
        )

    def test_sms_sent_only_after_consumer_event(self):
        with patch("webhooks.signals.send_sms", return_value="sid") as mock_send:
            # immediate save after creation should not trigger SMS
            self.lead.save()
            self.assertEqual(mock_send.call_count, 0)

            # add consumer event and save again -> should trigger SMS
            LeadEvent.objects.create(
                event_id="e1",
                lead_id=self.lead.lead_id,
                event_type="NEW_EVENT",
                user_type="CONSUMER",
                user_id="u1",
                user_display_name="User",
                text="reply",
                cursor="c1",
                time_created=timezone.now(),
                raw={},
            )
            self.lead.save()
            self.assertEqual(mock_send.call_count, 1)
