from django.test import TestCase
from config.celery import app
from webhooks.models import LeadPendingTask
import uuid


class CelerySignalTests(TestCase):
    def test_task_start_marks_pending_inactive(self):
        @app.task
        def dummy():
            return "ok"

        app.conf.task_always_eager = True
        tid = str(uuid.uuid4())
        LeadPendingTask.objects.create(lead_id="l", task_id=tid, phone_opt_in=False)

        dummy.apply(task_id=tid)

        pending = LeadPendingTask.objects.get(task_id=tid)
        self.assertFalse(pending.active)
