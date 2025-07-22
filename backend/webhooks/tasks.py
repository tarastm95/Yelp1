# webhooks/tasks.py

import logging
import traceback
import uuid
import functools

import redis
import requests
from requests.exceptions import HTTPError
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django_rq import job
from rq import get_current_job

from .models import (
    LeadDetail,
    YelpToken,
    CeleryTaskLog,
    LeadEvent,
    LeadPendingTask,
)
from django.db import transaction, IntegrityError
from .utils import (
    get_token_for_lead,
    get_valid_business_token,
    rotate_refresh_token,
    update_shared_refresh_token,
    _already_sent,
)

logger = logging.getLogger(__name__)

# Prevent concurrent tasks for the same lead
LOCK_TIMEOUT = 60  # seconds


def logged_job(func):
    """django_rq job decorator that records CeleryTaskLog entries."""

    @job
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        job_obj = get_current_job()
        task_id = job_obj.id if job_obj else str(uuid.uuid4())
        CeleryTaskLog.objects.update_or_create(
            task_id=task_id,
            defaults={
                "name": func.__name__,
                "args": list(args),
                "kwargs": kwargs,
                "eta": getattr(job_obj, "enqueued_at", timezone.now()),
                "started_at": timezone.now(),
                "status": "STARTED",
                "business_id": kwargs.get("business_id"),
            },
        )
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            CeleryTaskLog.objects.filter(task_id=task_id).update(
                finished_at=timezone.now(),
                status="FAILURE",
                result=str(exc),
                traceback=traceback.format_exc(),
            )
            raise
        else:
            CeleryTaskLog.objects.filter(task_id=task_id).update(
                finished_at=timezone.now(),
                status="SUCCESS",
                result="" if result is None else str(result),
            )
            return result

    return wrapper


_redis_client = None


def _get_lock(lock_id: str, timeout: int = LOCK_TIMEOUT, blocking_timeout: int = 5):
    """Return a redis-py lock from the configured cache backend."""
    if hasattr(cache, "lock"):
        return cache.lock(lock_id, timeout=timeout, blocking_timeout=blocking_timeout)

    client = getattr(cache, "client", None)
    if client and hasattr(client, "get_client"):
        redis_client = client.get_client(write=True)
    else:
        global _redis_client
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(settings.REDIS_URL)
        redis_client = _redis_client

    return redis_client.lock(lock_id, timeout=timeout, blocking_timeout=blocking_timeout)


def _extract_yelp_error(resp: requests.Response) -> str:
    """Return readable error text from a Yelp API response."""
    try:
        data = resp.json()
        return (
            data.get("error_description")
            or data.get("description")
            or resp.text
        )
    except Exception:
        return resp.text


@logged_job
def send_follow_up(lead_id: str, text: str, business_id: str | None = None):
    """
    Одноразова відправка follow-up повідомлення без повторних спроб.
    """
    job = get_current_job()
    job_id = job.id if job else None
    if job_id:
        LeadPendingTask.objects.filter(task_id=job_id).update(active=False)
    if _already_sent(lead_id, text, exclude_task_id=job_id):
        logger.info("[FOLLOW-UP] Duplicate follow-up for lead=%s; skipping", lead_id)
        return

    if not text.strip():
        logger.warning("[FOLLOW-UP] Empty follow-up text for lead=%s; skipping", lead_id)
        return

    lock_id = f"lead-lock:{lead_id}"
    try:
        with _get_lock(lock_id, timeout=LOCK_TIMEOUT, blocking_timeout=5):
            if _already_sent(lead_id, text, exclude_task_id=job_id):
                logger.info("[FOLLOW-UP] Duplicate follow-up for lead=%s; skipping", lead_id)
                return
            biz_id = business_id
            token = None
            if biz_id:
                try:
                    token = get_valid_business_token(biz_id)
                except Exception as exc:
                    logger.error(
                        f"[FOLLOW-UP] Error fetching token for business={biz_id}: {exc}"
                    )
            if not token:
                token = get_token_for_lead(lead_id)
            if not token:
                logger.error(f"[FOLLOW-UP] No token available for lead={lead_id}")
                return
            url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {"request_content": text, "request_type": "TEXT"}

            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"[FOLLOW-UP] Sent to lead={lead_id}")

            try:
                with transaction.atomic():
                    LeadEvent.objects.create(
                        event_id=str(uuid.uuid4()),
                        lead_id=lead_id,
                        event_type="FOLLOW_UP",
                        user_type="BUSINESS",
                        user_id=biz_id or "",
                        user_display_name="",
                        text=text,
                        cursor="",
                        time_created=timezone.now(),
                        raw={"task_id": job_id},
                        from_backend=True,
                    )
            except IntegrityError:
                logger.info(
                    "[FOLLOW-UP] LeadEvent already recorded for lead=%s", lead_id
                )
    except Exception as exc:
        if isinstance(exc, HTTPError) and getattr(exc, "response", None) is not None:
            message = _extract_yelp_error(exc.response)
            if exc.response.status_code in (401, 403):
                logger.error(
                    f"[FOLLOW-UP] Invalid or expired token for lead={lead_id}: {message}"
                )
            else:
                logger.error(
                    f"[FOLLOW-UP] HTTP {exc.response.status_code} for lead={lead_id}: {message}"
                )
        elif "acquire" in str(exc):
            logger.info(f"[FOLLOW-UP] Another task running for lead={lead_id}; skipping")
            return
        else:
            logger.error(f"[FOLLOW-UP] Error sending to lead={lead_id}: {exc}")
        raise


