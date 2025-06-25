import os
import logging
from datetime import datetime, timezone as dt_timezone

from celery import Celery
from celery.signals import before_task_publish, task_prerun, task_postrun
from django.db import transaction
from django.utils import timezone
from django.apps import apps

# Fallback UTC constant for older Django versions without timezone.utc
UTC = getattr(timezone, "utc", dt_timezone.utc)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


def get_task_log_model():
    """Return the CeleryTaskLog model when apps are ready."""
    return apps.get_model("webhooks", "CeleryTaskLog")


@before_task_publish.connect
def log_task_schedule(sender=None, headers=None, **kwargs):
    """Log when a task is scheduled to run including timezone."""
    eta = headers.get("eta") if headers else None
    tz = timezone.get_current_timezone()
    task_id = headers.get("id") if headers else None
    args = kwargs.get("body", [])[0] if kwargs.get("body") else None
    kargs = kwargs.get("body", [])[1] if kwargs.get("body") else None
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
        schedule_time = eta_dt
    else:
        now = timezone.localtime(timezone.now(), tz)
        logger.info(
            "[CELERY] %s scheduled for immediate execution at %s",
            sender,
            now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        )
        schedule_time = timezone.now()

    if task_id:
        with transaction.atomic():
            get_task_log_model().objects.update_or_create(
                task_id=task_id,
                defaults={
                    "name": sender,
                    "args": args,
                    "kwargs": kargs,
                    "eta": schedule_time,
                    "status": "SCHEDULED",
                },
            )


@task_prerun.connect
def log_task_start(sender=None, task_id=None, **kwargs):
    """Update start time when task begins."""
    get_task_log_model().objects.filter(task_id=task_id).update(
        started_at=timezone.now(), status="STARTED"
    )


@task_postrun.connect
def log_task_done(sender=None, task_id=None, retval=None, state=None, **kwargs):
    """Update finish time and status when task ends."""
    get_task_log_model().objects.filter(task_id=task_id).update(
        finished_at=timezone.now(), status=state or "SUCCESS", result=str(retval)
    )
