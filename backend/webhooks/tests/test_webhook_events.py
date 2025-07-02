from django.test import TestCase
from rest_framework.test import APIRequestFactory
from unittest.mock import patch
from datetime import timedelta

from webhooks.webhook_views import WebhookView
from webhooks.models import ProcessedLead, LeadPendingTask


class WebhookEventProcessingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WebhookView.as_view()
        self.lead_id = "l1"
        self.biz_id = "b1"
        # mark lead as already processed
        self.proc = ProcessedLead.objects.create(business_id=self.biz_id, lead_id=self.lead_id)
        LeadPendingTask.objects.create(lead_id=self.lead_id, task_id="t1", phone_opt_in=False)

    def _post(self):
        payload = {"data": {"id": self.biz_id, "updates": [{"lead_id": self.lead_id, "event_type": "NEW_LEAD"}]}}
        request = self.factory.post("/webhook/", {"payload": payload}, format="json")
        response = self.view(request)
        return response

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_initial_event_does_not_cancel_tasks(
        self, mock_token, mock_new_lead, mock_phone_available, mock_cancel, mock_get
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
        mock_cancel.assert_not_called()

    @patch("webhooks.webhook_views.requests.get")
    @patch.object(WebhookView, "_cancel_no_phone_tasks")
    @patch.object(WebhookView, "handle_phone_available")
    @patch.object(WebhookView, "handle_new_lead")
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_late_event_without_phone_cancels_tasks(
        self, mock_token, mock_new_lead, mock_phone_available, mock_cancel, mock_get
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
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_initial_event_with_phone_triggers_phone_available(
        self, mock_token, mock_new_lead, mock_phone_available, mock_cancel, mock_get
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
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_mark_new_lead_when_not_listed(
        self, mock_new_lead, mock_lead_token, mock_get
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
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    @patch.object(WebhookView, "handle_new_lead")
    def test_existing_lead_not_marked(
        self, mock_new_lead, mock_lead_token, mock_get
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
    @patch("webhooks.webhook_views.get_token_for_lead", return_value="tok")
    def test_phone_in_additional_info_triggers_phone_available(
        self, mock_token, mock_new_lead, mock_phone_available, mock_cancel, mock_get
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

