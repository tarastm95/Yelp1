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
    log_lead_activity,
    log_system_error,
    log_performance_metric,
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
    
    # Step 1: Check sequential queue - wait for previous message
    logger.info(f"[FOLLOW-UP] 🔗 STEP 0: Checking message queue order")
    logger.info(f"[FOLLOW-UP] ========== SEQUENTIAL QUEUE CHECK ==========")
    
    current_task = None
    if job_id:
        try:
            current_task = LeadPendingTask.objects.get(task_id=job_id)
            logger.info(f"[FOLLOW-UP] Current task found:")
            logger.info(f"[FOLLOW-UP] - Sequence: #{current_task.sequence_number}")
            logger.info(f"[FOLLOW-UP] - Previous task ID: {current_task.previous_task_id or 'None (first in queue)'}")
            logger.info(f"[FOLLOW-UP] - Status: {current_task.status}")
            
            # Використовуємо метод моделі для перевірки
            if not current_task.can_send():
                logger.warning(f"[FOLLOW-UP] ⏸️ WAITING FOR PREVIOUS MESSAGE")
                logger.info(f"[FOLLOW-UP] Cannot send sequence #{current_task.sequence_number} yet")
                logger.info(f"[FOLLOW-UP] Previous task {current_task.previous_task_id} not sent yet")
                
                # Перевіряємо статус попереднього
                try:
                    prev_task = LeadPendingTask.objects.get(task_id=current_task.previous_task_id)
                    logger.info(f"[FOLLOW-UP] Previous task status: {prev_task.status}")
                    logger.info(f"[FOLLOW-UP] Previous task sequence: #{prev_task.sequence_number}")
                    
                    if prev_task.status in ['FAILED', 'CANCELLED']:
                        logger.error(f"[FOLLOW-UP] ❌ Previous task FAILED/CANCELLED - cannot continue")
                        current_task.status = 'CANCELLED'
                        current_task.save()
                        return "CANCELLED: Previous message failed"
                    
                except LeadPendingTask.DoesNotExist:
                    logger.warning(f"[FOLLOW-UP] Previous task not found - will send anyway")
                
                # Retry через 30 секунд
                logger.info(f"[FOLLOW-UP] 🔄 Retrying in 30 seconds...")
                current_task.status = 'WAITING'
                current_task.save()
                
                # Re-schedule цей task
                send_follow_up.apply_async(
                    args=[lead_id, text],
                    headers={"business_id": business_id},
                    countdown=30
                )
                return "WAITING: Previous message not sent yet, retry scheduled"
            
            logger.info(f"[FOLLOW-UP] ✅ Queue check passed - can send message")
            current_task.status = 'SENDING'
            current_task.save()
            
        except LeadPendingTask.DoesNotExist:
            logger.warning(f"[FOLLOW-UP] Task {job_id} not found in DB - proceeding without queue check")
    
    logger.info(f"[FOLLOW-UP] =============================================")
    
    # Step 2: Mark task as inactive (moved from Step 1)
    if job_id:
        updated_count = LeadPendingTask.objects.filter(task_id=job_id).update(active=False)
        logger.info(f"[FOLLOW-UP] 📝 Marked {updated_count} LeadPendingTask(s) as inactive")
        
    # Step 3: Check for duplicates
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
            logger.info(f"[FOLLOW-UP] Task {i+1}: ID={task.pk}, task_id='{task.task_id}', active={task.active}, phone_available={task.phone_available}")
    
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
                                from datetime import timedelta
                                task_created_at = timezone.now() - timedelta(minutes=5)
                                logger.warning(f"[FOLLOW-UP] FINAL CHECK: Using fallback time (5 min ago): {task_created_at}")
                        except Exception as e:
                            logger.error(f"[FOLLOW-UP] FINAL CHECK: Error getting timing: {e}")
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

            # Step 8a: 🔄 CREATE LeadEvent FIRST to prevent race condition
            logger.info(f"[FOLLOW-UP] 📝 STEP 8a: Creating LeadEvent with from_backend=True BEFORE API call")
            logger.info(f"[FOLLOW-UP] 🎯 This prevents race condition where webhook arrives before LeadEvent creation")
            
            lead_event = None
            our_event_id = None
            
            try:
                from django.utils import timezone as django_timezone
                import uuid

                logger.info(f"[FOLLOW-UP] TEXT ANALYSIS FOR FUTURE DETECTION:")
                logger.info(f"[FOLLOW-UP] - Lead ID: {lead_id}")
                logger.info(f"[FOLLOW-UP] - Text length: {len(text)}")
                logger.info(f"[FOLLOW-UP] - Text hash: {hash(text)}")
                logger.info(f"[FOLLOW-UP] - Full text: '{text}'")
                logger.info(f"[FOLLOW-UP] - Text preview: '{text[:100]}...' " + ("" if len(text) <= 100 else f"(+{len(text)-100} more chars)"))

                # Створюємо унікальний event_id для нашого повідомлення
                our_event_id = f"backend_sent_{uuid.uuid4().hex[:16]}"

                # Normalize text before storing to ensure exact match with webhook
                from .webhook_views import normalize_text
                normalized_text = normalize_text(text)
                logger.info(f"[FOLLOW-UP] 🔄 TEXT NORMALIZATION FOR FUTURE DETECTION:")
                logger.info(f"[FOLLOW-UP] - Original: '{text}'")
                logger.info(f"[FOLLOW-UP] - Normalized: '{normalized_text}'")
                logger.info(f"[FOLLOW-UP] - Normalization changed text: {text != normalized_text}")
                
                if text != normalized_text:
                    logger.info(f"[FOLLOW-UP] 🔄 Unicode normalization applied")
                    # Show what changed
                    for i, (orig_char, norm_char) in enumerate(zip(text, normalized_text)):
                        if orig_char != norm_char:
                            logger.info(f"[FOLLOW-UP]   Pos {i}: '{orig_char}' (U+{ord(orig_char):04X}) → '{norm_char}' (U+{ord(norm_char):04X})")
                else:
                    logger.info(f"[FOLLOW-UP] ✅ Text already normalized (no changes needed)")
                
                # Create LeadEvent BEFORE API call with placeholder raw data
                lead_event = LeadEvent.objects.create(
                    event_id=our_event_id,
                    lead_id=lead_id,
                    event_type="TEXT",
                    user_type="BUSINESS",  # Ми відправляємо від імені бізнесу
                    user_id="",
                    user_display_name="",
                    text=normalized_text,  # Store normalized text for exact match
                    cursor="",
                    time_created=django_timezone.now().isoformat(),
                    raw={"backend_sent": True, "task_id": job_id, "api_status": "sending", "original_text": text},
                    from_backend=True  # 🔑 КЛЮЧОВИЙ FLAG!
                )

                logger.info(f"[FOLLOW-UP] ✅ Created LeadEvent id={lead_event.pk} with from_backend=True BEFORE API call")
                logger.info(f"[FOLLOW-UP] STORED TEXT: '{lead_event.text}'")
                logger.info(f"[FOLLOW-UP] 🛡️ This will help system recognize this message as ours when webhook arrives")

            except Exception as event_error:
                logger.error(f"[FOLLOW-UP] ❌ CRITICAL: Failed to create LeadEvent with from_backend=True: {event_error}")
                logger.exception(f"[FOLLOW-UP] LeadEvent creation exception")
                logger.error(f"[FOLLOW-UP] 🚨 Cannot proceed safely without LeadEvent - this would cause race condition")
                return f"ERROR: Failed to create LeadEvent before API call - {str(event_error)}"

            # Step 8b: Send API request
            logger.info(f"[FOLLOW-UP] 📤 STEP 8b: Sending follow-up message to Yelp API")
            api_success = False
            resp = None
            
            for attempt in range(3):
                try:
                    api_start_time = time.time()
                    api_sent_at = timezone.now()  # ✅ РЕАЛЬНИЙ ЧАС ВІДПРАВКИ
                    
                    logger.info(
                        f"[FOLLOW-UP] 🔄 Attempt {attempt + 1}/3: Making POST request to Yelp API at {api_sent_at.isoformat()}"
                    )
                    
                    # Записати РЕАЛЬНИЙ час відправки перед HTTP запитом
                    if job_id:
                        CeleryTaskLog.objects.filter(task_id=job_id).update(
                            sent_at=api_sent_at
                        )
                        logger.info(f"[FOLLOW-UP] 📤 Recorded real sent_at time: {api_sent_at.isoformat()}")
                    
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
                    
                    # CRITICAL: Compare what we sent vs what Yelp might return
                    logger.info(f"[FOLLOW-UP] 🔍 TEXT COMPARISON ANALYSIS:")
                    logger.info(f"[FOLLOW-UP] ========== SENT vs EXPECTED RETURN ==========")
                    logger.info(f"[FOLLOW-UP] SENT TO YELP:")
                    logger.info(f"[FOLLOW-UP] - Text: '{text}'")
                    logger.info(f"[FOLLOW-UP] - Length: {len(text)}")
                    logger.info(f"[FOLLOW-UP] - Hash: {hash(text)}")
                    logger.info(f"[FOLLOW-UP] - Encoding: {type(text)}")
                    
                    # Check for Unicode characters
                    import unicodedata
                    unicode_chars = []
                    for i, char in enumerate(text):
                        if ord(char) > 127:  # Non-ASCII
                            unicode_chars.append(f"pos {i}: '{char}' (U+{ord(char):04X})")
                    
                    if unicode_chars:
                        logger.info(f"[FOLLOW-UP] - Unicode chars found: {unicode_chars[:10]}")  # Show first 10
                    else:
                        logger.info(f"[FOLLOW-UP] - No Unicode characters (pure ASCII)")
                    
                    logger.info(f"[FOLLOW-UP] WHAT YELP WILL LIKELY RETURN:")
                    logger.info(f"[FOLLOW-UP] - When webhook arrives, expect this text in BIZ event")
                    logger.info(f"[FOLLOW-UP] - Any differences will be logged in webhook processing")
                    logger.info(f"[FOLLOW-UP] ==================================================")

                    if resp.status_code == 200:
                        logger.info(f"[FOLLOW-UP] ✅ HTTP 200 - Message sent successfully!")
                    elif resp.status_code == 201:
                        logger.info(f"[FOLLOW-UP] ✅ HTTP 201 - Message created successfully!")
                    else:
                        logger.warning(f"[FOLLOW-UP] ⚠️ Unexpected status code: {resp.status_code}")

                    resp.raise_for_status()
                    logger.info(f"[FOLLOW-UP] ✅ No HTTP errors detected!")
                    api_success = True
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
                    
                    # Clean up LeadEvent on final attempt failure
                    if attempt == 2 and lead_event:
                        try:
                            lead_event.delete()
                            logger.error(f"[FOLLOW-UP] 🧹 Cleaned up LeadEvent {lead_event.pk} due to timeout")
                        except Exception:
                            logger.error(f"[FOLLOW-UP] ⚠️ Failed to cleanup LeadEvent {lead_event.pk}")
                    
                    if attempt == 2:  # Last attempt
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
                    
                    # Clean up LeadEvent on final failure
                    if lead_event:
                        try:
                            lead_event.delete()
                            logger.error(f"[FOLLOW-UP] 🧹 Cleaned up LeadEvent {lead_event.pk} due to HTTP error")
                        except Exception:
                            logger.error(f"[FOLLOW-UP] ⚠️ Failed to cleanup LeadEvent {lead_event.pk}")
                    
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
                    
                    # Clean up LeadEvent on final attempt failure
                    if attempt == 2 and lead_event:
                        try:
                            lead_event.delete()
                            logger.error(f"[FOLLOW-UP] 🧹 Cleaned up LeadEvent {lead_event.pk} due to request error")
                        except Exception:
                            logger.error(f"[FOLLOW-UP] ⚠️ Failed to cleanup LeadEvent {lead_event.pk}")
                    
                    if attempt == 2:  # Last attempt
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
                    
                    # Log to database for tracking
                    log_system_error(
                        error_type='TASK_ERROR',
                        error_message=f'Follow-up API request failed for lead {lead_id}',
                        exception=e,
                        severity='HIGH',
                        lead_id=lead_id,
                        business_id=business_id,
                        task_id=job_id,
                        attempt=attempt + 1,
                        api_duration=api_duration,
                        url=url
                    )
                    
                    # Clean up LeadEvent on final attempt failure
                    if attempt == 2 and lead_event:
                        try:
                            lead_event.delete()
                            logger.error(f"[FOLLOW-UP] 🧹 Cleaned up LeadEvent {lead_event.pk} due to unexpected error")
                        except Exception:
                            logger.error(f"[FOLLOW-UP] ⚠️ Failed to cleanup LeadEvent {lead_event.pk}")
                    
                    if attempt == 2:  # Last attempt
                        return f"ERROR: Unexpected error after {api_duration:.2f}s - {str(e)}"

            # Step 8c: Update LeadEvent with API response details
            if api_success and lead_event and resp:
                try:
                    logger.info(f"[FOLLOW-UP] 📝 STEP 8c: Updating LeadEvent with API response details")
                    
                    # Update raw data with actual API response
                    updated_raw = lead_event.raw.copy()
                    updated_raw.update({
                        "api_status": "success",
                        "yelp_response": resp.text[:1000],
                        "status_code": resp.status_code,
                        "api_duration": api_duration if 'api_duration' in locals() else None,
                    })
                    
                    lead_event.raw = updated_raw
                    lead_event.save()
                    
                    logger.info(f"[FOLLOW-UP] ✅ Updated LeadEvent {lead_event.pk} with API response details")
                    
                except Exception as update_error:
                    logger.error(f"[FOLLOW-UP] ⚠️ Failed to update LeadEvent with API response: {update_error}")
                    logger.exception(f"[FOLLOW-UP] LeadEvent update exception (non-critical - message was sent)")

            logger.info(f"[FOLLOW-UP] 🎉 FOLLOW-UP COMPLETED SUCCESSFULLY for lead={lead_id}")
            logger.info(f"[FOLLOW-UP] ========== TASK COMPLETION ==========")
            logger.info(f"[FOLLOW-UP] - Lead ID: {lead_id}")
            logger.info(f"[FOLLOW-UP] - Business ID: {business_id}")
            logger.info(f"[FOLLOW-UP] - Task ID: {job_id}")
            logger.info(f"[FOLLOW-UP] - Message successfully sent to Yelp API")
            logger.info(f"[FOLLOW-UP] - HTTP Status: {resp.status_code if resp else 'N/A'}")
            logger.info(f"[FOLLOW-UP] - LeadEvent created BEFORE API call with from_backend=True")
            logger.info(f"[FOLLOW-UP] - API success: {api_success}")
            logger.info(f"[FOLLOW-UP] ===========================================")

            task_duration = time.time() - task_start_time if 'task_start_time' in locals() else 0
            logger.info(f"[FOLLOW-UP] 🎉 TASK COMPLETED SUCCESSFULLY in {task_duration:.2f} seconds")
            
                    # Database logging for successful follow-up execution
            log_lead_activity(
                lead_id=lead_id,
                activity_type="EXECUTION",
                event_name="follow_up_completed",
                message="Follow-up message sent successfully to Yelp API",
                component="WORKER",
                business_id=business_id,
                task_id=job_id,
                http_status=resp.status_code if resp else None,
                api_success=api_success,
                task_duration=task_duration,
                message_preview=text[:100],
                api_response_time=globals().get('api_duration', 0)
            )
            
            # Log performance metrics
            if 'api_duration' in globals():
                log_performance_metric(
                    metric_type='API_RESPONSE_TIME',
                    value=globals()['api_duration'] * 1000,  # Convert to milliseconds
                    unit='ms',
                    component='YELP_API',
                    business_id=business_id,
                    lead_id=lead_id,
                    endpoint='follow_up'
                )
            
            log_performance_metric(
                metric_type='FOLLOW_UP_SUCCESS_RATE',
                value=100.0,  # This task succeeded
                unit='%',
                component='FOLLOW_UP_SYSTEM',
                business_id=business_id
            )
            
            # ✅ ПОЗНАЧИТИ TASK ЯК SENT (для черги повідомлень)
            if current_task:
                current_task.status = 'SENT'
                current_task.sent_at = timezone.now()
                current_task.save()
                logger.info(f"[FOLLOW-UP] ✅ Task marked as SENT - next message in queue can proceed")
                logger.info(f"[FOLLOW-UP] - Sequence #{current_task.sequence_number} completed")
                logger.info(f"[FOLLOW-UP] - Sent at: {current_task.sent_at}")
            
            return f"SUCCESS: Message sent to Yelp API (HTTP {resp.status_code if resp else 'N/A'}) in {task_duration:.2f}s"
                
    except Exception as lock_exc:
        logger.error(f"[FOLLOW-UP] ❌ LOCK ERROR: {lock_exc}")
        logger.exception(f"[FOLLOW-UP] Lock acquisition or processing failed")
        
        # ❌ ПОЗНАЧИТИ TASK ЯК FAILED (для черги повідомлень)
        if current_task:
            current_task.status = 'FAILED'
            current_task.save()
            logger.error(f"[FOLLOW-UP] ❌ Task marked as FAILED - sequence #{current_task.sequence_number}")
            logger.error(f"[FOLLOW-UP] ⚠️ Subsequent messages in queue may be cancelled")
        
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
            
            # Log error to database for tracking
            log_system_error(
                error_type='TOKEN_ERROR',
                error_message=f'Failed to refresh token for business {tok.business_id}',
                exception=exc,
                severity='HIGH',
                business_id=tok.business_id
            )


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


