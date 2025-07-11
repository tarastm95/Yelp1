from django.test import TestCase
from unittest.mock import patch
from django.utils import timezone

from webhooks.models import YelpToken
from webhooks.utils import get_valid_business_token
from webhooks.tasks import refresh_expiring_tokens
from config.celery import app


class TokenRefreshSyncTests(TestCase):
    def setUp(self):
        self.old_refresh = "r1"
        expired = timezone.now() - timezone.timedelta(seconds=5)
        YelpToken.objects.create(
            business_id="b1", access_token="a1", refresh_token=self.old_refresh, expires_at=expired
        )
        YelpToken.objects.create(
            business_id="b2", access_token="a2", refresh_token=self.old_refresh, expires_at=expired
        )

    @patch("webhooks.utils.rotate_refresh_token")
    def test_get_valid_updates_all_shared(self, mock_rotate):
        mock_rotate.return_value = {
            "access_token": "new",
            "refresh_token": "r2",
            "expires_in": 3600,
        }
        token = get_valid_business_token("b1")
        self.assertEqual(token, "new")
        b1 = YelpToken.objects.get(business_id="b1")
        b2 = YelpToken.objects.get(business_id="b2")
        self.assertEqual(b1.access_token, "new")
        self.assertEqual(b2.access_token, "new")
        self.assertEqual(b1.refresh_token, "r2")
        self.assertEqual(b2.refresh_token, "r2")
        self.assertIsNotNone(b2.expires_at)

    @patch("webhooks.tasks.rotate_refresh_token")
    def test_task_refresh_updates_all_shared(self, mock_rotate):
        app.conf.task_always_eager = True
        soon = timezone.now() + timezone.timedelta(seconds=1)
        YelpToken.objects.all().update(expires_at=soon)
        mock_rotate.return_value = {
            "access_token": "task",
            "refresh_token": "r3",
            "expires_in": 7200,
        }
        refresh_expiring_tokens.delay()
        b1 = YelpToken.objects.get(business_id="b1")
        b2 = YelpToken.objects.get(business_id="b2")
        self.assertEqual(b1.access_token, "task")
        self.assertEqual(b2.access_token, "task")
        self.assertEqual(b1.refresh_token, "r3")
        self.assertEqual(b2.refresh_token, "r3")
        self.assertIsNotNone(b1.expires_at)

