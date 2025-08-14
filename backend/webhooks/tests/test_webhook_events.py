from django.test import TestCase
from rest_framework.test import APIRequestFactory
from unittest.mock import patch
from datetime import timedelta

from webhooks.webhook_views import WebhookView
from webhooks.models import (
    ProcessedLead,
    LeadPendingTask,
    YelpBusiness,
    AutoResponseSettings,
    LeadDetail,
    LeadEvent,
)
from webhooks.tasks import send_follow_up


class WebhookEventProcessingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WebhookView.as_view()
        self.lead_id = "l1"
        self.biz_id = "b1"
        # mark lead as already processed
        self.proc = ProcessedLead.objects.create(business_id=self.biz_id, lead_id=self.lead_id)
        LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            task_id="t1",
            text="t",
            phone_opt_in=False,
        )

    def _post(self):
        payload = {"data": {"id": self.biz_id, "updates": [{"lead_id": self.lead_id, "event_type": "NEW_LEAD"}]}}
        request = self.factory.post("/webhook/", {"payload": payload}, format="json")
        response = self.view(request)
        return response

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_initial_event_does_not_cancel_tasks(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get,
    ):
        event_time = (self.proc.processed_at - timedelta(seconds=5)).isoformat()
        mock_get.return_value = type("R", (), {"status_code": 200, "json": lambda self: {"events": [
            {
                "id": "e1",
                "event_type": "NEW_EVENT",
                "user_type": "CONSUMER",
                "user_id": "u",
                "user_display_name": "d",
                "event_content": {"text": "hi"},
                "cursor": "c1",
                "time_created": event_time,
            }
        ]}})()
        self._post()
        mock_cancel.assert_called_once()

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_late_event_without_phone_cancels_tasks(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get,
    ):
        event_time = (self.proc.processed_at + timedelta(minutes=1)).isoformat()
        mock_get.return_value = type("R", (), {"status_code": 200, "json": lambda self: {"events": [
            {
                "id": "e2",
                "event_type": "NEW_EVENT",
                "user_type": "CONSUMER",
                "user_id": "u",
                "user_display_name": "d",
                "event_content": {"text": "hello"},
                "cursor": "c2",
                "time_created": event_time,
            }
        ]}})()
        self._post()
        mock_cancel.assert_called_once()

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_old_event_with_phone_ignored(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get,
    ):
        event_time = (self.proc.processed_at - timedelta(seconds=5)).isoformat()
        mock_get.return_value = type(
            "R",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {
                            "id": "e3",
                            "event_type": "NEW_EVENT",
                            "user_type": "CONSUMER",
                            "user_id": "u",
                            "user_display_name": "d",
                            "event_content": {"text": "+380111111111"},
                            "cursor": "c3",
                            "time_created": event_time,
                        }
                    ]
                },
            },
        )()
        self._post()
        mock_phone_available.assert_called_once()
        mock_cancel.assert_not_called()

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_biz_event_with_phone_ignored(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get,
    ):
        event_time = (self.proc.processed_at + timedelta(minutes=2)).isoformat()
        mock_get.return_value = type(
            "R",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {
                            "id": "e4",
                            "event_type": "NEW_EVENT",
                            "user_type": "BIZ",
                            "user_id": "u",
                            "user_display_name": "d",
                            "event_content": {"text": "+123"},
                            "cursor": "c4",
                            "time_created": event_time,
                        }
                    ]
                },
            },
        )()
        self._post()
        mock_phone_available.assert_not_called()
        mock_cancel.assert_not_called()

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_all_tasks")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_biz_event_not_from_backend_cancels(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel_no_phone,
        mock_cancel_all,
        mock_get,
    ):
        event_time = (self.proc.processed_at + timedelta(minutes=2)).isoformat()
        mock_get.return_value = type(
            "R",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {
                            "id": "e5",
                            "event_type": "NEW_EVENT",
                            "user_type": "BIZ",
                            "user_id": "u",
                            "user_display_name": "d",
                            "event_content": {"text": "manual"},
                            "cursor": "c5",
                            "time_created": event_time,
                        }
                    ]
                },
            },
        )()
        self._post()
        mock_cancel_all.assert_called_once()
        mock_phone_available.assert_not_called()


class LeadIdVerificationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WebhookView.as_view()
        self.lead_id = "n1"
        self.biz_id = "b1"

    def _post(self):
        payload = {
            "data": {
                "id": self.biz_id,
                "updates": [{"lead_id": self.lead_id, "event_type": "NEW_EVENT"}],
            }
        }
        request = self.factory.post("/webhook/", {"payload": payload}, format="json")
        return self.view(request)

    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_mark_new_lead_when_not_listed(
        self,
        mock_new_lead,
        mock_lead_token,
        mock_business_token,
        mock_get
    ):
        events_resp = type(
            "E",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {
                            "id": "e0",
                            "user_type": "CONSUMER",
                        }
                    ]
                },
            },
        )()
        mock_get.return_value = events_resp
        self._post()
        mock_new_lead.assert_called_once_with(self.lead_id)

    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_mark_new_lead_with_phone_opt_in(
        self,
        mock_new_lead,
        mock_lead_token,
        mock_business_token,
        mock_get
    ):
        events_resp = type(
            "E",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {"id": "e0", "user_type": "CONSUMER"},
                        {"id": "e1", "event_type": "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT"},
                    ]
                },
            },
        )()
        mock_get.return_value = events_resp
        self._post()
        mock_new_lead.assert_called_once_with(self.lead_id)

    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_mark_new_lead_with_attachment_grouping(
        self,
        mock_new_lead,
        mock_lead_token,
        mock_business_token,
        mock_get
    ):
        events_resp = type(
            "E",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {"id": "e0", "user_type": "CONSUMER"},
                        {"id": "e1", "event_type": "ATTACHMENT_GROUPING"},
                    ]
                },
            },
        )()
        mock_get.return_value = events_resp
        self._post()
        mock_new_lead.assert_called_once_with(self.lead_id)

    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_mark_new_lead_with_blank_event_type(
        self,
        mock_new_lead,
        mock_lead_token,
        mock_business_token,
        mock_get
    ):
        events_resp = type(
            "E",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {"id": "e0", "user_type": "CONSUMER"},
                        {"id": "e1", "event_type": ""},
                    ]
                },
            },
        )()
        mock_get.return_value = events_resp
        self._post()
        mock_new_lead.assert_called_once_with(self.lead_id)

    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_existing_lead_not_marked(
        self,
        mock_new_lead,
        mock_lead_token,
        mock_business_token,
        mock_get
    ):
        ProcessedLead.objects.create(business_id=self.biz_id, lead_id=self.lead_id)
        events_resp = type(
            "E",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "events": [
                        {
                            "id": "e0",
                            "user_type": "CONSUMER",
                        }
                    ]
                },
            },
        )()
        mock_get.return_value = events_resp
        self._post()
        mock_new_lead.assert_not_called()
        self.assertFalse(ProcessedLead.objects.filter(lead_id=self.lead_id).exists())

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_phone_in_additional_info_triggers_phone_available(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get
    ):
        events_resp = type(
            "E",
            (),
            {"status_code": 200, "json": lambda self: {"events": []}},
        )()
        mock_get.side_effect = [events_resp, events_resp]
        self._post()
        mock_phone_available.assert_called_once()
        mock_cancel.assert_not_called()