@logged_job
def refresh_expiring_tokens():
    """Proactively refresh tokens expiring soon."""
    margin = timezone.now() + timezone.timedelta(minutes=10)
    tokens = YelpToken.objects.filter(expires_at__lte=margin)
    if not tokens:
        logger.debug("[TOKEN REFRESH] No tokens require refresh")
    for tok in tokens:
        logger.info(f"[TOKEN REFRESH] Attempting refresh for {tok.business_id}")
        try:
            old_refresh = tok.refresh_token
            data = rotate_refresh_token(old_refresh)
            update_shared_refresh_token(old_refresh, data)
            tok.access_token = data["access_token"]
            tok.refresh_token = data.get("refresh_token", tok.refresh_token)
            exp = data.get("expires_in")
            if exp:
                tok.expires_at = timezone.now() + timezone.timedelta(seconds=exp)
            tok.save()
            logger.info(
                f"[TOKEN REFRESH] refreshed for {tok.business_id}; expires_at={tok.expires_at}"
            )
        except Exception as exc:
            if isinstance(exc, HTTPError) and exc.response is not None:
                msg = _extract_yelp_error(exc.response)
                logger.error(
                    f"[TOKEN REFRESH] HTTP {exc.response.status_code} for {tok.business_id}: {msg}",
                    exc_info=True,
                )
            else:
                logger.error(
                    f"[TOKEN REFRESH] failed for {tok.business_id}: {exc}",
                    exc_info=True,
                )



@logged_job
def cleanup_celery_logs(days: int = 30):
    """Remove old CeleryTaskLog entries."""
    from django.core.management import call_command

    call_command("cleanup_celery_logs", days=str(days))


# Compatibility helpers -----------------------------------------------------

from datetime import timedelta
from types import SimpleNamespace
from django_rq import get_scheduler


def _apply(func, args=None, kwargs=None):
    args = args or []
    kwargs = kwargs or {}
    task_id = str(uuid.uuid4())
    start = timezone.now()
    CeleryTaskLog.objects.create(
        task_id=task_id,
        name=func.__name__,
        args=list(args),
        kwargs=kwargs,
        eta=start,
        started_at=start,
        status="STARTED",
        business_id=kwargs.get("business_id"),
    )
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        CeleryTaskLog.objects.filter(task_id=task_id).update(
            finished_at=timezone.now(),
            status="FAILURE",
            result=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
    else:
        CeleryTaskLog.objects.filter(task_id=task_id).update(
            finished_at=timezone.now(),
            status="SUCCESS",
            result="" if result is None else str(result),
        )
        return result


def _apply_async(func, args=None, kwargs=None, countdown=0, headers=None):
    args = args or []
    kwargs = kwargs or {}
    if headers and "business_id" in headers:
        kwargs.setdefault("business_id", headers["business_id"])
    eta = timezone.now() + timedelta(seconds=countdown)
    task_id = str(uuid.uuid4())
    if countdown:
        scheduler = get_scheduler("default")
        job = scheduler.enqueue_in(
            timedelta(seconds=countdown), func, *args, job_id=task_id, **kwargs
        )
    else:
        job = func.delay(*args, job_id=task_id, **kwargs)
    CeleryTaskLog.objects.create(
        task_id=task_id,
        name=func.__name__,
        args=list(args),
        kwargs=kwargs,
        eta=eta,
        status="SCHEDULED",
        business_id=kwargs.get("business_id"),
    )
    return SimpleNamespace(id=task_id)


for _f in (send_follow_up, refresh_expiring_tokens, cleanup_celery_logs):
    _f.apply = lambda args=None, kwargs=None, f=_f: _apply(f, args, kwargs)
    _f.apply_async = lambda args=None, kwargs=None, countdown=0, headers=None, f=_f: _apply_async(f, args, kwargs, countdown, headers)

