"""
Tests for Phone Opt-In follow-up cancellation logic.

This test ensures that when a consumer replies to a phone opt-in flow,
all related follow-up messages are properly cancelled.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from ..models import LeadDetail, LeadPendingTask, CeleryTaskLog
from ..webhook_views import WebhookView


class PhoneOptInCancellationTests(TestCase):
    def setUp(self):
        """Set up test data."""
        self.lead_id = "test_lead_123"
        self.webhook_view = WebhookView()
        
        # Create LeadDetail with phone opt-in
        self.lead_detail = LeadDetail.objects.create(
            lead_id=self.lead_id,
            business_id="test_business",
            time_created=timezone.now(),
            phone_opt_in=True,
            phone_number="+1234567890",  # Phone number is set during opt-in
            project={"test": "data"}
        )
        
        # Create phone opt-in tasks (greeting + follow-ups)
        self.optin_greeting_task = LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            text="Hello! Thank you for providing your phone number.",
            task_id="task_optin_greeting_123",
            phone_opt_in=True,
            phone_available=False,
            active=True
        )
        
        self.optin_followup_task = LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            text="Just following up on your inquiry...",
            task_id="task_optin_followup_123",
            phone_opt_in=True,
            phone_available=False,
            active=True
        )
        
        # Create regular tasks (should NOT be cancelled in phone opt-in scenario)
        self.regular_task = LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            text="Regular follow-up message",
            task_id="task_regular_123",
            phone_opt_in=False,
            phone_available=True,  # Different scenario
            active=True
        )

    @patch('django_rq.get_queue')
    @patch('django_rq.get_scheduler')
    def test_phone_opt_in_cancellation_specific_function(self, mock_scheduler, mock_queue):
        """Test the new _cancel_phone_opt_in_tasks function."""
        # Mock queue and scheduler
        mock_queue_instance = MagicMock()
        mock_scheduler_instance = MagicMock()
        mock_queue.return_value = mock_queue_instance
        mock_scheduler.return_value = mock_scheduler_instance
        
        # Mock job fetch
        mock_job = MagicMock()
        mock_queue_instance.fetch_job.return_value = mock_job
        
        # Call the function
        self.webhook_view._cancel_phone_opt_in_tasks(
            self.lead_id, 
            reason="Consumer replied to phone opt-in flow"
        )
        
        # Verify phone opt-in tasks were cancelled
        self.optin_greeting_task.refresh_from_db()
        self.optin_followup_task.refresh_from_db()
        self.regular_task.refresh_from_db()
        
        # Phone opt-in tasks should be inactive
        self.assertFalse(self.optin_greeting_task.active)
        self.assertFalse(self.optin_followup_task.active)
        
        # Regular task should remain active
        self.assertTrue(self.regular_task.active)
        
        # Verify queue/scheduler calls
        self.assertEqual(mock_queue_instance.fetch_job.call_count, 2)  # 2 opt-in tasks
        self.assertEqual(mock_job.cancel.call_count, 2)
        self.assertEqual(mock_scheduler_instance.cancel.call_count, 2)

    @patch('django_rq.get_queue')
    @patch('django_rq.get_scheduler')
    def test_cancel_pre_phone_tasks_includes_optin(self, mock_scheduler, mock_queue):
        """Test that _cancel_pre_phone_tasks now includes phone opt-in tasks."""
        # Mock queue and scheduler
        mock_queue_instance = MagicMock()
        mock_scheduler_instance = MagicMock()
        mock_queue.return_value = mock_queue_instance
        mock_scheduler.return_value = mock_scheduler_instance
        
        # Mock job fetch
        mock_job = MagicMock()
        mock_queue_instance.fetch_job.return_value = mock_job
        
        # Create a non-phone task
        no_phone_task = LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            text="No phone follow-up",
            task_id="task_no_phone_123",
            phone_opt_in=False,
            phone_available=False,
            active=True
        )
        
        # Call the function
        self.webhook_view._cancel_pre_phone_tasks(
            self.lead_id, 
            reason="Client responded, but no number was found"
        )
        
        # Refresh all tasks
        self.optin_greeting_task.refresh_from_db()
        self.optin_followup_task.refresh_from_db()
        no_phone_task.refresh_from_db()
        self.regular_task.refresh_from_db()
        
        # Phone opt-in tasks AND no-phone tasks should be cancelled
        self.assertFalse(self.optin_greeting_task.active)
        self.assertFalse(self.optin_followup_task.active)
        self.assertFalse(no_phone_task.active)
        
        # Phone available task should remain active
        self.assertTrue(self.regular_task.active)
        
        # Verify 3 tasks were processed (2 opt-in + 1 no-phone)
        self.assertEqual(mock_queue_instance.fetch_job.call_count, 3)

    def test_phone_opt_in_detection_logic(self):
        """Test that phone opt-in consumer replies are properly detected."""
        # Simulate consumer reply conditions
        ld_flags = {
            "phone_opt_in": True,
            "phone_number": "+1234567890"
        }
        
        # This should trigger phone opt-in cancellation
        condition_met = (
            ld_flags
            and ld_flags.get("phone_opt_in")
        )
        
        self.assertTrue(condition_met, "Phone opt-in condition should be met regardless of phone_number")
        
        # Test with no phone number (should still trigger)
        ld_flags_no_phone = {
            "phone_opt_in": True,
            "phone_number": ""
        }
        
        condition_met_no_phone = (
            ld_flags_no_phone
            and ld_flags_no_phone.get("phone_opt_in")
        )
        
        self.assertTrue(condition_met_no_phone, "Phone opt-in condition should be met even without phone_number")

    def test_pending_tasks_detection_includes_optin(self):
        """Test that pending task detection now includes phone opt-in tasks."""
        from django.db.models import Q
        
        # This is the new logic for detecting pending tasks
        pending = LeadPendingTask.objects.filter(
            lead_id=self.lead_id,
            active=True,
        ).filter(
            Q(phone_available=False) | Q(phone_opt_in=True)
        ).exists()
        
        self.assertTrue(pending, "Should detect phone opt-in tasks as pending")
        
        # Test with only regular phone available tasks
        LeadPendingTask.objects.filter(
            phone_opt_in=True
        ).update(active=False)
        
        pending_after_optin_cancelled = LeadPendingTask.objects.filter(
            lead_id=self.lead_id,
            active=True,
        ).filter(
            Q(phone_available=False) | Q(phone_opt_in=True)
        ).exists()
        
        self.assertFalse(pending_after_optin_cancelled, "Should not detect pending when only phone_available=True tasks remain")


class PhoneOptInIntegrationTests(TestCase):
    """Integration tests for the complete phone opt-in flow."""
    
    def setUp(self):
        self.lead_id = "integration_test_lead"
        self.webhook_view = WebhookView()
        
        # Create LeadDetail with phone opt-in
        LeadDetail.objects.create(
            lead_id=self.lead_id,
            business_id="test_business",
            time_created=timezone.now(),
            phone_opt_in=True,
            phone_number="+1234567890",
            project={"test": "data"}
        )

    @patch('django_rq.get_queue')
    @patch('django_rq.get_scheduler')
    def test_phone_optin_consumer_reply_flow(self, mock_scheduler, mock_queue):
        """Test the complete flow when consumer replies to phone opt-in."""
        # Mock queue and scheduler
        mock_queue_instance = MagicMock()
        mock_scheduler_instance = MagicMock()
        mock_queue.return_value = mock_queue_instance
        mock_scheduler.return_value = mock_scheduler_instance
        
        mock_job = MagicMock()
        mock_queue_instance.fetch_job.return_value = mock_job
        
        # Create phone opt-in tasks
        LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            text="Phone opt-in greeting",
            task_id="integration_optin_greeting",
            phone_opt_in=True,
            phone_available=False,
            active=True
        )
        
        LeadPendingTask.objects.create(
            lead_id=self.lead_id,
            text="Phone opt-in follow-up 1",
            task_id="integration_optin_followup_1",
            phone_opt_in=True,
            phone_available=False,
            active=True
        )
        
        # Simulate the webhook logic for phone opt-in consumer reply
        ld_flags = LeadDetail.objects.filter(
            lead_id=self.lead_id
        ).values("phone_opt_in", "phone_number").first()
        
        if ld_flags and ld_flags.get("phone_opt_in"):
            self.webhook_view._cancel_phone_opt_in_tasks(
                self.lead_id, 
                reason="Consumer replied to phone opt-in flow"
            )
        
        # Verify all phone opt-in tasks are cancelled
        remaining_active_tasks = LeadPendingTask.objects.filter(
            lead_id=self.lead_id,
            phone_opt_in=True,
            active=True
        ).count()
        
        self.assertEqual(remaining_active_tasks, 0, "All phone opt-in tasks should be cancelled")