class AutoResponseDisabledTests(TestCase):
    def setUp(self):
        self.view = WebhookView()
        self.lead_id = "d1"
        self.biz = YelpBusiness.objects.create(business_id="b2", name="biz")
        ProcessedLead.objects.create(business_id=self.biz.business_id, lead_id=self.lead_id)
        AutoResponseSettings.objects.create(
            business=self.biz,
            phone_opt_in=False,
            phone_available=False,
            enabled=False,
        )

    @patch("webhooks.webhook_views.send_follow_up.apply_async")
    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    def test_lead_detail_saved_when_disabled(
        self,
        mock_token,
        mock_get,
        mock_follow_up,
    ):
        detail_resp = {
            "business_id": self.biz.business_id,
            "conversation_id": "c",
            "temporary_email_address": "t@example.com",
            "temporary_email_address_expiry": "2023-01-01T00:00:00Z",
            "time_created": "2023-01-01T00:00:00Z",
            "user": {"display_name": "John"},
            "project": {},
        }
        events_resp = {"events": []}
        mock_get.side_effect = [
            type("R", (), {"status_code": 200, "json": lambda self: detail_resp})(),
            type("R", (), {"status_code": 200, "json": lambda self: events_resp})(),
        ]

        self.view._process_auto_response(self.lead_id, phone_opt_in=False, phone_available=False)

        self.assertTrue(LeadDetail.objects.filter(lead_id=self.lead_id).exists())
        mock_follow_up.assert_not_called()


class SendFollowUpTests(TestCase):
    def test_empty_message_skipped(self):
        with self.assertLogs('webhooks.tasks', level='WARNING') as cm:
            send_follow_up.__wrapped__('lead-x', '   ')
        self.assertEqual(LeadEvent.objects.count(), 0)
        self.assertIn('Empty follow-up text', cm.output[0])

    def test_event_marked_from_backend(self):
        send_follow_up.__wrapped__('lead-y', 'hello', business_id='b1')
        ev = LeadEvent.objects.get(lead_id='lead-y')
        self.assertTrue(ev.from_backend)


class BusinessTokenErrorTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WebhookView.as_view()
        self.lead_id = "err1"
        self.biz_id = "biz1"

    def _post(self):
        payload = {
            "data": {
                "id": self.biz_id,
                "updates": [{"lead_id": self.lead_id, "event_type": "NEW_LEAD"}],
            }
        }
        request = self.factory.post("/webhook/", {"payload": payload}, format="json")
        return self.view(request)

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch(
        "webhooks.webhook_views.get_valid_business_token",
        side_effect=ValueError("no token"),
    )
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_valueerror_skips_fetching_events(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get,
    ):
        resp = self._post()
        mock_get.assert_not_called()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(LeadEvent.objects.count(), 0)


class AutoResponse404DetailTests(TestCase):
    def setUp(self):
        self.view = WebhookView()
        self.lead_id = "l404"
        self.biz = YelpBusiness.objects.create(business_id="b404", name="biz")
        ProcessedLead.objects.create(business_id=self.biz.business_id, lead_id=self.lead_id)
        AutoResponseSettings.objects.create(
            business=self.biz,
            phone_opt_in=False,
            phone_available=False,
            enabled=True,
        )

    @patch("webhooks.twilio_utils.send_sms", return_value="sid")
    @patch("webhooks.webhook_views.send_follow_up.apply_async")
    @patch("webhooks.webhook_views.requests.get")
    @patch("webhooks.webhook_views.get_valid_business_token", return_value="tok")
    def test_detail_404_still_schedules_auto_response(
        self,
        mock_token,
        mock_get,
        mock_follow_up,
        mock_sms,
    ):
        events_resp = {"events": []}
        mock_get.side_effect = [
            type("R", (), {"status_code": 404, "text": "not found"})(),
            type("R", (), {"status_code": 200, "json": lambda self: events_resp})(),
        ]

        self.view._process_auto_response(
            self.lead_id, phone_opt_in=False, phone_available=False
        )

        mock_follow_up.assert_called_once()
        self.assertEqual(mock_get.call_count, 2)

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch(
        "webhooks.webhook_views.get_valid_business_token",
        side_effect=RuntimeError("boom"),
    )
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_exception_skips_fetching_events(
        self,
        mock_lead_token,
        mock_business_token,
        mock_new_lead,
        mock_phone_available,
        mock_cancel,
        mock_get,
    ):
        resp = self._post()
        mock_get.assert_not_called()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(LeadEvent.objects.count(), 0)

