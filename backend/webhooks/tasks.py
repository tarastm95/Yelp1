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
    logger.info(f"[FOLLOW-UP] 🚀 STARTING send_follow_up task")
    logger.info(f"[FOLLOW-UP] Parameters:")
    logger.info(f"[FOLLOW-UP] - Lead ID: {lead_id}")
    logger.info(f"[FOLLOW-UP] - Business ID: {business_id or 'Not specified'}")
    logger.info(f"[FOLLOW-UP] - Message text: {text[:100]}..." + ("" if len(text) <= 100 else " (truncated)"))
    logger.info(f"[FOLLOW-UP] - Full message length: {len(text)} characters")
    
    job = get_current_job()
    job_id = job.id if job else None
    logger.info(f"[FOLLOW-UP] Task ID: {job_id}")
    
    # Step 1: Mark task as inactive
    if job_id:
        updated_count = LeadPendingTask.objects.filter(task_id=job_id).update(active=False)
        logger.info(f"[FOLLOW-UP] 📝 Marked {updated_count} LeadPendingTask(s) as inactive")
        
    # Step 2: Check for duplicates
    logger.info(f"[FOLLOW-UP] 🔍 STEP 1: Checking for duplicate messages")
    if _already_sent(lead_id, text, exclude_task_id=job_id):
        logger.warning(f"[FOLLOW-UP] ⚠️ DUPLICATE DETECTED - message already sent for lead={lead_id}")
        logger.info(f"[FOLLOW-UP] 🛑 EARLY RETURN - skipping duplicate message")
        return

    logger.info(f"[FOLLOW-UP] ✅ No duplicate found - proceeding with send")

    # Step 3: Validate message text
    logger.info(f"[FOLLOW-UP] 📝 STEP 2: Validating message text")
    if not text.strip():
        logger.warning(f"[FOLLOW-UP] ⚠️ EMPTY MESSAGE TEXT detected for lead={lead_id}")
        logger.info(f"[FOLLOW-UP] Original text: '{text}'")
        logger.info(f"[FOLLOW-UP] Stripped text: '{text.strip()}'")
        logger.info(f"[FOLLOW-UP] 🛑 EARLY RETURN - skipping empty message")
        return
        
    logger.info(f"[FOLLOW-UP] ✅ Message text validation passed")

    # Step 4: Acquire lead lock
    logger.info(f"[FOLLOW-UP] 🔒 STEP 3: Acquiring lead lock")
    lock_id = f"lead-lock:{lead_id}"
    logger.info(f"[FOLLOW-UP] Lock ID: {lock_id}")
    logger.info(f"[FOLLOW-UP] Lock timeout: {LOCK_TIMEOUT}s")
    logger.info(f"[FOLLOW-UP] Lock blocking timeout: 5s")
    
    try:
        with _get_lock(lock_id, timeout=LOCK_TIMEOUT, blocking_timeout=5):
            logger.info(f"[FOLLOW-UP] ✅ Lock acquired successfully")
            
            # Step 5: Double-check for duplicates inside lock
            logger.info(f"[FOLLOW-UP] 🔍 STEP 4: Double-checking for duplicates inside lock")
            if _already_sent(lead_id, text, exclude_task_id=job_id):
                logger.warning(f"[FOLLOW-UP] ⚠️ DUPLICATE DETECTED IN LOCK - message already sent for lead={lead_id}")
                logger.info(f"[FOLLOW-UP] This suggests another task sent the same message while we were waiting")
                logger.info(f"[FOLLOW-UP] 🛑 RETURN - skipping duplicate message")
                return
                
            logger.info(f"[FOLLOW-UP] ✅ Still no duplicate found in lock - proceeding")

            # Step 6: Get authentication token
            logger.info(f"[FOLLOW-UP] 🔐 STEP 5: Getting authentication token")
            biz_id = business_id
            token = None
            
            if biz_id:
                logger.info(f"[FOLLOW-UP] Attempting to get business-specific token for business_id: {biz_id}")
                try:
                    token = get_valid_business_token(biz_id)
                    logger.info(f"[FOLLOW-UP] ✅ Successfully obtained business token")
                    logger.debug(f"[FOLLOW-UP] Business token: {token[:20]}...")
                except Exception as exc:
                    logger.error(f"[FOLLOW-UP] ❌ Error fetching business token for business={biz_id}: {exc}")
                    logger.exception(f"[FOLLOW-UP] Business token fetch exception")
                    
            if not token:
                logger.info(f"[FOLLOW-UP] No business token available - attempting to get lead-specific token")
                try:
                    token = get_token_for_lead(lead_id)
                    if token:
                        logger.info(f"[FOLLOW-UP] ✅ Successfully obtained lead-specific token")
                        logger.debug(f"[FOLLOW-UP] Lead token: {token[:20]}...")
                    else:
                        logger.warning(f"[FOLLOW-UP] ⚠️ Lead-specific token is None")
                except Exception as exc:
                    logger.error(f"[FOLLOW-UP] ❌ Error fetching lead token: {exc}")
                    logger.exception(f"[FOLLOW-UP] Lead token fetch exception")
                    
            if not token:
                logger.error(f"[FOLLOW-UP] ❌ NO TOKEN AVAILABLE for lead={lead_id}")
                logger.error(f"[FOLLOW-UP] Cannot send message without authentication")
                logger.error(f"[FOLLOW-UP] Tried business_id={biz_id} and lead_id={lead_id}")
                logger.info(f"[FOLLOW-UP] 🛑 RETURN - cannot proceed without token")
                return
                
            logger.info(f"[FOLLOW-UP] ✅ Token obtained successfully")

            # Step 7: Prepare API request
            logger.info(f"[FOLLOW-UP] 📡 STEP 6: Preparing API request")
            url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {"request_content": text, "request_type": "TEXT"}
            
            logger.info(f"[FOLLOW-UP] API request details:")
            logger.info(f"[FOLLOW-UP] - URL: {url}")
            logger.info(f"[FOLLOW-UP] - Headers: Authorization=Bearer {token[:20]}..., Content-Type=application/json")
            logger.info(f"[FOLLOW-UP] - Payload: {payload}")
            logger.info(f"[FOLLOW-UP] - Timeout: 10 seconds")

            # Step 8: Send API request
            logger.info(f"[FOLLOW-UP] 📤 STEP 7: Sending follow-up message to Yelp API")
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                logger.info(f"[FOLLOW-UP] API response received:")
                logger.info(f"[FOLLOW-UP] - Status code: {resp.status_code}")
                logger.info(f"[FOLLOW-UP] - Response headers: {dict(resp.headers)}")
                logger.info(f"[FOLLOW-UP] - Response text: {resp.text[:200]}..." + ("" if len(resp.text) <= 200 else " (truncated)"))
                
                resp.raise_for_status()
                logger.info(f"[FOLLOW-UP] ✅ Message sent successfully!")
                
                # Створюємо LeadEvent з from_backend=True щоб система знала що це наше повідомлення
                try:
                    from .models import LeadEvent
                    from django.utils import timezone as django_timezone
                    
                    logger.info(f"[FOLLOW-UP] 📝 Creating LeadEvent with from_backend=True")
                    
                    # Створюємо унікальний event_id для нашого повідомлення
                    import uuid
                    our_event_id = f"backend_sent_{uuid.uuid4().hex[:16]}"
                    
                    lead_event = LeadEvent.objects.create(
                        event_id=our_event_id,
                        lead_id=lead_id,
                        event_type="TEXT",
                        user_type="BUSINESS",  # Ми відправляємо від імені бізнесу
                        user_id="",
                        user_display_name="",
                        text=text,
                        cursor="",
                        time_created=django_timezone.now().isoformat(),
                        raw={"backend_sent": True, "task_id": job_id},
                        from_backend=True  # 🔑 КЛЮЧОВИЙ FLAG!
                    )
                    
                    logger.info(f"[FOLLOW-UP] ✅ Created LeadEvent id={lead_event.pk} with from_backend=True")
                    logger.info(f"[FOLLOW-UP] This will help system recognize this message as ours when webhook arrives")
                    
                except Exception as event_error:
                    # Не падаємо якщо не вдалося створити LeadEvent - повідомлення вже надіслано
                    logger.error(f"[FOLLOW-UP] ⚠️ Failed to create LeadEvent with from_backend=True: {event_error}")
                    logger.exception(f"[FOLLOW-UP] LeadEvent creation exception (non-critical)")
                
                logger.info(f"[FOLLOW-UP] 🎉 FOLLOW-UP COMPLETED for lead={lead_id}")
                
            except requests.exceptions.Timeout as e:
                logger.error(f"[FOLLOW-UP] ❌ TIMEOUT ERROR during API request: {e}")
                logger.error(f"[FOLLOW-UP] Request took longer than 10 seconds")
                raise
            except requests.exceptions.HTTPError as e:
                logger.error(f"[FOLLOW-UP] ❌ HTTP ERROR during API request: {e}")
                logger.error(f"[FOLLOW-UP] Response status: {resp.status_code}")
                logger.error(f"[FOLLOW-UP] Response body: {resp.text}")
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"[FOLLOW-UP] ❌ REQUEST ERROR during API request: {e}")
                logger.exception(f"[FOLLOW-UP] Request exception details")
                raise
            except Exception as e:
                logger.error(f"[FOLLOW-UP] ❌ UNEXPECTED ERROR during API request: {e}")
                logger.exception(f"[FOLLOW-UP] Unexpected exception details")
                raise
                
    except Exception as lock_exc:
        logger.error(f"[FOLLOW-UP] ❌ LOCK ERROR: {lock_exc}")
        logger.exception(f"[FOLLOW-UP] Lock acquisition or processing failed")
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

