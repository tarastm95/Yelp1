# webhooks/tasks.py

import logging
import os
import time
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
    
    ВАЖЛИВО: Ця функція відправляє повідомлення через Yelp API, 
    це НЕ SMS! SMS налаштування не мають тут жодного відношення.
    """
    logger.info(f"[FOLLOW-UP] 🚀 STARTING send_follow_up task")
    logger.info(f"[FOLLOW-UP] ========== TASK INITIALIZATION ==========")
    logger.info(f"[FOLLOW-UP] Parameters:")
    logger.info(f"[FOLLOW-UP] - Lead ID: {lead_id}")
    logger.info(f"[FOLLOW-UP] - Business ID: {business_id or 'Not specified'}")
    logger.info(f"[FOLLOW-UP] - Message text: {text[:100]}..." + ("" if len(text) <= 100 else " (truncated)"))
    logger.info(f"[FOLLOW-UP] - Full message length: {len(text)} characters")
    logger.info(f"[FOLLOW-UP] - Message hash: {hash(text)}")
    logger.info(f"[FOLLOW-UP] - Timestamp: {timezone.now().isoformat()}")
    
    # Initialize timing
    task_start_time = time.time()
    
    job = get_current_job()
    job_id = job.id if job else None
    logger.info(f"[FOLLOW-UP] Task ID: {job_id}")
    logger.info(f"[FOLLOW-UP] Worker process: {os.getpid()}")
    logger.info(f"[FOLLOW-UP] ============================================")
    
    # Step 1: Mark task as inactive
    if job_id:
        updated_count = LeadPendingTask.objects.filter(task_id=job_id).update(active=False)
        logger.info(f"[FOLLOW-UP] 📝 Marked {updated_count} LeadPendingTask(s) as inactive")
        
    # Step 2: Check for duplicates
    logger.info(f"[FOLLOW-UP] 🔍 STEP 1: Checking for duplicate messages")
    logger.info(f"[FOLLOW-UP] ========== DUPLICATE DETECTION ==========")
    logger.info(f"[FOLLOW-UP] Message to check for duplicates:")
    logger.info(f"[FOLLOW-UP] - Lead ID: {lead_id}")
    logger.info(f"[FOLLOW-UP] - Task ID: {job_id}")
    logger.info(f"[FOLLOW-UP] - Full message text: '{text}'")
    logger.info(f"[FOLLOW-UP] - Message length: {len(text)} characters")
    logger.info(f"[FOLLOW-UP] - Message hash: {hash(text)}")
    
    # Check existing events with this text
    existing_events = LeadEvent.objects.filter(lead_id=lead_id, text=text)
    logger.info(f"[FOLLOW-UP] Existing LeadEvent count with same text: {existing_events.count()}")
    
    if existing_events.exists():
        logger.info(f"[FOLLOW-UP] Existing LeadEvent details:")
        for i, event in enumerate(existing_events[:3]):  # Show first 3
            logger.info(f"[FOLLOW-UP] Event {i+1}: ID={event.pk}, event_id='{event.event_id}', from_backend={event.from_backend}, time={event.time_created}")
    
    # Check existing pending tasks with this text
    existing_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, text=text, active=True)
    if job_id:
        existing_tasks = existing_tasks.exclude(task_id=job_id)
    
    logger.info(f"[FOLLOW-UP] Existing active LeadPendingTask count with same text: {existing_tasks.count()}")
    
    if existing_tasks.exists():
        logger.info(f"[FOLLOW-UP] Existing LeadPendingTask details:")
        for i, task in enumerate(existing_tasks[:3]):  # Show first 3
            logger.info(f"[FOLLOW-UP] Task {i+1}: ID={task.pk}, task_id='{task.task_id}', active={task.active}, phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}")
    
    logger.info(f"[FOLLOW-UP] =====================================")

    # 🔥 CRITICAL FIX: Check consumer response BEFORE duplicate check
    # This ensures we catch consumer responses even if duplicate detection would skip the task
    logger.info(f"[FOLLOW-UP] 🔍 STEP 1.5: Checking for consumer responses (PRIORITY CHECK)")
    logger.info(f"[FOLLOW-UP] ========== CONSUMER RESPONSE CHECK ===========")
    
    try:
        # Get the pending task to check when it was created
        if job_id:
            pending_task = LeadPendingTask.objects.filter(task_id=job_id).first()
            if pending_task:
                task_created_at = pending_task.created_at
                logger.info(f"[FOLLOW-UP] Task created at: {task_created_at}")
            else:
                # HOTFIX: Якщо задачі немає в БД, використовуємо час запуску RQ job
                logger.warning(f"[FOLLOW-UP] ⚠️ Task {job_id} not found in DB - using fallback timing")
                logger.warning(f"[FOLLOW-UP] This indicates RQ-DB synchronization issue!")
                
                # Отримуємо час створення RQ job
                try:
                    rq_job = job if job else None
                    if rq_job and hasattr(rq_job, 'created_at') and rq_job.created_at:
                        task_created_at = rq_job.created_at
                        logger.info(f"[FOLLOW-UP] Using RQ job created_at: {task_created_at}")
                    else:
                        # Останній fallback - використовуємо час 5 хвилин тому
                        from datetime import timedelta
                        task_created_at = timezone.now() - timedelta(minutes=5)
                        logger.warning(f"[FOLLOW-UP] Using fallback time (5 min ago): {task_created_at}")
                except Exception as e:
                    logger.error(f"[FOLLOW-UP] Error getting RQ job timing: {e}")
                    from datetime import timedelta
                    task_created_at = timezone.now() - timedelta(minutes=5)
                    logger.warning(f"[FOLLOW-UP] Using emergency fallback time: {task_created_at}")
            
            # Check for consumer events after task creation (працює для обох випадків)
            consumer_responses = LeadEvent.objects.filter(
                lead_id=lead_id,
                user_type="CONSUMER",
                time_created__gt=task_created_at,
                from_backend=False
            ).order_by('time_created')
            
            response_count = consumer_responses.count()
            logger.info(f"[FOLLOW-UP] Consumer responses after task creation: {response_count}")
            
            if response_count > 0:
                logger.info(f"[FOLLOW-UP] ❗ CONSUMER RESPONDED - cancelling follow-up")
                logger.info(f"[FOLLOW-UP] Recent consumer responses:")
                for i, response in enumerate(consumer_responses[:3]):
                    logger.info(f"[FOLLOW-UP] Response {i+1}: '{response.text[:50]}...' at {response.time_created}")
                
                # Mark task as cancelled due to consumer response (тільки якщо є запис в БД)
                if pending_task:
                    pending_task.active = False
                    pending_task.save(update_fields=['active'])
                    logger.info(f"[FOLLOW-UP] ✅ Marked DB task as inactive")
                else:
                    logger.warning(f"[FOLLOW-UP] ⚠️ Cannot mark DB task as inactive - no DB record")
                
                logger.info(f"[FOLLOW-UP] 🛑 EARLY RETURN - consumer responded after task creation")
                return "SKIPPED: Consumer responded after task creation"
            else:
                logger.info(f"[FOLLOW-UP] ✅ No consumer responses - proceeding with follow-up")
        else:
            logger.info(f"[FOLLOW-UP] ⚠️ No job_id provided - skipping consumer response check")
    except Exception as e:
        logger.error(f"[FOLLOW-UP] ❌ Error checking consumer responses: {e}")
        logger.info(f"[FOLLOW-UP] Proceeding with follow-up despite error")
    
    logger.info(f"[FOLLOW-UP] ==========================================")

    # Step 2: Check for duplicates (after consumer response check)
    logger.info(f"[FOLLOW-UP] 🔍 STEP 2: Checking for duplicate messages")
    if _already_sent(lead_id, text, exclude_task_id=job_id):
        logger.warning(f"[FOLLOW-UP] ⚠️ DUPLICATE DETECTED - message already sent for lead={lead_id}")
        logger.warning(f"[FOLLOW-UP] DUPLICATE DETAILS:")
        logger.warning(f"[FOLLOW-UP] - Duplicate message: '{text}'")
        logger.warning(f"[FOLLOW-UP] - Job ID: {job_id}")
        logger.info(f"[FOLLOW-UP] 🛑 EARLY RETURN - skipping duplicate message")
        return "SKIPPED: Duplicate message detected"

    logger.info(f"[FOLLOW-UP] ✅ No duplicate found - proceeding with send")

    # Step 3: Validate message text
    logger.info(f"[FOLLOW-UP] 📝 STEP 2: Validating message text")
    if not text.strip():
        logger.warning(f"[FOLLOW-UP] ⚠️ EMPTY MESSAGE TEXT detected for lead={lead_id}")
        logger.info(f"[FOLLOW-UP] Original text: '{text}'")
        logger.info(f"[FOLLOW-UP] Stripped text: '{text.strip()}'")
        logger.info(f"[FOLLOW-UP] 🛑 EARLY RETURN - skipping empty message")
        return "SKIPPED: Empty message text"
        
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
                return "SKIPPED: Duplicate found in lock"
                
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
                return "ERROR: No authentication token available"
                
            logger.info(f"[FOLLOW-UP] ✅ Token obtained successfully")

            # ❌ ВИДАЛЕНО: помилкову перевірку SMS налаштувань
            # Follow-up повідомлення відправляються через Yelp API в чат,
            # це НЕ SMS і не має жодного відношення до SMS налаштувань!
            
            logger.info(f"[FOLLOW-UP] 📝 STEP 6: Follow-up messages via Yelp API")
            logger.info(f"[FOLLOW-UP] ========== YELP API MESSAGE ==========")
            logger.info(f"[FOLLOW-UP] ✅ This is a Yelp chat message, NOT SMS")
            logger.info(f"[FOLLOW-UP] ✅ SMS settings are irrelevant for Yelp API")
            logger.info(f"[FOLLOW-UP] ✅ Proceeding with Yelp API message send")
            logger.info(f"[FOLLOW-UP] =====================================")

            # Step 7: Prepare API request
            logger.info(f"[FOLLOW-UP] 📡 STEP 7: Preparing API request")
            logger.info(f"[FOLLOW-UP] ========== API REQUEST PREPARATION ==========")
            
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
            logger.info(f"[FOLLOW-UP] - Timeout: 30 seconds")
            logger.info(f"[FOLLOW-UP] ==============================================")

            # 🔥 CRITICAL FINAL CHECK: Check consumer response RIGHT BEFORE sending
            logger.info(f"[FOLLOW-UP] 🔍 FINAL CONSUMER CHECK: Last chance before sending")
            logger.info(f"[FOLLOW-UP] ========== FINAL CONSUMER RESPONSE CHECK ===========")
            
            try:
                # Check for ANY consumer responses since task was created (if we know task creation time)
                if job_id:
                    pending_task = LeadPendingTask.objects.filter(task_id=job_id).first()
                    if pending_task:
                        task_created_at = pending_task.created_at
                        logger.info(f"[FOLLOW-UP] FINAL CHECK: Using DB task created_at: {task_created_at}")
                    else:
                        # HOTFIX: Використовуємо той самий fallback що й раніше
                        logger.warning(f"[FOLLOW-UP] ⚠️ FINAL CHECK: Task {job_id} not found in DB - using fallback timing")
                        try:
                            rq_job = job if job else None
                            if rq_job and hasattr(rq_job, 'created_at') and rq_job.created_at:
                                task_created_at = rq_job.created_at
                                logger.info(f"[FOLLOW-UP] FINAL CHECK: Using RQ job created_at: {task_created_at}")
                            else:
                                from django.utils import timezone
                                from datetime import timedelta
                                task_created_at = timezone.now() - timedelta(minutes=5)
                                logger.warning(f"[FOLLOW-UP] FINAL CHECK: Using fallback time (5 min ago): {task_created_at}")
                        except Exception as e:
                            logger.error(f"[FOLLOW-UP] FINAL CHECK: Error getting timing: {e}")
                            from django.utils import timezone
                            from datetime import timedelta
                            task_created_at = timezone.now() - timedelta(minutes=5)
                    
                    # Check for consumer events after task creation (працює для обох випадків)
                    final_consumer_responses = LeadEvent.objects.filter(
                        lead_id=lead_id,
                        user_type="CONSUMER",
                        time_created__gt=task_created_at,
                        from_backend=False
                    ).order_by('time_created')
                    
                    final_response_count = final_consumer_responses.count()
                    logger.info(f"[FOLLOW-UP] FINAL CHECK: {final_response_count} consumer responses since task creation")
                    
                    if final_response_count > 0:
                        logger.info(f"[FOLLOW-UP] 🛑 FINAL ABORT: Consumer responded - cancelling at the last moment")
                        logger.info(f"[FOLLOW-UP] Recent consumer responses found:")
                        for i, response in enumerate(final_consumer_responses[:3]):
                            logger.info(f"[FOLLOW-UP] Response {i+1}: '{response.text[:50]}...' at {response.time_created}")
                        
                        logger.info(f"[FOLLOW-UP] 🚫 FINAL CANCELLATION - not sending follow-up")
                        return "FINAL_SKIP: Consumer responded just before send"
                    else:
                        logger.info(f"[FOLLOW-UP] ✅ FINAL CHECK PASSED - no recent consumer responses")
                else:
                    logger.info(f"[FOLLOW-UP] ⚠️ No job_id for final check")
            except Exception as e:
                logger.error(f"[FOLLOW-UP] ❌ Error in final consumer check: {e}")
                logger.info(f"[FOLLOW-UP] Proceeding with send despite final check error")
                
            logger.info(f"[FOLLOW-UP] ================================================")

            # Step 8: Send API request
            logger.info(f"[FOLLOW-UP] 📤 STEP 8: Sending follow-up message to Yelp API")
            for attempt in range(3):
                try:
                    api_start_time = time.time()
                    logger.info(
                        f"[FOLLOW-UP] 🔄 Attempt {attempt + 1}/3: Making POST request to Yelp API at {timezone.now().isoformat()}"
                    )
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time

                    logger.info(f"[FOLLOW-UP] ✅ API response received after {api_duration:.2f} seconds")
                    logger.info(f"[FOLLOW-UP] ========== DETAILED API RESPONSE ==========")
                    logger.info(f"[FOLLOW-UP] - Status code: {resp.status_code}")
                    logger.info(f"[FOLLOW-UP] - Response time: {api_duration:.2f} seconds")
                    logger.info(f"[FOLLOW-UP] - Response headers: {dict(resp.headers)}")
                    logger.info(f"[FOLLOW-UP] - Response text: {resp.text[:500]}..." + ("" if len(resp.text) <= 500 else " (truncated)"))
                    logger.info(f"[FOLLOW-UP] - Response encoding: {resp.encoding}")
                    logger.info(f"[FOLLOW-UP] - Response URL: {resp.url}")
                    logger.info(f"[FOLLOW-UP] =======================================")

                    if resp.status_code == 200:
                        logger.info(f"[FOLLOW-UP] ✅ HTTP 200 - Message sent successfully!")
                    elif resp.status_code == 201:
                        logger.info(f"[FOLLOW-UP] ✅ HTTP 201 - Message created successfully!")
                    else:
                        logger.warning(f"[FOLLOW-UP] ⚠️ Unexpected status code: {resp.status_code}")

                    resp.raise_for_status()
                    logger.info(f"[FOLLOW-UP] ✅ No HTTP errors detected!")
                    break
                except requests.exceptions.Timeout as e:
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time
                    task_duration = api_end_time - task_start_time
                    logger.error(
                        f"[FOLLOW-UP] ❌ TIMEOUT ERROR during API request (attempt {attempt + 1}): {e}"
                    )
                    logger.error(f"[FOLLOW-UP] ========== TIMEOUT ERROR DETAILS ==========")
                    logger.error(f"[FOLLOW-UP] - Request duration: {api_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - Total task duration: {task_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - URL: {url}")
                    logger.error(f"[FOLLOW-UP] - Lead ID: {lead_id}")
                    logger.error(f"[FOLLOW-UP] - Business ID: {business_id}")
                    logger.error(f"[FOLLOW-UP] - Worker process: {os.getpid()}")
                    logger.error(f"[FOLLOW-UP] Request took longer than 30 seconds")
                    logger.error(f"[FOLLOW-UP] This usually means Yelp API is slow or unreachable")
                    logger.error(f"[FOLLOW-UP] =======================================")
                    return f"ERROR: Request timeout after {api_duration:.2f}s - {str(e)}"
                except requests.exceptions.HTTPError as e:
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time
                    task_duration = api_end_time - task_start_time
                    logger.error(
                        f"[FOLLOW-UP] ❌ HTTP ERROR during API request (attempt {attempt + 1}): {e}"
                    )
                    logger.error(f"[FOLLOW-UP] ========== HTTP ERROR DETAILS ==========")
                    logger.error(f"[FOLLOW-UP] - Response status: {resp.status_code}")
                    logger.error(f"[FOLLOW-UP] - Response headers: {dict(resp.headers)}")
                    try:
                        logger.error(f"[FOLLOW-UP] - Response JSON: {resp.json()}")
                    except ValueError:
                        logger.error(f"[FOLLOW-UP] - Response text: {resp.text}")
                    logger.error(f"[FOLLOW-UP] - Request duration: {api_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - Total task duration: {task_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - URL: {url}")
                    logger.error(f"[FOLLOW-UP] - Lead ID: {lead_id}")
                    logger.error(f"[FOLLOW-UP] - Business ID: {business_id}")
                    logger.error(f"[FOLLOW-UP] - Worker process: {os.getpid()}")
                    error_details = _extract_yelp_error(resp)
                    logger.error(f"[FOLLOW-UP] - Yelp error details: {error_details}")
                    logger.error(f"[FOLLOW-UP] ===================================")
                    if e.response is not None and e.response.status_code >= 500 and attempt < 2:
                        logger.warning(
                            f"[FOLLOW-UP] ⚠️ HTTP {e.response.status_code} on attempt {attempt + 1}. Retrying in 5 seconds."
                        )
                        time.sleep(5)
                        continue
                    return f"ERROR: HTTP {resp.status_code} after {api_duration:.2f}s - {error_details}"
                except requests.exceptions.RequestException as e:
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time
                    task_duration = api_end_time - task_start_time
                    logger.error(
                        f"[FOLLOW-UP] ❌ REQUEST ERROR during API request (attempt {attempt + 1}): {e}"
                    )
                    logger.error(f"[FOLLOW-UP] ========== REQUEST ERROR DETAILS ==========")
                    logger.error(f"[FOLLOW-UP] - Request duration: {api_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - Total task duration: {task_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - URL: {url}")
                    logger.error(f"[FOLLOW-UP] - Lead ID: {lead_id}")
                    logger.error(f"[FOLLOW-UP] - Business ID: {business_id}")
                    logger.error(f"[FOLLOW-UP] - Worker process: {os.getpid()}")
                    logger.error(f"[FOLLOW-UP] - Error type: {type(e).__name__}")
                    logger.error(f"[FOLLOW-UP] =========================================")
                    logger.exception(f"[FOLLOW-UP] Request exception details")
                    return f"ERROR: Request failed after {api_duration:.2f}s - {str(e)}"
                except Exception as e:
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time
                    task_duration = api_end_time - task_start_time
                    logger.error(
                        f"[FOLLOW-UP] ❌ UNEXPECTED ERROR during API request (attempt {attempt + 1}): {e}"
                    )
                    logger.error(f"[FOLLOW-UP] ========== UNEXPECTED ERROR DETAILS ==========")
                    logger.error(f"[FOLLOW-UP] - Request duration: {api_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - Total task duration: {task_duration:.2f} seconds")
                    logger.error(f"[FOLLOW-UP] - URL: {url}")
                    logger.error(f"[FOLLOW-UP] - Lead ID: {lead_id}")
                    logger.error(f"[FOLLOW-UP] - Business ID: {business_id}")
                    logger.error(f"[FOLLOW-UP] - Worker process: {os.getpid()}")
                    logger.error(f"[FOLLOW-UP] - Error type: {type(e).__name__}")
                    logger.error(f"[FOLLOW-UP] ============================================")
                    logger.exception(f"[FOLLOW-UP] Unexpected exception details")
                    return f"ERROR: Unexpected error after {api_duration:.2f}s - {str(e)}"

            # Створюємо LeadEvent з from_backend=True щоб система знала що це наше повідомлення
            try:
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
                    raw={"backend_sent": True, "task_id": job_id, "yelp_response": resp.text[:1000]},
                    from_backend=True  # 🔑 КЛЮЧОВИЙ FLAG!
                )

                logger.info(f"[FOLLOW-UP] ✅ Created LeadEvent id={lead_event.pk} with from_backend=True")
                logger.info(f"[FOLLOW-UP] This will help system recognize this message as ours when webhook arrives")

            except Exception as event_error:
                # Не падаємо якщо не вдалося створити LeadEvent - повідомлення вже надіслано
                logger.error(f"[FOLLOW-UP] ⚠️ Failed to create LeadEvent with from_backend=True: {event_error}")
                logger.exception(f"[FOLLOW-UP] LeadEvent creation exception (non-critical)")

            logger.info(f"[FOLLOW-UP] 🎉 FOLLOW-UP COMPLETED SUCCESSFULLY for lead={lead_id}")
            logger.info(f"[FOLLOW-UP] ========== TASK COMPLETION ==========")
            logger.info(f"[FOLLOW-UP] - Lead ID: {lead_id}")
            logger.info(f"[FOLLOW-UP] - Business ID: {business_id}")
            logger.info(f"[FOLLOW-UP] - Task ID: {job_id}")
            logger.info(f"[FOLLOW-UP] - Message successfully sent to Yelp API")
            logger.info(f"[FOLLOW-UP] - HTTP Status: {resp.status_code}")
            logger.info(f"[FOLLOW-UP] - LeadEvent created with from_backend=True")
            logger.info(f"[FOLLOW-UP] ===========================================")

            task_duration = time.time() - task_start_time if 'task_start_time' in locals() else 0
            logger.info(f"[FOLLOW-UP] 🎉 TASK COMPLETED SUCCESSFULLY in {task_duration:.2f} seconds")
            return f"SUCCESS: Message sent to Yelp API (HTTP {resp.status_code}) in {task_duration:.2f}s"
                
    except Exception as lock_exc:
        logger.error(f"[FOLLOW-UP] ❌ LOCK ERROR: {lock_exc}")
        logger.exception(f"[FOLLOW-UP] Lock acquisition or processing failed")
        return f"ERROR: Lock error - {str(lock_exc)}"


@logged_job
def refresh_expiring_tokens():
    """Proactively refresh tokens expiring soon."""
    margin = timezone.now() + timezone.timedelta(minutes=10)
    tokens = YelpToken.objects.filter(expires_at__lte=margin)
    if not tokens:
        logger.debug("[TOKEN REFRESH] No tokens require refresh")
    for tok in tokens:
        logger.info(f"[TOKEN REFRESH] Refreshing token for business={tok.business_id}")
        try:
            new_token_data = rotate_refresh_token(
                tok.refresh_token, tok.client_id, tok.client_secret
            )
            if new_token_data and "access_token" in new_token_data:
                tok.access_token = new_token_data["access_token"]
                tok.expires_at = timezone.now() + timezone.timedelta(
                    seconds=new_token_data.get("expires_in", 3600)
                )
                if "refresh_token" in new_token_data:
                    tok.refresh_token = new_token_data["refresh_token"]
                tok.save()
                logger.info(f"[TOKEN REFRESH] ✅ Token refreshed for business={tok.business_id}")
        except Exception as exc:
            logger.error(f"[TOKEN REFRESH] ❌ Failed to refresh token for business={tok.business_id}: {exc}")


@logged_job
def cleanup_celery_logs():
    """Remove old task logs."""
    cutoff = timezone.now() - timezone.timedelta(days=7)
    deleted_count, _ = CeleryTaskLog.objects.filter(finished_at__lt=cutoff).delete()
    logger.info(f"[CLEANUP] Deleted {deleted_count} old task logs")


# Define the jobs for easy access
ALL_JOBS = [send_follow_up, refresh_expiring_tokens, cleanup_celery_logs]


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


# Fix the job setup
for _f in (send_follow_up, refresh_expiring_tokens, cleanup_celery_logs):
    _f.apply = lambda args=None, kwargs=None, f=_f: _apply(f, args, kwargs)
    _f.apply_async = lambda args=None, kwargs=None, countdown=0, headers=None, f=_f: _apply_async(f, args, kwargs, countdown, headers)