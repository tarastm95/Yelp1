from django.test import TestCase
from unittest.mock import patch, Mock
from requests import HTTPError
from webhooks.tasks import send_follow_up
from config.celery import app
import requests

class TaskErrorHandlingTests(TestCase):
    def test_follow_up_invalid_token_logs(self):
        app.conf.task_always_eager = True
        resp = Mock(spec=requests.Response)
        resp.json.return_value = {"error_description": "token expired"}
        resp.text = "token expired"
        resp.status_code = 403
        http_err = HTTPError(response=resp)
        with patch("webhooks.tasks.get_token_for_lead", return_value="tok"), \
             patch("webhooks.tasks.requests.post", side_effect=http_err):
            with self.assertLogs("webhooks.tasks", level="ERROR") as cm:
                with self.assertRaises(Exception):
                    send_follow_up.apply(args=["l1", "hi"])
        self.assertTrue(
            any("Invalid or expired token for lead=l1" in msg for msg in cm.output)
        )

