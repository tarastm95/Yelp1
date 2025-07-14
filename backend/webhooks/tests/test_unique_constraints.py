from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from webhooks.models import (
    ScheduledMessage,
    FollowUpTemplate,
    LeadScheduledMessage,
)


class ScheduledMessageUniqueConstraintTests(TestCase):
    def test_unique_lead_template_constraint(self):
        tpl = FollowUpTemplate.objects.create(name='tpl', template='hi')
        ScheduledMessage.objects.create(
            lead_id='l1',
            template=tpl,
            next_run=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            ScheduledMessage.objects.create(
                lead_id='l1',
                template=tpl,
                next_run=timezone.now(),
            )

    def test_lead_scheduled_unique_constraint(self):
        LeadScheduledMessage.objects.create(
            lead_id='l1',
            content='hello',
            interval_minutes=60,
            next_run=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            LeadScheduledMessage.objects.create(
                lead_id='l1',
                content='hello',
                interval_minutes=60,
                next_run=timezone.now(),
            )
