from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from webhooks.models import ScheduledMessage, FollowUpTemplate


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
