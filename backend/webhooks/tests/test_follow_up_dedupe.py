from django.test import TestCase
from unittest.mock import patch
from django.utils import timezone
from django.db import IntegrityError

from webhooks.tasks import send_follow_up
from webhooks.models import CeleryTaskLog, LeadEvent
from config.celery import app


class FollowUpDuplicateTests(TestCase):
    def setUp(self):
        app.conf.task_always_eager = True

    def test_duplicate_task_skipped(self):
        lead_id = "l1"
        text = "hi"
        CeleryTaskLog.objects.create(
            task_id="old",
            name="send_follow_up",
            args=[lead_id, text],
            status="SUCCESS",
        )
        with patch("webhooks.tasks._get_lock") as mock_lock, \
             patch("webhooks.tasks.requests.post") as mock_post:
            send_follow_up.apply(args=[lead_id, text])
            mock_lock.assert_not_called()
            mock_post.assert_not_called()

    def test_follow_up_unique_constraint(self):
        lead_id = "l2"
        text = "msg"
        LeadEvent.objects.create(
            event_id="e1",
            lead_id=lead_id,
            event_type="FOLLOW_UP",
            user_type="BUSINESS",
            user_id="b",
            user_display_name="",
            text=text,
            cursor="",
            time_created=timezone.now(),
            raw={},
        )
        with self.assertRaises(IntegrityError):
            LeadEvent.objects.create(
                event_id="e2",
                lead_id=lead_id,
                event_type="FOLLOW_UP",
                user_type="BUSINESS",
                user_id="b",
                user_display_name="",
                text=text,
                cursor="",
                time_created=timezone.now(),
                raw={},
            )

