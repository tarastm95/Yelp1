import os
import logging
from datetime import datetime, timezone as dt_timezone

from celery import Celery
from celery.signals import before_task_publish
from django.utils import timezone

# Fallback UTC constant for older Django versions without timezone.utc
UTC = getattr(timezone, "utc", dt_timezone.utc)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@before_task_publish.connect
def log_task_schedule(sender=None, headers=None, **kwargs):
    """Log when a task is scheduled to run including timezone."""
    eta = headers.get("eta") if headers else None
    tz = timezone.get_current_timezone()
    if eta:
        try:
            eta_dt = datetime.fromisoformat(eta)
        except ValueError:
            # Fallback if fromisoformat fails
            eta_dt = datetime.strptime(eta, "%Y-%m-%dT%H:%M:%S.%f%z")
        if timezone.is_naive(eta_dt):
            eta_dt = timezone.make_aware(eta_dt, UTC)
        run_time = timezone.localtime(eta_dt, tz)
        logger.info(
            "[CELERY] %s scheduled for %s", sender,
            run_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        )
    else:
        now = timezone.localtime(timezone.now(), tz)
        logger.info(
            "[CELERY] %s scheduled for immediate execution at %s",
            sender,
            now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        )