# OAuth Background Processing Jobs ============================================

@logged_job
def process_oauth_data(access_token: str, refresh_token: str, expires_in: int, retry_count: int = 0):
    """
    Background processing of OAuth data after successful token exchange.
    
    This job handles:
    1. Fetching business list
    2. Storing tokens 
    3. Queuing individual business processing jobs
    
    Args:
        access_token: OAuth access token
        refresh_token: OAuth refresh token  
        expires_in: Token expiration time in seconds
        retry_count: Current retry attempt (for retry logic)
    """
    MAX_RETRIES = 3
    RETRY_DELAY = 60  # seconds
    
    logger.info("[OAUTH-BG] 🚀 Starting OAuth background processing")
    logger.info(f"[OAUTH-BG] Token expires in: {expires_in} seconds")
    logger.info(f"[OAUTH-BG] Retry count: {retry_count}/{MAX_RETRIES}")
    
    start_time = time.time()
    
    try:
        # Step 1: Get businesses list
        logger.info("[OAUTH-BG] 📋 Step 1: Fetching businesses list")
        biz_resp = requests.get(
            "https://partner-api.yelp.com/token/v1/businesses",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        
        if biz_resp.status_code != 200:
            logger.error(f"[OAUTH-BG] ❌ Failed to fetch businesses: status={biz_resp.status_code}, response={biz_resp.text}")
            return f"ERROR: Failed to fetch businesses - {biz_resp.status_code}"
            
        business_data = biz_resp.json()
        biz_ids = business_data.get("business_ids", [])
        logger.info(f"[OAUTH-BG] ✅ Found {len(biz_ids)} businesses: {biz_ids}")
        
        if not biz_ids:
            logger.warning("[OAUTH-BG] ⚠️ No businesses found for this token")
            return "SUCCESS: No businesses to process"
        
        # Step 2: Store tokens for each business
        logger.info("[OAUTH-BG] 💾 Step 2: Storing tokens")
        from .models import YelpToken
        expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        stored_count = 0
        for bid in biz_ids:
            try:
                token_obj, created = YelpToken.objects.update_or_create(
                    business_id=bid,
                    defaults={
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "expires_at": expires_at,
                    },
                )
                stored_count += 1
                action = "Created" if created else "Updated"
                logger.info(f"[OAUTH-BG] ✅ {action} token for business {bid}")
            except Exception as e:
                logger.error(f"[OAUTH-BG] ❌ Failed to store token for business {bid}: {e}")
        
        logger.info(f"[OAUTH-BG] 💾 Stored tokens for {stored_count}/{len(biz_ids)} businesses")
        
        # Step 3: Queue business processing jobs
        logger.info("[OAUTH-BG] 📤 Step 3: Queuing business processing jobs")
        queued_jobs = 0
        for bid in biz_ids:
            try:
                # Add small delay between jobs to avoid overwhelming APIs
                delay_seconds = queued_jobs * 2  # 0, 2, 4, 6... seconds
                
                job = process_single_business.apply_async(
                    args=[access_token, bid],
                    countdown=delay_seconds,
                )
                queued_jobs += 1
                logger.info(f"[OAUTH-BG] 📤 Queued job for business {bid} (delay: {delay_seconds}s, job_id: {job.id})")
            except Exception as e:
                logger.error(f"[OAUTH-BG] ❌ Failed to queue job for business {bid}: {e}")
        
        duration = time.time() - start_time
        logger.info(f"[OAUTH-BG] ✅ OAuth processing completed successfully")
        logger.info(f"[OAUTH-BG] 📊 Summary:")
        logger.info(f"[OAUTH-BG] - Businesses found: {len(biz_ids)}")
        logger.info(f"[OAUTH-BG] - Tokens stored: {stored_count}")
        logger.info(f"[OAUTH-BG] - Jobs queued: {queued_jobs}")
        logger.info(f"[OAUTH-BG] - Total duration: {duration:.2f}s")
        
        return f"SUCCESS: Processed {len(biz_ids)} businesses, queued {queued_jobs} jobs"
        
    except requests.RequestException as e:
        duration = time.time() - start_time
        logger.error(f"[OAUTH-BG] ❌ Network error during OAuth processing: {e}")
        logger.error(f"[OAUTH-BG] Duration before error: {duration:.2f}s")
        
        # Retry logic for network errors
        if retry_count < MAX_RETRIES:
            retry_count += 1
            logger.warning(f"[OAUTH-BG] 🔄 Retrying in {RETRY_DELAY}s (attempt {retry_count}/{MAX_RETRIES})")
            
            try:
                # Schedule retry with delay
                process_oauth_data.apply_async(
                    args=[access_token, refresh_token, expires_in, retry_count],
                    countdown=RETRY_DELAY,
                )
                return f"RETRYING: Network error, scheduled retry {retry_count}/{MAX_RETRIES}"
            except Exception as retry_error:
                logger.error(f"[OAUTH-BG] ❌ Failed to schedule retry: {retry_error}")
                return f"ERROR: Network error + retry failed - {str(e)}"
        else:
            logger.error(f"[OAUTH-BG] 💀 Max retries ({MAX_RETRIES}) exceeded for network error")
            
            # Log critical error for monitoring
            log_system_error(
                error_type='OAUTH_NETWORK_ERROR',
                error_message=f'OAuth processing failed after {MAX_RETRIES} retries',
                exception=e,
                severity='HIGH',
                metadata={'retry_count': retry_count, 'duration': duration}
            )
            return f"ERROR: Network error after {MAX_RETRIES} retries - {str(e)}"
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[OAUTH-BG] ❌ Unexpected error during OAuth processing: {e}")
        logger.exception("[OAUTH-BG] Full exception traceback:")
        logger.error(f"[OAUTH-BG] Duration before error: {duration:.2f}s")
        
        # For unexpected errors, only retry if it's not a permanent error
        should_retry = (
            retry_count < MAX_RETRIES and
            not isinstance(e, (KeyError, TypeError, AttributeError))  # Don't retry programming errors
        )
        
        if should_retry:
            retry_count += 1
            logger.warning(f"[OAUTH-BG] 🔄 Retrying unexpected error in {RETRY_DELAY}s (attempt {retry_count}/{MAX_RETRIES})")
            
            try:
                process_oauth_data.apply_async(
                    args=[access_token, refresh_token, expires_in, retry_count],
                    countdown=RETRY_DELAY,
                )
                return f"RETRYING: Unexpected error, scheduled retry {retry_count}/{MAX_RETRIES}"
            except Exception as retry_error:
                logger.error(f"[OAUTH-BG] ❌ Failed to schedule retry: {retry_error}")
                return f"ERROR: Unexpected error + retry failed - {str(e)}"
        else:
            logger.error(f"[OAUTH-BG] 💀 Not retrying unexpected error (retry_count: {retry_count}, error_type: {type(e).__name__})")
            
            # Log critical error for monitoring
            log_system_error(
                error_type='OAUTH_PROCESSING_ERROR',
                error_message=f'OAuth processing failed with unexpected error',
                exception=e,
                severity='CRITICAL',
                metadata={'retry_count': retry_count, 'duration': duration}
            )
            return f"ERROR: Unexpected error - {str(e)}"


@logged_job
def process_single_business(access_token: str, business_id: str, retry_count: int = 0):
    """
    Process single business details and leads.
    
    This job handles:
    1. Fetching business details from Yelp API
    2. Getting timezone from Google Maps
    3. Storing business information
    4. Fetching and processing all leads for this business
    
    Args:
        access_token: OAuth access token
        business_id: Yelp business ID to process
        retry_count: Current retry attempt (for retry logic)
    """
    MAX_RETRIES = 2  # Fewer retries for individual business processing
    RETRY_DELAY = 30  # seconds
    
    logger.info(f"[OAUTH-BIZ] 🏢 Processing business {business_id}")
    logger.info(f"[OAUTH-BIZ] Retry count: {retry_count}/{MAX_RETRIES}")
    start_time = time.time()
    
    try:
        from .models import YelpBusiness, ProcessedLead
        from .oauth_views import fetch_and_store_lead
        import time as time_module
        
        # Days mapping (should be imported from oauth_views)
        DAYS = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        
        # Step 1: Get business details
        logger.info(f"[OAUTH-BIZ] 📋 Step 1: Fetching business details for {business_id}")
        det_resp = requests.get(
            f"https://api.yelp.com/v3/businesses/{business_id}",
            headers={"Authorization": f"Bearer {settings.YELP_API_KEY}"},
            timeout=30,
        )
        
        if det_resp.status_code != 200:
            logger.error(f"[OAUTH-BIZ] ❌ Failed to fetch business details: status={det_resp.status_code}")
            return f"ERROR: Failed to fetch business details - {det_resp.status_code}"
        
        det = det_resp.json()
        name = det.get("name", "")
        loc = ", ".join(det.get("location", {}).get("display_address", []))
        lat = det.get("coordinates", {}).get("latitude")
        lng = det.get("coordinates", {}).get("longitude")
        
        logger.info(f"[OAUTH-BIZ] ✅ Business details: {name} at {loc}")
        
        # Step 2: Get timezone (if coordinates available)
        tz = ""
        if lat is not None and lng is not None:
            logger.info(f"[OAUTH-BIZ] 🌍 Step 2: Fetching timezone for coordinates {lat},{lng}")
            try:
                tz_resp = requests.get(
                    "https://maps.googleapis.com/maps/api/timezone/json",
                    params={
                        "location": f"{lat},{lng}",
                        "timestamp": int(time_module.time()),
                        "key": settings.GOOGLE_TIMEZONE_API_KEY,
                    },
                    timeout=30,
                )
                if tz_resp.status_code == 200:
                    tz_data = tz_resp.json()
                    tz = tz_data.get("timeZoneId", "")
                    logger.info(f"[OAUTH-BIZ] ✅ Timezone: {tz}")
                else:
                    logger.warning(f"[OAUTH-BIZ] ⚠️ Failed to fetch timezone: {tz_resp.status_code}")
            except requests.RequestException as e:
                logger.error(f"[OAUTH-BIZ] ❌ Error fetching timezone: {e}")
        else:
            logger.info("[OAUTH-BIZ] ⚠️ No coordinates available, skipping timezone")
        
        # Step 3: Parse business hours
        logger.info("[OAUTH-BIZ] ⏰ Step 3: Parsing business hours")
        open_days = ""
        open_hours = ""
        hours_info = det.get("hours") or []
        
        if hours_info:
            open_data = hours_info[0].get("open") or []
            days_set = []
            hours_lines = []
            
            for o in open_data:
                day = o.get("day")
                if day is None:
                    continue
                days_set.append(day)
                start = o.get("start", "")
                end = o.get("end", "")
                line = f"{DAYS[day]}: {start[:2]}:{start[2:]} - {end[:2]}:{end[2:]}"
                if o.get("is_overnight"):
                    line += " (+1)"
                hours_lines.append(line)
                
            if days_set:
                open_days = ", ".join(DAYS[d] for d in sorted(set(days_set)))
            if hours_lines:
                open_hours = "; ".join(hours_lines)
                
        logger.info(f"[OAUTH-BIZ] ✅ Business hours: {open_days} | {open_hours}")
        
        # Step 4: Store business information
        logger.info("[OAUTH-BIZ] 💾 Step 4: Storing business information")
        biz_obj, created = YelpBusiness.objects.update_or_create(
            business_id=business_id,
            defaults={
                "name": name,
                "location": loc,
                "time_zone": tz,
                "open_days": open_days,
                "open_hours": open_hours,
                "details": det,
            },
        )
        action = "Created" if created else "Updated"
        logger.info(f"[OAUTH-BIZ] ✅ {action} business record")
        
        # Step 5: Get leads list
        logger.info("[OAUTH-BIZ] 📋 Step 5: Fetching leads for business")
        lid_resp = requests.get(
            f"https://api.yelp.com/v3/businesses/{business_id}/lead_ids",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        
        if lid_resp.status_code != 200:
            logger.error(f"[OAUTH-BIZ] ❌ Failed to fetch lead_ids: status={lid_resp.status_code}")
            # Continue without leads - business info is still saved
            duration = time.time() - start_time
            logger.info(f"[OAUTH-BIZ] ✅ Business processing completed (no leads) in {duration:.2f}s")
            return f"SUCCESS: Business processed, failed to get leads - {lid_resp.status_code}"
        
        leads_data = lid_resp.json()
        lead_ids = leads_data.get("lead_ids", [])
        logger.info(f"[OAUTH-BIZ] ✅ Found {len(lead_ids)} leads")
        
        # Step 6: Process each lead
        if lead_ids:
            logger.info("[OAUTH-BIZ] 📋 Step 6: Processing leads")
            processed_leads = 0
            
            for lid in lead_ids:
                try:
                    # Mark lead as processed
                    ProcessedLead.objects.get_or_create(
                        business_id=business_id, lead_id=lid
                    )
                    
                    # Fetch and store lead details
                    fetch_and_store_lead(access_token, lid)
                    processed_leads += 1
                    logger.info(f"[OAUTH-BIZ] ✅ Processed lead {lid} ({processed_leads}/{len(lead_ids)})")
                    
                except Exception as e:
                    logger.error(f"[OAUTH-BIZ] ❌ Failed to process lead {lid}: {e}")
                    
            logger.info(f"[OAUTH-BIZ] ✅ Processed {processed_leads}/{len(lead_ids)} leads")
        
        duration = time.time() - start_time
        logger.info(f"[OAUTH-BIZ] ✅ Business processing completed successfully in {duration:.2f}s")
        logger.info(f"[OAUTH-BIZ] 📊 Summary for {business_id}:")
        logger.info(f"[OAUTH-BIZ] - Name: {name}")
        logger.info(f"[OAUTH-BIZ] - Leads processed: {processed_leads if lead_ids else 0}")
        logger.info(f"[OAUTH-BIZ] - Duration: {duration:.2f}s")
        
        return f"SUCCESS: Business {name} processed with {len(lead_ids)} leads"
        
    except requests.RequestException as e:
        duration = time.time() - start_time
        logger.error(f"[OAUTH-BIZ] ❌ Network error processing business {business_id}: {e}")
        logger.error(f"[OAUTH-BIZ] Duration before error: {duration:.2f}s")
        
        # Retry logic for network errors
        if retry_count < MAX_RETRIES:
            retry_count += 1
            logger.warning(f"[OAUTH-BIZ] 🔄 Retrying business {business_id} in {RETRY_DELAY}s (attempt {retry_count}/{MAX_RETRIES})")
            
            try:
                # Schedule retry with delay
                process_single_business.apply_async(
                    args=[access_token, business_id, retry_count],
                    countdown=RETRY_DELAY,
                )
                return f"RETRYING: Business {business_id} network error, retry {retry_count}/{MAX_RETRIES}"
            except Exception as retry_error:
                logger.error(f"[OAUTH-BIZ] ❌ Failed to schedule retry for business {business_id}: {retry_error}")
                return f"ERROR: Network error + retry failed - {str(e)}"
        else:
            logger.error(f"[OAUTH-BIZ] 💀 Max retries ({MAX_RETRIES}) exceeded for business {business_id}")
            
            # Log error for monitoring
            log_system_error(
                error_type='OAUTH_BUSINESS_NETWORK_ERROR',
                error_message=f'Business processing failed after {MAX_RETRIES} retries',
                exception=e,
                severity='MEDIUM',
                business_id=business_id,
                metadata={'retry_count': retry_count, 'duration': duration}
            )
            return f"ERROR: Business {business_id} network error after {MAX_RETRIES} retries - {str(e)}"
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[OAUTH-BIZ] ❌ Unexpected error processing business {business_id}: {e}")
        logger.exception(f"[OAUTH-BIZ] Full exception traceback:")
        logger.error(f"[OAUTH-BIZ] Duration before error: {duration:.2f}s")
        
        # For unexpected errors, be more selective about retrying individual business
        should_retry = (
            retry_count < MAX_RETRIES and
            not isinstance(e, (KeyError, TypeError, AttributeError, ImportError))  # Don't retry programming/config errors
        )
        
        if should_retry:
            retry_count += 1
            logger.warning(f"[OAUTH-BIZ] 🔄 Retrying business {business_id} for unexpected error in {RETRY_DELAY}s (attempt {retry_count}/{MAX_RETRIES})")
            
            try:
                process_single_business.apply_async(
                    args=[access_token, business_id, retry_count],
                    countdown=RETRY_DELAY,
                )
                return f"RETRYING: Business {business_id} unexpected error, retry {retry_count}/{MAX_RETRIES}"
            except Exception as retry_error:
                logger.error(f"[OAUTH-BIZ] ❌ Failed to schedule retry for business {business_id}: {retry_error}")
                return f"ERROR: Unexpected error + retry failed - {str(e)}"
        else:
            logger.error(f"[OAUTH-BIZ] 💀 Not retrying business {business_id} for unexpected error (retry_count: {retry_count}, error_type: {type(e).__name__})")
            
            # Log error for monitoring (lower severity since it's individual business)
            log_system_error(
                error_type='OAUTH_BUSINESS_PROCESSING_ERROR',
                error_message=f'Business {business_id} processing failed with unexpected error',
                exception=e,
                severity='MEDIUM',
                business_id=business_id,
                metadata={'retry_count': retry_count, 'duration': duration}
            )
            return f"ERROR: Business {business_id} unexpected error - {str(e)}"


# Fix the job setup
for _f in (send_follow_up, refresh_expiring_tokens, cleanup_celery_logs, process_oauth_data, process_single_business):
    _f.apply = lambda args=None, kwargs=None, f=_f: _apply(f, args, kwargs)
    _f.apply_async = lambda args=None, kwargs=None, countdown=0, headers=None, f=_f: _apply_async(f, args, kwargs, countdown, headers)