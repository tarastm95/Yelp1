import logging
import time
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.utils.dateparse import parse_datetime
import re
import requests
import django_rq
from django.utils import timezone
from django.db import transaction, OperationalError, IntegrityError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    Event,
    ProcessedLead,
    AutoResponseSettings,
    LeadEvent,
    LeadDetail,
    FollowUpTemplate,
    LeadPendingTask,
    CeleryTaskLog,
    YelpBusiness,
)
from .serializers import EventSerializer
from .utils import (
    get_valid_business_token,
    get_token_for_lead,
    adjust_due_time,
    _already_sent,
    _parse_days,
    get_time_based_greeting,
)
from .tasks import send_follow_up

logger = logging.getLogger(__name__)

# Simple pattern to detect phone numbers like +380XXXXXXXXX or other
# international formats with optional spaces or dashes.
PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")
# Simple pattern to detect ISO-like dates such as 2023-12-31
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _extract_phone(text: str) -> str | None:
    """Return first phone number found in text, if any."""
    if not text:
        return None
    for m in PHONE_RE.finditer(text):
        candidate = m.group()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 10 and not DATE_RE.fullmatch(candidate):
            return candidate
    return None


def safe_update_or_create(model, defaults=None, **kwargs):
    """Retry update_or_create with simple retry logic."""
    for attempt in range(1, 6):
        try:
            logger.debug(
                f"[DB RETRY] Attempt {attempt}/5 for {model.__name__}.update_or_create with kwargs={kwargs}"
            )
            with transaction.atomic():
                obj, created = model.objects.update_or_create(
                    defaults=defaults or {}, **kwargs
                )
            logger.debug(
                f"[DB RETRY] Success on attempt {attempt} for {model.__name__} (pk={obj.pk}, created={created})"
            )
            return obj, created
        except OperationalError as e:
            logger.warning(
                f"[DB RETRY] OperationalError on attempt {attempt}/5 for {model.__name__}: {e}"
            )
            time.sleep(0.1)
    logger.debug(f"[DB RETRY] Final attempt for {model.__name__}.update_or_create")
    return model.objects.update_or_create(defaults=defaults or {}, **kwargs)


class WebhookView(APIView):
    """Handle incoming webhook events from Yelp."""

    def _is_new_lead(self, lead_id: str, business_id: str | None = None) -> dict:
        """Check Yelp events to verify if this lead is new.

        When ``business_id`` is provided the access token is obtained for that
        business.  Otherwise it falls back to :func:`get_token_for_lead`.

        Returns a JSON-like dict ``{"new_lead": bool}`` where ``new_lead`` is
        ``True`` when only a single consumer event exists.
        """
        logger.debug(
            "[WEBHOOK] _is_new_lead called with lead_id=%s, business_id=%s",
            lead_id,
            business_id,
        )

        if business_id:
            token = get_valid_business_token(business_id)
        else:
            token = get_token_for_lead(lead_id)

        logger.debug("[WEBHOOK] Using token for lead=%s: %s", lead_id, token)

        if not token:
            logger.error("[WEBHOOK] No token available for lead=%s", lead_id)
            return {"new_lead": False}
        url = f"https://api.yelp.com/v3/leads/{lead_id}/events"

        logger.debug(
            "[WEBHOOK] Verifying new lead via %s (no limit - all events)",
            url,
        )
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        logger.info(
            "[WEBHOOK] Yelp verify status for lead=%s: %s",
            lead_id,
            resp.status_code,
        )
        if resp.status_code != 200:
            logger.error(
                f"[WEBHOOK] Failed to verify new lead {lead_id}: {resp.status_code}"
            )
            return {"new_lead": False}

        events = resp.json().get("events", [])
        logger.debug(
            "[WEBHOOK] Yelp returned events for lead=%s: %s",
            lead_id,
            events,
        )
        logger.debug(
            "[WEBHOOK] Number of events for lead=%s: %d",
            lead_id,
            len(events),
        )
        reason = ""
        is_new = False
        if not events:
            reason = "no events returned"
        elif len(events) == 1:
            user_type = events[0].get("user_type")
            if user_type == "CONSUMER":
                is_new = True
                reason = "single CONSUMER event"
            else:
                reason = f"single event with user_type={user_type}"
        elif len(events) == 2:
            first_user_type = events[0].get("user_type")
            second_event_type_raw = events[1].get("event_type")
            second_event_type = (second_event_type_raw or "").upper()
            if first_user_type == "CONSUMER" and second_event_type != "TEXT":
                is_new = True
                reason = (
                    f"consumer message followed by {second_event_type_raw or 'unknown'}"
                )
            else:
                reason = (
                    "two events: "
                    f"first_user_type={first_user_type}, "
                    f"second_event_type={second_event_type}"
                )
        else:
            reason = f"{len(events)} events found"

        logger.debug(
            "[WEBHOOK] _is_new_lead decision for %s: %s (reason=%s)",
            lead_id,
            is_new,
            reason,
        )
        return {"new_lead": is_new, "reason": reason}

    def _apply_job_mappings(self, job_names: list) -> list:
        """Застосовує глобальні налаштування заміни назв послуг"""
        if not job_names:
            return job_names

        logger.info(f"[JOB-MAPPING] 🔄 Applying job mappings for: {job_names}")
        
        # Отримуємо всі активні маппінги з кешем
        mappings = {}
        try:
            from .models import JobMapping
            active_mappings = JobMapping.objects.filter(active=True)
            mappings = {mapping.original_name: mapping.custom_name for mapping in active_mappings}
            logger.info(f"[JOB-MAPPING] Found {len(mappings)} active mappings")
        except Exception as e:
            logger.error(f"[JOB-MAPPING] ❌ Error loading job mappings: {e}")
            return job_names

        # Застосовуємо маппінги
        mapped_names = []
        for job_name in job_names:
            if job_name in mappings:
                mapped_name = mappings[job_name]
                mapped_names.append(mapped_name)
                logger.info(f"[JOB-MAPPING] ✅ Mapped: '{job_name}' → '{mapped_name}'")
            else:
                mapped_names.append(job_name)
                logger.info(f"[JOB-MAPPING] ➡️ No mapping for: '{job_name}' (using original)")

        logger.info(f"[JOB-MAPPING] 🎯 Final mapped jobs: {mapped_names}")
        return mapped_names

    def post(self, request, *args, **kwargs):
        logger.info("[WEBHOOK] Received POST /webhook/")
        raw = request.data or {}
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else raw
        logger.info(f"[WEBHOOK] Parsed payload keys: {list(payload.keys())}")

        updates = payload.get("data", {}).get("updates", [])
        logger.info(f"[WEBHOOK] Found {len(updates)} update(s)")
        if not updates:
            logger.info("[WEBHOOK] No updates → returning 204")
            return Response({"status": "no updates"}, status=status.HTTP_204_NO_CONTENT)

        ev_ser = EventSerializer(data={"payload": payload})
        if not ev_ser.is_valid():
            logger.error(f"[WEBHOOK] EventSerializer errors: {ev_ser.errors}")
            return Response(ev_ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ev = ev_ser.save()
        logger.info(f"[WEBHOOK] Saved raw Event id={ev.id}")

        lead_ids = set()
        for upd in updates:
            lid = upd.get("lead_id")
            if lid:
                lead_ids.add(lid)
                logger.info(
                    f"[WEBHOOK] =============== LEAD VERIFICATION TRIGGER ==============="
                )
                logger.info(
                    f"[WEBHOOK] Checking ProcessedLead for lead_id={lid}"
                )
                logger.info(
                    f"[WEBHOOK] Current update event_type: {upd.get('event_type')}"
                )
                logger.info(
                    f"[WEBHOOK] Current update user_type: {upd.get('user_type')}"
                )
                logger.info(
                    f"[WEBHOOK] Current update user_display_name: {upd.get('user_display_name', '')}"
                )
                
                # Check if ProcessedLead exists
                processed_lead_exists = ProcessedLead.objects.filter(lead_id=lid).exists()
                logger.info(f"[WEBHOOK] ProcessedLead exists for {lid}: {processed_lead_exists}")
                
                event_type_check = upd.get("event_type") != "NEW_LEAD"
                logger.info(f"[WEBHOOK] Event type is not NEW_LEAD: {event_type_check}")
                
                if event_type_check and not processed_lead_exists:
                    logger.info(f"[WEBHOOK] 🔍 TRIGGERING NEW LEAD VERIFICATION for {lid}")
                    logger.info(f"[WEBHOOK] Reason: event_type='{upd.get('event_type')}' AND ProcessedLead doesn't exist")
                    logger.info(f"[WEBHOOK] Business ID for verification: {payload['data'].get('id')}")
                    
                    check = self._is_new_lead(lid, payload["data"].get("id"))
                    
                    logger.info(f"[WEBHOOK] ============= NEW LEAD VERIFICATION RESULT =============")
                    logger.info(f"[WEBHOOK] Lead ID: {lid}")
                    logger.info(f"[WEBHOOK] Verification result: {check}")
                    logger.info(f"[WEBHOOK] Is new lead: {check.get('new_lead')}")
                    logger.info(f"[WEBHOOK] Reason: {check.get('reason')}")
                    
                    if check.get("new_lead"):
                        logger.info(f"[WEBHOOK] ✅ CONVERTING EVENT TO NEW_LEAD for {lid}")
                        upd["event_type"] = "NEW_LEAD"
                        logger.info(
                            f"[WEBHOOK] Successfully marked lead={lid} as NEW_LEAD via events check"
                        )
                        logger.info(f"[WEBHOOK] Original event_type was: {upd.get('event_type', 'UNKNOWN')}")
                        logger.info(f"[WEBHOOK] New event_type is: NEW_LEAD")
                    else:
                        logger.warning(f"[WEBHOOK] ❌ LEAD NOT VERIFIED AS NEW for {lid}")
                        logger.warning(
                            "[WEBHOOK] _is_new_lead returned False for lead=%s: %s",
                            lid,
                            check.get("reason"),
                        )
                        logger.info(f"[WEBHOOK] Lead {lid} will be processed as regular event, not new lead")
                    logger.info(f"[WEBHOOK] ================================================")
                else:
                    if not event_type_check:
                        logger.info(f"[WEBHOOK] ⏭️ SKIPPING new lead check for {lid}: event_type is already NEW_LEAD")
                    if processed_lead_exists:
                        logger.info(f"[WEBHOOK] ⏭️ SKIPPING new lead check for {lid}: ProcessedLead already exists")
                    logger.info(f"[WEBHOOK] No new lead verification needed for {lid}")
                    
                if upd.get("event_type") == "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT":
                    logger.info(f"[WEBHOOK] 📱 CONSUMER_PHONE_NUMBER_OPT_IN_EVENT detected")
                    logger.info(f"[WEBHOOK] ========== PHONE OPT-IN EVENT ==========")
                    logger.info(f"[WEBHOOK] Lead ID: {lid}")
                    logger.info(f"[WEBHOOK] Event type: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT")
                    logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True")
                    
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    
                    logger.info(f"[WEBHOOK] LeadDetail update result:")
                    logger.info(f"[WEBHOOK] - Records updated: {updated}")
                    logger.info(f"[WEBHOOK] - This means {updated} LeadDetail(s) had phone_opt_in changed from False to True")
                    
                    if updated:
                        logger.info(f"[WEBHOOK] ✅ Phone opt-in updated successfully")
                        logger.info(f"[WEBHOOK] 🚀 TRIGGERING handle_phone_opt_in")
                        logger.info(f"[WEBHOOK] This will call _process_auto_response with phone_opt_in=True, phone_available=False")
                        self.handle_phone_opt_in(lid)
                        logger.info(f"[WEBHOOK] ✅ handle_phone_opt_in completed")
                    else:
                        logger.warning(f"[WEBHOOK] ⚠️ No LeadDetail records updated")
                        logger.warning(f"[WEBHOOK] This means the lead already had phone_opt_in=True")
                        logger.warning(f"[WEBHOOK] No additional auto-response will be triggered")
                    
                    logger.info(f"[WEBHOOK] =======================================")
                        
                logger.debug(
                    f"[WEBHOOK] Update for lead_id={lid}: "
                    f"event_type={upd.get('event_type')}, "
                    f"user_type={upd.get('user_type')}, "
                    f"user_display_name={upd.get('user_display_name', '')}"
                )
                if (
                    upd.get("event_type") == "NEW_EVENT"
                    and upd.get("user_type") == "CONSUMER"
                ):
                    logger.info(
                        f"[WEBHOOK] Consumer NEW_EVENT passed check for lead_id={lid}"
                    )
                    content = upd.get("event_content", {}) or {}
                    text = content.get("text") or content.get("fallback_text", "")
                    phone = _extract_phone(text)
                    has_phone = bool(phone)
                    pending = LeadPendingTask.objects.filter(
                        lead_id=lid,
                        phone_opt_in=False,
                        phone_available=False,
                        active=True,
                    ).exists()
                    if has_phone:
                        LeadDetail.objects.filter(lead_id=lid).update(
                            phone_in_text=True, phone_number=phone
                        )
                        try:
                            from .utils import update_phone_in_sheet

                            update_phone_in_sheet(lid, phone)
                        except Exception:
                            logger.exception(
                                "[WEBHOOK] Failed to update phone in sheet"
                            )
                        updated = True
                        trigger = updated or pending
                        if trigger:
                            reason = (
                                "Client responded with a number → switched to the 'phone available' scenario"
                                if pending
                                else None
                            )
                            self.handle_phone_available(lid, reason=reason)
                    elif pending:
                        reason = "Client responded, but no number was found"
                        self._cancel_no_phone_tasks(lid, reason=reason)
                else:
                    reasons = []
                    if upd.get("event_type") != "NEW_EVENT":
                        reasons.append(f"event_type={upd.get('event_type')}")
                    if upd.get("user_type") != "CONSUMER":
                        reasons.append(f"user_type={upd.get('user_type')}")
                    logger.debug(
                        "[WEBHOOK] Update did not pass consumer NEW_EVENT check for lead_id=%s (%s)",
                        lid,
                        ", ".join(reasons) or "unknown",
                    )
        logger.info(f"[WEBHOOK] Lead IDs to process: {lead_ids}")

        logger.info("[WEBHOOK] ================= PROCESSING NEW LEAD EVENTS =================")
        new_lead_updates = [upd for upd in updates if upd.get("event_type") == "NEW_LEAD"]
        logger.info(f"[WEBHOOK] Found {len(new_lead_updates)} NEW_LEAD events to process")
        
        for upd in updates:
            if upd.get("event_type") == "NEW_LEAD":
                lid = upd["lead_id"]
                business_id = payload["data"]["id"]
                
                logger.info(f"[WEBHOOK] 🆕 PROCESSING NEW LEAD EVENT")
                logger.info(f"[WEBHOOK] Lead ID: {lid}")
                logger.info(f"[WEBHOOK] Business ID: {business_id}")
                logger.info(f"[WEBHOOK] Update details: {upd}")
                
                logger.info(f"[WEBHOOK] Attempting to create/get ProcessedLead record")
                
                try:
                    pl, created = ProcessedLead.objects.get_or_create(
                        business_id=business_id,
                        lead_id=lid,
                    )
                    
                    logger.info(f"[WEBHOOK] ProcessedLead operation result:")
                    logger.info(f"[WEBHOOK] - Record ID: {pl.id}")
                    logger.info(f"[WEBHOOK] - Was created: {created}")
                    logger.info(f"[WEBHOOK] - Business ID: {pl.business_id}")
                    logger.info(f"[WEBHOOK] - Lead ID: {pl.lead_id}")
                    logger.info(f"[WEBHOOK] - Processed at: {pl.processed_at}")
                    
                    if created:
                        logger.info(f"[WEBHOOK] ✅ NEW ProcessedLead created successfully")
                        logger.info(f"[WEBHOOK] Created ProcessedLead id={pl.id} for lead={lid}")
                        logger.info(f"[WEBHOOK] 🚀 TRIGGERING handle_new_lead for lead={lid}")
                        logger.info(f"[WEBHOOK] This will start auto-response flow")
                        
                        self.handle_new_lead(lid)
                        
                        logger.info(f"[WEBHOOK] ✅ handle_new_lead completed for lead={lid}")
                    else:
                        logger.warning(f"[WEBHOOK] ⚠️ ProcessedLead already exists")
                        logger.info(f"[WEBHOOK] Lead {lid} already processed; skipping handle_new_lead")
                        logger.info(f"[WEBHOOK] Existing record created at: {pl.processed_at}")
                        logger.info(f"[WEBHOOK] This indicates the lead was processed before")
                        
                except Exception as e:
                    logger.error(f"[WEBHOOK] ❌ ERROR creating ProcessedLead for {lid}: {e}")
                    logger.error(f"[WEBHOOK] Exception details: {type(e).__name__}: {str(e)}")
                    
                logger.info(f"[WEBHOOK] ================================================")
            else:
                logger.debug(f"[WEBHOOK] Skipping non-NEW_LEAD event: {upd.get('event_type')} for {upd.get('lead_id')}")

        biz_id = payload["data"].get("id")
        for lid in lead_ids:
            try:
                token = get_valid_business_token(biz_id)
                logger.info(
                    f"[WEBHOOK] Using business token for lead={lid}: {token}"
                )
            except ValueError:
                logger.error(
                    f"[WEBHOOK] Missing Yelp token for business={biz_id}; "
                    f"skipping lead={lid}"
                )
                continue
            except Exception:
                logger.exception(
                    f"[WEBHOOK] Error obtaining token for business={biz_id} "
                    f"lead={lid}"
                )
                continue
            url = f"https://api.yelp.com/v3/leads/{lid}/events"
            params = {"limit": 20}
            resp = requests.get(
                url, headers={"Authorization": f"Bearer {token}"}, params=params
            )
            logger.info(
                f"[WEBHOOK] Yelp response status for lead={lid}: {resp.status_code}"
            )

            if resp.status_code != 200:
                logger.error(
                    f"[WEBHOOK] Failed to fetch events for lead={lid}: {resp.text}"
                )
                continue

            events = resp.json().get("events", [])
            logger.info(f"[WEBHOOK] Received {len(events)} events for lead={lid}")

            for e in events:
                # Store every event but process phone logic only for new ones
                # The first consumer message that created the lead often lacks
                # a phone number.  We don't want that initial message to cancel
                # auto-response tasks, so we compare the event time with the
                # moment the lead was processed and skip older events.
                eid = e["id"]
                defaults = {
                    "lead_id": lid,
                    "event_type": e.get("event_type"),
                    "user_type": e.get("user_type"),
                    "user_id": e.get("user_id"),
                    "user_display_name": e.get("user_display_name", ""),
                    "text": e["event_content"].get("text")
                    or e["event_content"].get("fallback_text", ""),
                    "cursor": e.get("cursor", ""),
                    "time_created": e.get("time_created"),
                    "raw": e,
                    "from_backend": False,
                }
                
                # Покращена логіка визначення from_backend
                text = defaults.get("text", "")
                event_time_str = e.get("time_created")
                event_time = parse_datetime(event_time_str) if event_time_str else None
                
                # Спосіб 1: Перевірка чи вже існує аналогічний LeadEvent з from_backend=True
                if text and LeadEvent.objects.filter(
                    lead_id=lid, text=text, from_backend=True
                ).exists():
                    defaults["from_backend"] = True
                    logger.info(f"[WEBHOOK] 🔍 Setting from_backend=True (previously sent by us)")
                
                # Спосіб 2: Перевірка чи текст співпадає з активним або недавнім LeadPendingTask
                if not defaults["from_backend"] and text:
                    # Активні завдання
                    matching_active = LeadPendingTask.objects.filter(
                        lead_id=lid, text=text, active=True
                    ).exists()
                    
                    # Недавно виконані завдання (останні 10 хвилин)
                    from django.utils import timezone
                    ten_minutes_ago = timezone.now() - timezone.timedelta(minutes=10)
                    matching_recent = LeadPendingTask.objects.filter(
                        lead_id=lid, text=text, active=False, created_at__gte=ten_minutes_ago
                    ).exists()
                    
                    if matching_active or matching_recent:
                        defaults["from_backend"] = True
                        logger.info(f"[WEBHOOK] 🔍 Setting from_backend=True (matches LeadPendingTask)")
                
                # Спосіб 3: Timing-based detection для BIZ/BUSINESS events
                if (not defaults["from_backend"] and 
                    defaults.get("user_type") in ("BIZ", "BUSINESS") and 
                    event_time):
                    
                    processed_at = (
                        ProcessedLead.objects.filter(lead_id=lid)
                        .values_list("processed_at", flat=True)
                        .first()
                    )
                    
                    if processed_at:
                        time_diff = (event_time - processed_at).total_seconds()
                        # Якщо BIZ повідомлення прийшло менше ніж через 5 хвилин після обробки
                        if 0 < time_diff < 300:
                            defaults["from_backend"] = True
                            logger.info(f"[WEBHOOK] 🔍 Setting from_backend=True (BIZ timing: {time_diff:.1f}s)")
                
                # Спосіб 4: Content-based patterns для автоматичних повідомлень
                if not defaults["from_backend"] and text:
                    auto_patterns = [
                        "Hi there! Could you help me with my project?",
                        "Thank you for reaching out",
                        "We received your inquiry",
                        "Hello! I'm excited to help",
                        "Thanks for your interest",
                        "Hi! I'd love to help",
                        "Thank you for contacting",
                        "Hello there!",
                        "Hi! Thanks for reaching out",
                        "Great to hear from you"
                    ]
                    
                    for pattern in auto_patterns:
                        if pattern.lower() in text.lower():
                            defaults["from_backend"] = True
                            logger.info(f"[WEBHOOK] 🔍 Setting from_backend=True (content pattern)")
                            break
                
                logger.info(f"[WEBHOOK] Upserting LeadEvent id={eid} for lead={lid}")
                logger.info(f"[WEBHOOK] from_backend flag set to: {defaults['from_backend']}")
                obj, created = safe_update_or_create(
                    LeadEvent, defaults=defaults, event_id=eid
                )
                logger.info(f"[WEBHOOK] LeadEvent saved pk={obj.pk}, created={created}")

                logger.debug(
                    f"[WEBHOOK] Fetching processed_at for lead={lid}"
                )
                processed_at = (
                    ProcessedLead.objects.filter(lead_id=lid)
                    .values_list("processed_at", flat=True)
                    .first()
                )
                phone = _extract_phone(text)
                has_phone = bool(phone)
                
                # ❌ СТАРИЙ КОД: is_new = created
                # ✅ НОВИЙ КОД: Перевіряємо чи це справжня нова подія клієнта
                
                # Справжня нова подія = створена в БД AND час події після обробки ліда
                is_really_new_event = (
                    created and 
                    event_time and 
                    processed_at and 
                    event_time > processed_at
                )
                
                logger.info(f"[WEBHOOK] 🔍 EVENT ANALYSIS for lead={lid}, event_id={eid}")
                logger.info(f"[WEBHOOK] - Record created in DB: {created}")
                logger.info(f"[WEBHOOK] - Event time: {event_time_str}")
                logger.info(f"[WEBHOOK] - Lead processed at: {processed_at}")
                logger.info(f"[WEBHOOK] - Event after processing: {event_time > processed_at if event_time and processed_at else 'Cannot determine'}")
                logger.info(f"[WEBHOOK] - Is really new client event: {is_really_new_event}")
                
                # Замінюємо is_new на is_really_new_event
                is_new = is_really_new_event

                if e.get("event_type") == "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT":
                    logger.info(f"[WEBHOOK] 📱 CONSUMER_PHONE_NUMBER_OPT_IN_EVENT detected (second handler)")
                    logger.info(f"[WEBHOOK] ======== PHONE OPT-IN EVENT (EVENTS LOOP) ========")
                    logger.info(f"[WEBHOOK] Lead ID: {lid}")
                    logger.info(f"[WEBHOOK] Event ID: {eid}")
                    logger.info(f"[WEBHOOK] Event type: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT")
                    logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True")
                    
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    
                    logger.info(f"[WEBHOOK] LeadDetail update result:")
                    logger.info(f"[WEBHOOK] - Records updated: {updated}")
                    logger.info(f"[WEBHOOK] - This means {updated} LeadDetail(s) had phone_opt_in changed from False to True")
                    
                    if updated:
                        logger.info(f"[WEBHOOK] ✅ Phone opt-in updated successfully")
                        logger.info(f"[WEBHOOK] 🚀 TRIGGERING handle_phone_opt_in (from events loop)")
                        logger.info(f"[WEBHOOK] This will call _process_auto_response with phone_opt_in=True, phone_available=False")
                        self.handle_phone_opt_in(lid)
                        logger.info(f"[WEBHOOK] ✅ handle_phone_opt_in completed")
                    else:
                        logger.warning(f"[WEBHOOK] ⚠️ No LeadDetail records updated")
                        logger.warning(f"[WEBHOOK] This means the lead already had phone_opt_in=True")
                        logger.warning(f"[WEBHOOK] No additional auto-response will be triggered")
                    
                    logger.info(f"[WEBHOOK] ==============================================")

                if is_new and e.get("user_type") == "CONSUMER":
                    logger.info(f"[WEBHOOK] 👤 PROCESSING CONSUMER EVENT as TRULY NEW")
                    logger.info(f"[WEBHOOK] Event ID: {eid}")
                    logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                    logger.info(f"[WEBHOOK] Has phone in text: {has_phone}")
                    if has_phone:
                        logger.info(f"[WEBHOOK] Extracted phone: {phone}")
                    
                    pending = LeadPendingTask.objects.filter(
                        lead_id=lid,
                        phone_opt_in=False,
                        phone_available=False,
                        active=True,
                    ).exists()
                    logger.info(f"[WEBHOOK] Pending no-phone tasks exist: {pending}")
                    
                    if has_phone:
                        logger.info(f"[WEBHOOK] 📞 CLIENT PROVIDED PHONE NUMBER")
                        logger.info(f"[WEBHOOK] ========== PHONE DETECTED IN TEXT ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Extracted phone: {phone}")
                        logger.info(f"[WEBHOOK] Text that contained phone: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                        logger.info(f"[WEBHOOK] Pending no-phone tasks exist: {pending}")
                        logger.info(f"[WEBHOOK] Updating LeadDetail with phone_in_text=True, phone_number={phone}")
                        
                        LeadDetail.objects.filter(lead_id=lid).update(
                            phone_in_text=True, phone_number=phone
                        )
                        
                        logger.info(f"[WEBHOOK] ✅ LeadDetail updated with phone information")
                        
                        try:
                            from .utils import update_phone_in_sheet

                            update_phone_in_sheet(lid, phone)
                            logger.info(f"[WEBHOOK] ✅ Phone updated in Google Sheets")
                        except Exception:
                            logger.exception(
                                "[WEBHOOK] Failed to update phone in sheet"
                            )
                        
                        if pending:
                            logger.info(f"[WEBHOOK] 🔄 PENDING TASKS EXIST - switching scenario")
                            reason = "Client responded with a number → switched to the 'phone available' scenario"
                            logger.info(f"[WEBHOOK] 🔄 SWITCHING TO PHONE AVAILABLE scenario")
                            logger.info(f"[WEBHOOK] 🚀 TRIGGERING handle_phone_available (pending tasks exist)")
                            logger.info(f"[WEBHOOK] This will call _process_auto_response with phone_opt_in=False, phone_available=True")
                            self.handle_phone_available(lid, reason=reason)
                            logger.info(f"[WEBHOOK] ✅ handle_phone_available completed")
                        else:
                            logger.info(f"[WEBHOOK] 🔄 NO PENDING TASKS - triggering phone available flow")
                            logger.info(f"[WEBHOOK] 🚀 TRIGGERING handle_phone_available (no pending tasks)")
                            logger.info(f"[WEBHOOK] This will call _process_auto_response with phone_opt_in=False, phone_available=True")
                            self.handle_phone_available(lid)
                            logger.info(f"[WEBHOOK] ✅ handle_phone_available completed")
                        
                        logger.info(f"[WEBHOOK] ==============================================")
                    elif pending:
                        logger.info(f"[WEBHOOK] 🚫 CLIENT RESPONDED WITHOUT PHONE NUMBER")
                        logger.info(f"[WEBHOOK] ========== CUSTOMER REPLY SCENARIO (NO PHONE) ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                        logger.info(f"[WEBHOOK] Has pending no-phone tasks: {pending}")
                        logger.info(f"[WEBHOOK] Phone number found in text: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ This SHOULD trigger Customer Reply SMS but currently only cancels tasks")
                        logger.info(f"[WEBHOOK] 🎯 SMS DECISION ANALYSIS:")
                        logger.info(f"[WEBHOOK] - Scenario: Customer Reply (phone_opt_in=False, phone_available=False)")
                        logger.info(f"[WEBHOOK] - Current behavior: Only cancel pending tasks")
                        logger.info(f"[WEBHOOK] - Missing: _process_auto_response call for Customer Reply SMS")
                        
                        reason = "Client responded, but no number was found"
                        self._cancel_no_phone_tasks(lid, reason=reason)
                        
                        logger.info(f"[WEBHOOK] 💡 TRIGGERING CUSTOMER REPLY SMS:")
                        logger.info(f"[WEBHOOK] Calling: self._process_auto_response({lid}, phone_opt_in=False, phone_available=False)")
                        try:
                            self._process_auto_response(lid, phone_opt_in=False, phone_available=False)
                            logger.info(f"[WEBHOOK] ✅ Customer Reply SMS processing completed")
                        except Exception as e:
                            logger.error(f"[WEBHOOK] ❌ Customer Reply SMS processing failed: {e}")
                            logger.exception(f"[WEBHOOK] Customer Reply SMS exception details")
                        logger.info(f"[WEBHOOK] ==============================================")
                    else:
                        logger.info(f"[WEBHOOK] ℹ️ CLIENT RESPONDED but no pending tasks to handle")
                        logger.info(f"[WEBHOOK] ========== CUSTOMER REPLY SCENARIO (NO PENDING TASKS) ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                        logger.info(f"[WEBHOOK] Has pending no-phone tasks: {pending}")
                        logger.info(f"[WEBHOOK] Phone number found in text: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ This COULD BE a Customer Reply SMS scenario")
                        logger.info(f"[WEBHOOK] 🎯 SMS DECISION ANALYSIS:")
                        logger.info(f"[WEBHOOK] - Scenario: Customer Reply (phone_opt_in=False, phone_available=False)")
                        logger.info(f"[WEBHOOK] - Current behavior: No action taken")
                        logger.info(f"[WEBHOOK] - Missing: _process_auto_response call for Customer Reply SMS")
                        
                        logger.info(f"[WEBHOOK] 💡 TRIGGERING CUSTOMER REPLY SMS:")
                        logger.info(f"[WEBHOOK] Calling: self._process_auto_response({lid}, phone_opt_in=False, phone_available=False)")
                        try:
                            self._process_auto_response(lid, phone_opt_in=False, phone_available=False)
                            logger.info(f"[WEBHOOK] ✅ Customer Reply SMS processing completed")
                        except Exception as e:
                            logger.error(f"[WEBHOOK] ❌ Customer Reply SMS processing failed: {e}")
                            logger.exception(f"[WEBHOOK] Customer Reply SMS exception details")
                        logger.info(f"[WEBHOOK] ==============================================")
                elif created and e.get("user_type") == "CONSUMER":
                    logger.info(f"[WEBHOOK] 📊 CONSUMER EVENT RECORDED but NOT PROCESSED as new")
                    logger.info(f"[WEBHOOK] Reason: Event happened BEFORE lead processing")
                    logger.info(f"[WEBHOOK] Event time: {event_time_str}")
                    logger.info(f"[WEBHOOK] Processed at: {processed_at}")
                    logger.info(f"[WEBHOOK] This prevents false triggering of task cancellations")
                elif is_new and defaults.get("user_type") in ("BIZ", "BUSINESS"):
                    logger.info(f"[WEBHOOK] 🏢 BUSINESS USER EVENT DETECTED")
                    logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                    logger.info(f"[WEBHOOK] from_backend flag: {defaults.get('from_backend')}")
                    
                    # Перевіряємо чи це наше власне повідомлення
                    is_our_message = False
                    detection_reasons = []
                    
                    # Спосіб 1: Перевірка по from_backend (стара логіка)
                    if defaults.get("from_backend"):
                        is_our_message = True
                        detection_reasons.append("from_backend=True")
                        logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (from_backend=True)")
                    
                    # Спосіб 2: Перевірка чи текст відповідає активному або недавно неактивному завданню
                    if not is_our_message and text:
                        # Перевіряємо активні задачі
                        matching_active_tasks = LeadPendingTask.objects.filter(
                            lead_id=lid,
                            text=text,
                            active=True
                        ).exists()
                        
                        # Перевіряємо недавно деактивовані задачі (останні 10 хвилин)
                        from django.utils import timezone
                        ten_minutes_ago = timezone.now() - timezone.timedelta(minutes=10)
                        matching_recent_tasks = LeadPendingTask.objects.filter(
                            lead_id=lid,
                            text=text,
                            active=False,
                            created_at__gte=ten_minutes_ago
                        ).exists()
                        
                        if matching_active_tasks:
                            is_our_message = True
                            detection_reasons.append("matches active task")
                            logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (matches active task)")
                        elif matching_recent_tasks:
                            is_our_message = True
                            detection_reasons.append("matches recently executed task")
                            logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (matches recently executed task)")
                        else:
                            logger.info(f"[WEBHOOK] ❌ Text does NOT match any active or recent tasks")
                    
                    # Спосіб 3: Перевірка чи текст був відправлений раніше нашою системою
                    if not is_our_message and text:
                        sent_by_us = LeadEvent.objects.filter(
                            lead_id=lid,
                            text=text,
                            from_backend=True
                        ).exists()
                        if sent_by_us:
                            is_our_message = True
                            detection_reasons.append("previously sent by backend")
                            logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (previously sent by backend)")
                        else:
                            logger.info(f"[WEBHOOK] ❌ Text was NOT previously sent by our backend")
                    
                    # Спосіб 4: Content-based detection (автоматичні патерни)
                    if not is_our_message and text:
                        # Патерни що вказують на автоматичні повідомлення
                        auto_patterns = [
                            "Hi there! Could you help me with my project?",  # Greeting template
                            "Thank you for reaching out",
                            "We received your inquiry",
                            "Hello! I'm excited to help",
                            "Thanks for your interest",
                            "Hi! I'd love to help",
                            "Thank you for contacting",
                            "Hello there!",
                            "Hi! Thanks for reaching out",
                            "Great to hear from you"
                        ]
                        
                        for pattern in auto_patterns:
                            if pattern.lower() in text.lower():
                                is_our_message = True
                                detection_reasons.append(f"content pattern: '{pattern}'")
                                logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (content pattern: '{pattern}')")
                                break
                        
                        if not is_our_message:
                            logger.info(f"[WEBHOOK] ❌ Text does NOT match any known automated patterns")
                    
                    # Спосіб 5: АГРЕСИВНИЙ timing-based detection
                    if not is_our_message and event_time and processed_at:
                        time_diff_seconds = (event_time - processed_at).total_seconds()
                        logger.info(f"[WEBHOOK] 🕐 Event happened {time_diff_seconds:.1f}s after processing")
                        
                        # Якщо повідомлення прийшло менше ніж через 10 хвилин після обробки
                        if 0 < time_diff_seconds < 600:  # 10 хвилин
                            # Додаткові індикатори автоматичного повідомлення
                            likely_automated = False
                            
                            # Перевіряємо чи є активні задачі взагалі
                            has_active_tasks = LeadPendingTask.objects.filter(
                                lead_id=lid, active=True
                            ).exists()
                            
                            # Якщо є активні задачі і повідомлення в межах 10 хвилин - ймовірно наше
                            if has_active_tasks and time_diff_seconds < 600:
                                likely_automated = True
                                logger.info(f"[WEBHOOK] 🎯 LIKELY automated (has active tasks + timing)")
                            
                            # Якщо повідомлення дуже скоро після обробки (менше 5 хвилин) - майже точно наше
                            if time_diff_seconds < 300:  # 5 хвилин
                                likely_automated = True
                                logger.info(f"[WEBHOOK] 🎯 VERY LIKELY automated (timing < 5 min)")
                            
                            # Greeting зазвичай надсилається через 1-2 хвилини після обробки
                            if 60 < time_diff_seconds < 180:  # 1-3 хвилини
                                likely_automated = True
                                logger.info(f"[WEBHOOK] 🎯 LIKELY greeting message (timing in greeting window)")
                            
                            if likely_automated:
                                is_our_message = True
                                detection_reasons.append(f"aggressive timing detection ({time_diff_seconds:.1f}s)")
                                logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (aggressive timing detection)")
                        else:
                            logger.info(f"[WEBHOOK] ⏰ Event too late to be automated ({time_diff_seconds:.1f}s)")
                    
                    # Спосіб 6: Перевірка user_display_name чи це не система
                    if not is_our_message:
                        user_display_name = e.get('user_display_name', '').strip()
                        business_name_patterns = [
                            'system', 'automated', 'bot', 'auto', 'yelp',
                            # Можна додати назву бізнесу якщо відома
                        ]
                        
                        if user_display_name and any(pattern.lower() in user_display_name.lower() for pattern in business_name_patterns):
                            is_our_message = True
                            detection_reasons.append(f"user_display_name: '{user_display_name}'")
                            logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (user_display_name: '{user_display_name}')")
                        else:
                            logger.info(f"[WEBHOOK] ❌ user_display_name does not suggest automation: '{user_display_name}'")
                        
                    # Фінальне рішення
                    if is_our_message:
                        logger.info(f"[WEBHOOK] 🤖 CONFIRMED: This is OUR automated message")
                        logger.info(f"[WEBHOOK] Detection reasons: {', '.join(detection_reasons)}")
                        logger.info(f"[WEBHOOK] No action needed - this is expected system behavior")
                    else:
                        logger.info(f"[WEBHOOK] 👨‍💼 CONFIRMED: Real business user response in Yelp dashboard")
                        logger.info(f"[WEBHOOK] Will cancel all active tasks as business took over")
                        reason = "Business user responded in Yelp dashboard"
                        self._cancel_all_tasks(lid, reason=reason)
                elif e.get("user_type") == "CONSUMER":
                    logger.info(f"[WEBHOOK] 📝 CONSUMER EVENT SKIPPED")
                    logger.info(f"[WEBHOOK] Record already existed in DB - not a new client response")
                else:
                    logger.debug(f"[WEBHOOK] 📄 OTHER EVENT TYPE")
                    logger.debug(f"[WEBHOOK] Event ID: {eid}")
                    logger.debug(f"[WEBHOOK] User type: {e.get('user_type')}")
                    logger.debug(f"[WEBHOOK] Event type: {e.get('event_type')}")
                    logger.debug(f"[WEBHOOK] No action required for this event type")

        return Response({"status": "received"}, status=status.HTTP_201_CREATED)

    def handle_new_lead(self, lead_id: str):
        logger.info(f"[AUTO-RESPONSE] 🆕 STARTING handle_new_lead")
        logger.info(f"[AUTO-RESPONSE] =================== NEW LEAD HANDLER ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: NEW_LEAD")
        logger.info(f"[AUTO-RESPONSE] Scenario: Basic new lead (phone_opt_in=False, phone_available=False)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: ProcessedLead was created for this lead")
        logger.info(f"[AUTO-RESPONSE] About to call _process_auto_response")
        
        try:
            self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)
            logger.info(f"[AUTO-RESPONSE] ✅ handle_new_lead completed successfully for {lead_id}")
        except Exception as e:
            logger.error(f"[AUTO-RESPONSE] ❌ handle_new_lead failed for {lead_id}: {e}")
            logger.exception(f"[AUTO-RESPONSE] Exception details for handle_new_lead")
            raise

    def handle_phone_opt_in(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 📱 STARTING handle_phone_opt_in")
        logger.info(f"[AUTO-RESPONSE] ================ PHONE OPT-IN HANDLER ================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_OPT_IN")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone opt-in received (phone_opt_in=True, phone_available=False)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT received")
        
        # ⭐ SMART FRESHNESS CHECK: Skip only if ProcessedLead is OLD (not created recently)
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        logger.info(f"[AUTO-RESPONSE] ProcessedLead exists for {lead_id}: {pl is not None}")
        
        if pl:
            time_since_processed = timezone.now() - pl.processed_at
            freshness_threshold_minutes = 5  # 5 minutes threshold for "fresh" ProcessedLead
            
            logger.info(f"[AUTO-RESPONSE] ProcessedLead freshness check:")
            logger.info(f"[AUTO-RESPONSE] - Processed at: {pl.processed_at}")
            logger.info(f"[AUTO-RESPONSE] - Time since processed: {time_since_processed.total_seconds():.1f} seconds")
            logger.info(f"[AUTO-RESPONSE] - Freshness threshold: {freshness_threshold_minutes} minutes")
            
            if time_since_processed > timedelta(minutes=freshness_threshold_minutes):
                logger.info(f"[AUTO-RESPONSE] ⏭️ SKIPPING phone opt-in auto-response: ProcessedLead too old")
                logger.info(f"[AUTO-RESPONSE] This indicates the lead was processed before this webhook")
                logger.info(f"[AUTO-RESPONSE] 🛑 EARLY RETURN - ProcessedLead not fresh")
                return
            else:
                logger.info(f"[AUTO-RESPONSE] ✅ ProcessedLead is fresh - proceeding with phone opt-in")
                logger.info(f"[AUTO-RESPONSE] This ProcessedLead was likely created during this webhook processing")
        else:
            logger.info(f"[AUTO-RESPONSE] ✅ No ProcessedLead found - proceeding with phone opt-in flow")
        logger.info(f"[AUTO-RESPONSE] Step 1: Cancelling no-phone tasks")
        
        try:
            self._cancel_no_phone_tasks(lead_id, reason)
            logger.info(f"[AUTO-RESPONSE] Step 2: Starting auto-response for phone opt-in scenario")
            self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)
            logger.info(f"[AUTO-RESPONSE] ✅ handle_phone_opt_in completed successfully for {lead_id}")
        except Exception as e:
            logger.error(f"[AUTO-RESPONSE] ❌ handle_phone_opt_in failed for {lead_id}: {e}")
            logger.exception(f"[AUTO-RESPONSE] Exception details for handle_phone_opt_in")
            raise

    def handle_phone_available(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 📞 STARTING handle_phone_available")
        logger.info(f"[AUTO-RESPONSE] ============== PHONE AVAILABLE HANDLER ==============")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone number provided (phone_opt_in=False, phone_available=True)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: Phone number found in consumer text")
        
        # ⭐ SMART FRESHNESS CHECK: Skip only if ProcessedLead is OLD (not created recently)
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        logger.info(f"[AUTO-RESPONSE] ProcessedLead exists for {lead_id}: {pl is not None}")
        
        if pl:
            time_since_processed = timezone.now() - pl.processed_at
            freshness_threshold_minutes = 5  # 5 minutes threshold for "fresh" ProcessedLead
            
            logger.info(f"[AUTO-RESPONSE] ProcessedLead freshness check:")
            logger.info(f"[AUTO-RESPONSE] - Processed at: {pl.processed_at}")
            logger.info(f"[AUTO-RESPONSE] - Time since processed: {time_since_processed.total_seconds():.1f} seconds")
            logger.info(f"[AUTO-RESPONSE] - Freshness threshold: {freshness_threshold_minutes} minutes")
            
            if time_since_processed > timedelta(minutes=freshness_threshold_minutes):
                logger.info(f"[AUTO-RESPONSE] ⏭️ SKIPPING phone available auto-response: ProcessedLead too old")
                logger.info(f"[AUTO-RESPONSE] This indicates the lead was processed before this webhook")
                logger.info(f"[AUTO-RESPONSE] 🛑 EARLY RETURN - ProcessedLead not fresh")
                return
            else:
                logger.info(f"[AUTO-RESPONSE] ✅ ProcessedLead is fresh - proceeding with phone available")
                logger.info(f"[AUTO-RESPONSE] This ProcessedLead was likely created during this webhook processing")
        else:
            logger.info(f"[AUTO-RESPONSE] ✅ No ProcessedLead found - proceeding with phone available flow")
        logger.info(f"[AUTO-RESPONSE] Step 1: Cancelling no-phone tasks")
        
        try:
            self._cancel_no_phone_tasks(lead_id, reason)
            logger.info(f"[AUTO-RESPONSE] Step 2: Starting auto-response for phone available scenario")
            self._process_auto_response(lead_id, phone_opt_in=False, phone_available=True)
            logger.info(f"[AUTO-RESPONSE] ✅ handle_phone_available completed successfully for {lead_id}")
        except Exception as e:
            logger.error(f"[AUTO-RESPONSE] ❌ handle_phone_available failed for {lead_id}: {e}")
            logger.exception(f"[AUTO-RESPONSE] Exception details for handle_phone_available")
            raise

    def _cancel_no_phone_tasks(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_no_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Looking for pending tasks with: phone_opt_in=False, phone_available=False, active=True")
        
        pending = LeadPendingTask.objects.filter(
            lead_id=lead_id, phone_opt_in=False, phone_available=False, active=True
        )
        pending_count = pending.count()
        logger.info(f"[AUTO-RESPONSE] Found {pending_count} pending no-phone tasks to cancel")
        
        if pending_count == 0:
            logger.info(f"[AUTO-RESPONSE] No no-phone tasks to cancel for {lead_id}")
            return
            
        queue = django_rq.get_queue("default")
        scheduler = django_rq.get_scheduler("default")
        
        cancelled_count = 0
        error_count = 0
        
        for p in pending:
            logger.info(f"[AUTO-RESPONSE] Cancelling task: {p.task_id} for lead {lead_id}")
            logger.info(f"[AUTO-RESPONSE] Task text preview: {p.text[:50]}...")
            logger.info(f"[AUTO-RESPONSE] Task created at: {p.created_at}")
            
            try:
                job = queue.fetch_job(p.task_id)
                if job:
                    job.cancel()
                    logger.info(f"[AUTO-RESPONSE] ✅ Queue job {p.task_id} cancelled successfully")
                else:
                    logger.info(f"[AUTO-RESPONSE] ⚠️ Queue job {p.task_id} not found (might be already processed)")
                    
                scheduler.cancel(p.task_id)
                logger.info(f"[AUTO-RESPONSE] ✅ Scheduler job {p.task_id} cancelled successfully")
                cancelled_count += 1
                
            except Exception as exc:
                logger.error(f"[AUTO-RESPONSE] ❌ Error cancelling task {p.task_id}: {exc}")
                logger.exception(f"[AUTO-RESPONSE] Exception details for task cancellation")
                error_count += 1
                
            # Update task status
            p.active = False
            p.save(update_fields=["active"])
            logger.info(f"[AUTO-RESPONSE] ✅ LeadPendingTask {p.task_id} marked as inactive")
            
            # Update Celery log
            updated_logs = CeleryTaskLog.objects.filter(task_id=p.task_id).update(
                status="REVOKED", result=reason
            )
            logger.info(f"[AUTO-RESPONSE] ✅ Updated {updated_logs} CeleryTaskLog entries for {p.task_id}")
            
        logger.info(f"[AUTO-RESPONSE] 📊 _cancel_no_phone_tasks summary for {lead_id}:")
        logger.info(f"[AUTO-RESPONSE] - Tasks found: {pending_count}")
        logger.info(f"[AUTO-RESPONSE] - Tasks cancelled successfully: {cancelled_count}")
        logger.info(f"[AUTO-RESPONSE] - Tasks with errors: {error_count}")
        logger.info(f"[AUTO-RESPONSE] ✅ _cancel_no_phone_tasks completed")

    def _cancel_all_tasks(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 🛑 STARTING _cancel_all_tasks")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Looking for ALL pending tasks with: active=True")
        
        pending = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        pending_count = pending.count()
        logger.info(f"[AUTO-RESPONSE] Found {pending_count} pending tasks to cancel")
        
        if pending_count == 0:
            logger.info(f"[AUTO-RESPONSE] No tasks to cancel for {lead_id}")
            return
            
        # Log details about tasks being cancelled
        for p in pending:
            logger.info(f"[AUTO-RESPONSE] Task to cancel: {p.task_id}")
            logger.info(f"[AUTO-RESPONSE] - Text: {p.text[:50]}...")
            logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {p.phone_opt_in}")
            logger.info(f"[AUTO-RESPONSE] - phone_available: {p.phone_available}")
            logger.info(f"[AUTO-RESPONSE] - Created: {p.created_at}")
            
        queue = django_rq.get_queue("default")
        scheduler = django_rq.get_scheduler("default")
        
        cancelled_count = 0
        error_count = 0
        
        for p in pending:
            logger.info(f"[AUTO-RESPONSE] Cancelling task: {p.task_id}")
            
            try:
                job = queue.fetch_job(p.task_id)
                if job:
                    job.cancel()
                    logger.info(f"[AUTO-RESPONSE] ✅ Queue job {p.task_id} cancelled successfully")
                else:
                    logger.info(f"[AUTO-RESPONSE] ⚠️ Queue job {p.task_id} not found (might be already processed)")
                    
                scheduler.cancel(p.task_id)
                logger.info(f"[AUTO-RESPONSE] ✅ Scheduler job {p.task_id} cancelled successfully")
                cancelled_count += 1
                
            except Exception as exc:
                logger.error(f"[AUTO-RESPONSE] ❌ Error cancelling task {p.task_id}: {exc}")
                logger.exception(f"[AUTO-RESPONSE] Exception details for task cancellation")
                error_count += 1
                
            # Update task status
            p.active = False
            p.save(update_fields=["active"])
            logger.info(f"[AUTO-RESPONSE] ✅ LeadPendingTask {p.task_id} marked as inactive")
            
            # Update Celery log
            updated_logs = CeleryTaskLog.objects.filter(task_id=p.task_id).update(
                status="REVOKED", result=reason
            )
            logger.info(f"[AUTO-RESPONSE] ✅ Updated {updated_logs} CeleryTaskLog entries for {p.task_id}")
            
        logger.info(f"[AUTO-RESPONSE] 📊 _cancel_all_tasks summary for {lead_id}:")
        logger.info(f"[AUTO-RESPONSE] - Tasks found: {pending_count}")
        logger.info(f"[AUTO-RESPONSE] - Tasks cancelled successfully: {cancelled_count}")
        logger.info(f"[AUTO-RESPONSE] - Tasks with errors: {error_count}")
        logger.info(f"[AUTO-RESPONSE] ✅ _cancel_all_tasks completed")

    def _process_auto_response(
        self, lead_id: str, phone_opt_in: bool, phone_available: bool
    ):
        logger.info(f"[AUTO-RESPONSE] 🔧 STARTING _process_auto_response")
        logger.info(f"[AUTO-RESPONSE] Parameters:")
        logger.info(f"[AUTO-RESPONSE] - Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {phone_opt_in}")
        logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
        
        # Determine reason for SMS based on scenario
        if phone_opt_in:
            reason = "Phone Opt-in"
        elif phone_available:
            reason = "Phone Number Found"
        else:
            reason = "Customer Reply"
        
        logger.info(f"[AUTO-RESPONSE] SMS Reason: {reason}")
        
        # Step 1: Look up settings
        logger.info(f"[AUTO-RESPONSE] 🔍 STEP 1: Looking up AutoResponseSettings")
        logger.info(f"[AUTO-RESPONSE] ========== SMS SETTINGS LOOKUP ==========")
        logger.info(f"[AUTO-RESPONSE] Search criteria:")
        logger.info(f"[AUTO-RESPONSE] - business__isnull=True (global settings)")
        logger.info(f"[AUTO-RESPONSE] - phone_opt_in={phone_opt_in}")
        logger.info(f"[AUTO-RESPONSE] - phone_available={phone_available}")
        
        # Debug: Show all AutoResponseSettings in database
        all_auto_settings = AutoResponseSettings.objects.all()
        logger.info(f"[AUTO-RESPONSE] 📊 ALL AutoResponseSettings in database:")
        if all_auto_settings.exists():
            for setting in all_auto_settings:
                logger.info(f"[AUTO-RESPONSE] - ID={setting.id}, business={setting.business}, phone_opt_in={setting.phone_opt_in}, phone_available={setting.phone_available}, enabled={setting.enabled}")
                if hasattr(setting, 'sms_on_customer_reply'):
                    logger.info(f"[AUTO-RESPONSE]   sms_on_customer_reply={setting.sms_on_customer_reply}, sms_on_phone_found={setting.sms_on_phone_found}, sms_on_phone_opt_in={setting.sms_on_phone_opt_in}")
        else:
            logger.info(f"[AUTO-RESPONSE] ❌ NO AutoResponseSettings found in database!")
        
        default_settings = AutoResponseSettings.objects.filter(
            business__isnull=True,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available,
        ).first()
        logger.info(f"[AUTO-RESPONSE] 🎯 Default settings found: {default_settings is not None}")
        if default_settings:
            logger.info(f"[AUTO-RESPONSE] ✅ Default settings details:")
            logger.info(f"[AUTO-RESPONSE] - ID: {default_settings.id}")
            logger.info(f"[AUTO-RESPONSE] - enabled: {default_settings.enabled}")
            logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {default_settings.phone_opt_in}")
            logger.info(f"[AUTO-RESPONSE] - phone_available: {default_settings.phone_available}")
            if hasattr(default_settings, 'sms_on_customer_reply'):
                logger.info(f"[AUTO-RESPONSE] - sms_on_customer_reply: {default_settings.sms_on_customer_reply}")
                logger.info(f"[AUTO-RESPONSE] - sms_on_phone_found: {default_settings.sms_on_phone_found}")
                logger.info(f"[AUTO-RESPONSE] - sms_on_phone_opt_in: {default_settings.sms_on_phone_opt_in}")
        else:
            logger.error(f"[AUTO-RESPONSE] ❌ NO MATCHING AutoResponseSettings!")
            logger.error(f"[AUTO-RESPONSE] This means SMS won't be sent for {reason} scenario")
            logger.error(f"[AUTO-RESPONSE] Need AutoResponseSettings with business=null, phone_opt_in={phone_opt_in}, phone_available={phone_available}")
        
        logger.debug(
            f"[AUTO-RESPONSE] Looking up ProcessedLead for lead_id={lead_id}"
        )
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        logger.info(f"[AUTO-RESPONSE] ProcessedLead found: {pl is not None}")
        
        biz_settings = None
        if pl:
            logger.info(f"[AUTO-RESPONSE] ProcessedLead details:")
            logger.info(f"[AUTO-RESPONSE] - ID: {pl.id}")
            logger.info(f"[AUTO-RESPONSE] - Business ID: {pl.business_id}")
            logger.info(f"[AUTO-RESPONSE] - Lead ID: {pl.lead_id}")
            logger.info(f"[AUTO-RESPONSE] - Processed at: {pl.processed_at}")
            
            biz_settings = AutoResponseSettings.objects.filter(
                business__business_id=pl.business_id,
                phone_opt_in=phone_opt_in,
                phone_available=phone_available,
            ).first()
            logger.info(f"[AUTO-RESPONSE] Business-specific settings found: {biz_settings is not None}")
            if biz_settings:
                logger.info(f"[AUTO-RESPONSE] Business settings ID: {biz_settings.id}, enabled: {biz_settings.enabled}")
            
            # Step 2: Get authentication token (optional for SMS)
            logger.info(f"[AUTO-RESPONSE] 🔐 STEP 2: Getting authentication token")
            token = None
            has_token = False
            try:
                token = get_valid_business_token(pl.business_id)
                has_token = True
                logger.info(f"[AUTO-RESPONSE] ✅ Successfully obtained business token")
                logger.debug(
                    f"[AUTO-RESPONSE] Obtained business token for {pl.business_id}: {token[:20]}..."
                )
            except ValueError as e:
                logger.warning(
                    f"[AUTO-RESPONSE] ⚠️ No token for business {pl.business_id}; continuing for SMS functionality"
                )
                logger.warning(f"[AUTO-RESPONSE] Token error: {e}")
                logger.warning(f"[AUTO-RESPONSE] Auto-response messages will be disabled, but SMS can still work")
                has_token = False
        else:
            qs = ProcessedLead.objects.filter(lead_id=lead_id)
            logger.error(
                "[AUTO-RESPONSE] ❌ Cannot determine business for lead=%s (found %s ProcessedLead records)",
                lead_id,
                qs.count(),
            )
            if qs.exists():
                logger.error(
                    "[AUTO-RESPONSE] Sample ProcessedLead records: %s",
                    list(qs.values("id", "business_id", "processed_at")[:3]),
                )
            return

        auto_settings = biz_settings if biz_settings is not None else default_settings
        if auto_settings is None:
            logger.info("[AUTO-RESPONSE] AutoResponseSettings not configured")
        
        # Enhanced logging for settings selection
        logger.info(f"[AUTO-RESPONSE] ========== SETTINGS SELECTION ==========")
        logger.info(f"[AUTO-RESPONSE] Business-specific settings available: {biz_settings is not None}")
        logger.info(f"[AUTO-RESPONSE] Default settings available: {default_settings is not None}")
        logger.info(f"[AUTO-RESPONSE] Final settings selected: {auto_settings is not None}")
        
        if auto_settings:
            logger.info(f"[AUTO-RESPONSE] SELECTED AutoResponseSettings:")
            logger.info(f"[AUTO-RESPONSE] - Settings ID: {auto_settings.id}")
            logger.info(f"[AUTO-RESPONSE] - Settings type: {'Business-specific' if biz_settings is not None else 'Default'}")
            logger.info(f"[AUTO-RESPONSE] - Business: {auto_settings.business.name if auto_settings.business else 'Global (None)'}")
            logger.info(f"[AUTO-RESPONSE] - Enabled: {auto_settings.enabled}")
            logger.info(f"[AUTO-RESPONSE] - phone_opt_in: {auto_settings.phone_opt_in}")
            logger.info(f"[AUTO-RESPONSE] - phone_available: {auto_settings.phone_available}")
            logger.info(f"[AUTO-RESPONSE] - use_ai_greeting: {getattr(auto_settings, 'use_ai_greeting', False)}")
            logger.info(f"[AUTO-RESPONSE] - export_to_sheets: {auto_settings.export_to_sheets}")
            logger.info(f"[AUTO-RESPONSE] - greeting_template: {auto_settings.greeting_template[:50]}...")
            
            # ⭐ DETAILED SMS SETTINGS LOGGING ⭐
            logger.info(f"[AUTO-RESPONSE] 🚨 SMS SETTINGS ANALYSIS:")
            logger.info(f"[AUTO-RESPONSE] - sms_on_phone_found: {getattr(auto_settings, 'sms_on_phone_found', 'MISSING FIELD')}")
            logger.info(f"[AUTO-RESPONSE] - sms_on_customer_reply: {getattr(auto_settings, 'sms_on_customer_reply', 'MISSING FIELD')}")
            logger.info(f"[AUTO-RESPONSE] - sms_on_phone_opt_in: {getattr(auto_settings, 'sms_on_phone_opt_in', 'MISSING FIELD')}")
            logger.info(f"[AUTO-RESPONSE] SMS processing will be handled in Step 3 below")
        else:
            logger.warning(f"[AUTO-RESPONSE] ❌ NO AutoResponseSettings found!")
            logger.warning(f"[AUTO-RESPONSE] Query filters used:")
            logger.warning(f"[AUTO-RESPONSE] - phone_opt_in: {phone_opt_in}")
            logger.warning(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
            logger.warning(f"[AUTO-RESPONSE] - business_id: {pl.business_id if pl else 'N/A'}")
        
        biz_id = pl.business_id if pl else None
        logger.info(
            "[AUTO-RESPONSE] Using AutoResponseSettings for business=%s, lead=%s, export_to_sheets=%s",
            biz_id,
            lead_id,
            getattr(auto_settings, "export_to_sheets", None),
        )

        # Step 3: Process SMS notifications (works without Yelp token)
        logger.info(f"[AUTO-RESPONSE] 📱 STEP 3: Processing SMS notifications")
        if auto_settings:
            should_send_sms = False
            sms_reason_field = ""
            if phone_opt_in:
                should_send_sms = getattr(auto_settings, 'sms_on_phone_opt_in', False)
                sms_reason_field = "sms_on_phone_opt_in"
            elif phone_available:
                should_send_sms = getattr(auto_settings, 'sms_on_phone_found', False)
                sms_reason_field = "sms_on_phone_found"
            else:
                should_send_sms = getattr(auto_settings, 'sms_on_customer_reply', False)
                sms_reason_field = "sms_on_customer_reply"
            
            final_sms_decision = should_send_sms and auto_settings.enabled
            logger.info(f"[AUTO-RESPONSE] 📲 SMS PROCESSING FOR SCENARIO '{reason}':")
            logger.info(f"[AUTO-RESPONSE] - Field checked: {sms_reason_field}")
            logger.info(f"[AUTO-RESPONSE] - SMS flag: {should_send_sms}")
            logger.info(f"[AUTO-RESPONSE] - Settings enabled: {auto_settings.enabled}")
            logger.info(f"[AUTO-RESPONSE] - FINAL SMS DECISION: {final_sms_decision}")
            
            if final_sms_decision:
                logger.info(f"[AUTO-RESPONSE] 🚀 SENDING SMS for {reason} scenario")
                # TODO: Implement actual SMS sending logic here
                # This would call send_sms() with appropriate parameters
                logger.info(f"[AUTO-RESPONSE] SMS sending not yet implemented in _process_auto_response")
            else:
                logger.info(f"[AUTO-RESPONSE] ⏭️ Skipping SMS - not enabled or configured")
        
        # Step 4: Process Yelp auto-response (requires token)
        if not has_token:
            logger.warning(f"[AUTO-RESPONSE] ⚠️ No Yelp token - skipping auto-response messages")
            logger.warning(f"[AUTO-RESPONSE] Only SMS processing was performed")
            return
        
        logger.info(f"[AUTO-RESPONSE] 🔗 STEP 4: Processing Yelp auto-response messages")
        detail_url = f"https://api.yelp.com/v3/leads/{lead_id}"
        headers = {"Authorization": f"Bearer {token}"}
        logger.debug(
            f"[AUTO-RESPONSE] Fetching lead details from {detail_url} using token {token[:20]}..."
        )
        resp = requests.get(detail_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            source = f"business {pl.business_id}" if pl else "unknown"
            logger.error(
                f"[AUTO-RESPONSE] DETAIL ERROR lead={lead_id}, business_id={pl.business_id if pl else 'N/A'}, "
                f"token_source={source}, token={token[:20]}..., status={resp.status_code}, body={resp.text}"
            )
            return
        d = resp.json()

        last_time = None
        ev_resp = requests.get(
            f"{detail_url}/events", headers=headers, params={"limit": 1}, timeout=10
        )
        if ev_resp.status_code == 200:
            evs = ev_resp.json().get("events", [])
            if evs:
                last_time = evs[0]["time_created"]
        logger.info(f"[AUTO-RESPONSE] Last event time for lead={lead_id}: {last_time}")

        raw_proj = d.get("project", {}) or {}
        raw_answers = raw_proj.get("survey_answers", []) or []
        if isinstance(raw_answers, dict):
            survey_list = [
                {"question_text": q, "answer_text": a if isinstance(a, list) else [a]}
                for q, a in raw_answers.items()
            ]
        else:
            survey_list = raw_answers

        phone_number = _extract_phone(raw_proj.get("additional_info", "")) or ""

        display_name = d.get("user", {}).get("display_name", "")
        first_name = display_name.split()[0] if display_name else ""

        detail_data = {
            "lead_id": lead_id,
            "business_id": d.get("business_id"),
            "conversation_id": d.get("conversation_id"),
            "temporary_email_address": d.get("temporary_email_address"),
            "temporary_email_address_expiry": d.get("temporary_email_address_expiry"),
            "time_created": d.get("time_created"),
            "last_event_time": last_time,
            "user_display_name": first_name,
            "phone_number": phone_number,
            "phone_opt_in": d.get("phone_opt_in", False),
            "project": {
                "survey_answers": survey_list,
                "location": raw_proj.get("location", {}),
                "additional_info": raw_proj.get("additional_info", ""),
                "availability": raw_proj.get("availability", {}),
                "job_names": raw_proj.get("job_names", []),
                "attachments": raw_proj.get("attachments", []),
            },
        }

        ld, created = safe_update_or_create(
            LeadDetail, defaults=detail_data, lead_id=lead_id
        )
        logger.info(
            f"[AUTO-RESPONSE] LeadDetail {'created' if created else 'updated'} pk={ld.pk}"
        )

        # ✅ DETAILED PHONE DETECTION WITH EXTENSIVE LOGGING
        logger.info(f"[AUTO-RESPONSE] ======== PHONE DETECTION CHECK ========")
        logger.info(f"[AUTO-RESPONSE] Current scenario: phone_available={phone_available}")
        logger.info(f"[AUTO-RESPONSE] Checking for phone in additional_info...")
        
        additional_info = detail_data["project"].get("additional_info", "")
        logger.info(f"[AUTO-RESPONSE] additional_info content: '{additional_info[:200]}...'" + ("" if len(additional_info) <= 200 else " (truncated)"))
        logger.info(f"[AUTO-RESPONSE] additional_info length: {len(additional_info)} characters")
        
        phone_match = PHONE_RE.search(additional_info)
        logger.info(f"[AUTO-RESPONSE] Phone regex match found: {phone_match is not None}")
        
        if phone_match:
            logger.info(f"[AUTO-RESPONSE] Phone match details: '{phone_match.group()}'")
        
        # If a phone number is present in additional_info when the lead detail is
        # fetched for the first time, treat it as a real phone provided by the
        # consumer and switch to the phone available flow.
        if not phone_available and phone_match:
            logger.info(f"[AUTO-RESPONSE] 📞 PHONE DETECTED IN ADDITIONAL INFO")
            logger.info(f"[AUTO-RESPONSE] ========== SWITCHING TO PHONE AVAILABLE FLOW ==========")
            logger.info(f"[AUTO-RESPONSE] Current scenario was: phone_available=False")
            logger.info(f"[AUTO-RESPONSE] Found phone number: {phone_match.group()}")
            logger.info(f"[AUTO-RESPONSE] Will switch to phone_available=True scenario")
            logger.info(f"[AUTO-RESPONSE] This will trigger handle_phone_available()")
            
            if auto_settings and auto_settings.export_to_sheets:
                logger.info(f"[AUTO-RESPONSE] Exporting to Google Sheets first...")
                try:
                    from .utils import append_lead_to_sheet

                    logger.info(
                        "[AUTO-RESPONSE] Exporting lead %s (business=%s) to Google Sheets",
                        lead_id,
                        biz_id,
                    )
                    append_lead_to_sheet(detail_data)
                    logger.info(
                        "[AUTO-RESPONSE] ✅ Lead %s (business=%s) exported to Google Sheets",
                        lead_id,
                        biz_id,
                    )
                except Exception:
                    logger.exception(
                        "[AUTO-RESPONSE] ❌ Google Sheets export failed for lead=%s",
                        lead_id,
                    )

            logger.info(f"[AUTO-RESPONSE] Updating LeadDetail with phone information...")
            
            if not ld.phone_in_additional_info:
                ld.phone_in_additional_info = True
                ld.save(update_fields=["phone_in_additional_info"])
                logger.info(f"[AUTO-RESPONSE] ✅ Set phone_in_additional_info=True")
            
            if phone_number:
                ld.phone_number = phone_number
                ld.save(update_fields=["phone_number"])
                logger.info(f"[AUTO-RESPONSE] ✅ Set phone_number='{phone_number}'")
            
            logger.info("[AUTO-RESPONSE] ✅ Phone found in additional_info")
            logger.info(f"[AUTO-RESPONSE] 🔄 TRIGGERING handle_phone_available")
            logger.info(f"[AUTO-RESPONSE] 🛑 EARLY RETURN - switching to phone available flow")
            
            self.handle_phone_available(
                lead_id, reason="phone number found in additional_info"
            )
            return
        else:
            logger.info(f"[AUTO-RESPONSE] ℹ️ NO PHONE SWITCH NEEDED")
            logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
            logger.info(f"[AUTO-RESPONSE] - phone found in additional_info: {phone_match is not None}")
            logger.info(f"[AUTO-RESPONSE] Continuing with current scenario...")
        
        logger.info(f"[AUTO-RESPONSE] ========================================")

        if auto_settings and auto_settings.export_to_sheets:
            try:
                from .utils import append_lead_to_sheet

                logger.info(
                    "[AUTO-RESPONSE] Exporting lead %s (business=%s) to Google Sheets",
                    lead_id,
                    biz_id,
                )
                append_lead_to_sheet(detail_data)
                logger.info(
                    "[AUTO-RESPONSE] Lead %s (business=%s) exported to Google Sheets",
                    lead_id,
                    biz_id,
                )
            except Exception:
                logger.exception(
                    "[AUTO-RESPONSE] Google Sheets export failed for lead=%s",
                    lead_id,
                )
        elif auto_settings and not auto_settings.export_to_sheets:
            logger.info(
                "[AUTO-RESPONSE] Sheets export disabled in AutoResponseSettings for business=%s, lead=%s",
                biz_id,
                lead_id,
            )

        # ✅ DETAILED ENABLED CHECK WITH EXTENSIVE LOGGING
        logger.info(f"[AUTO-RESPONSE] ======== CRITICAL ENABLED CHECK ========")
        logger.info(f"[AUTO-RESPONSE] About to check if auto responses are enabled...")
        logger.info(f"[AUTO-RESPONSE] auto_settings is None: {auto_settings is None}")
        
        if auto_settings is not None:
            logger.info(f"[AUTO-RESPONSE] auto_settings exists - checking enabled flag...")
            logger.info(f"[AUTO-RESPONSE] auto_settings.enabled: {auto_settings.enabled}")
            logger.info(f"[AUTO-RESPONSE] auto_settings.enabled type: {type(auto_settings.enabled)}")
            
            if auto_settings.enabled:
                logger.info(f"[AUTO-RESPONSE] ✅ AUTO RESPONSES ARE ENABLED")
                logger.info(f"[AUTO-RESPONSE] Proceeding with message generation...")
            else:
                logger.info(f"[AUTO-RESPONSE] ❌ AUTO RESPONSES ARE DISABLED")
                logger.info(f"[AUTO-RESPONSE] auto_settings.enabled = {auto_settings.enabled}")
                logger.info(f"[AUTO-RESPONSE] This is why no message will be sent")
                logger.info(f"[AUTO-RESPONSE] 🛑 EARLY RETURN - auto responses disabled")
                return
        else:
            logger.info(f"[AUTO-RESPONSE] ❌ NO AUTO SETTINGS FOUND")
            logger.info(f"[AUTO-RESPONSE] auto_settings is None - no configuration exists")
            logger.info(f"[AUTO-RESPONSE] This is why no message will be sent")
            logger.info(f"[AUTO-RESPONSE] 🛑 EARLY RETURN - no auto settings")
            return

        logger.info(f"[AUTO-RESPONSE] ✅ ENABLED CHECK PASSED - continuing with message generation")
        logger.info(f"[AUTO-RESPONSE] =======================================")

        # Enhanced logging for message variables preparation
        logger.info(f"[AUTO-RESPONSE] ============ MESSAGE VARIABLES ============")
        logger.info(f"[AUTO-RESPONSE] Preparing message variables from LeadDetail:")
        
        name = ld.user_display_name
        raw_job_names = ld.project.get("job_names", [])
        
        # 🔄 Apply custom job mappings before formatting
        mapped_job_names = self._apply_job_mappings(raw_job_names)
        jobs = ", ".join(mapped_job_names)
        sep = ", " if name and jobs else ""
        
        # 🔧 DUPLICATE PREVENTION: Check if jobs changed after LeadDetail update
        # If job_names was empty initially but now has values, it might cause duplicate with different content
        if created:
            logger.info(f"[AUTO-RESPONSE] 🆕 LeadDetail was CREATED (first time processing)")
        else:
            logger.info(f"[AUTO-RESPONSE] 🔄 LeadDetail was UPDATED (potentially changed data)")
            # TODO: In future, consider using job_names from first creation to prevent content differences
        
        logger.info(f"[AUTO-RESPONSE] Lead data extraction:")
        logger.info(f"[AUTO-RESPONSE] - LeadDetail ID: {ld.pk if ld else 'None'}")
        logger.info(f"[AUTO-RESPONSE] - user_display_name: '{name}'")
        logger.info(f"[AUTO-RESPONSE] - project.job_names (raw): {raw_job_names}")
        logger.info(f"[AUTO-RESPONSE] - project.job_names (mapped): {mapped_job_names}")
        logger.info(f"[AUTO-RESPONSE] - jobs (formatted): '{jobs}'")
        logger.info(f"[AUTO-RESPONSE] - separator: '{sep}'")
        
        # Get time-based greeting
        greetings = get_time_based_greeting(business_id=biz_id)
        logger.info(f"[AUTO-RESPONSE] - greetings: '{greetings}'")
        logger.info(f"[AUTO-RESPONSE] - Full project data: {ld.project}")
        
        # 🔍 DUPLICATE DETECTION: Check if similar message might already exist
        potential_duplicate_jobs = ["", "Remodeling", "remodeling"]  # Common variations
        for alt_jobs in potential_duplicate_jobs:
            if alt_jobs != jobs:  # Don't check against self
                alt_sep = ", " if name and alt_jobs else ""
                # Check for potential template matches
                if auto_settings and hasattr(auto_settings, 'greeting_template'):
                    try:
                        alt_text = auto_settings.greeting_template.format(name=name, jobs=alt_jobs, sep=alt_sep, reason=reason, greetings=greetings)
                        if _already_sent(lead_id, alt_text):
                            logger.warning(f"[AUTO-RESPONSE] ⚠️ POTENTIAL DUPLICATE DETECTED!")
                            logger.warning(f"[AUTO-RESPONSE] Similar message already sent with jobs='{alt_jobs}'")
                            logger.warning(f"[AUTO-RESPONSE] Current jobs='{jobs}', previous jobs='{alt_jobs}'")
                            logger.warning(f"[AUTO-RESPONSE] This might be caused by asynchronous job_names update")
                            # Note: We don't return here, just log the warning for analysis
                    except Exception as e:
                        # Template formatting might fail, that's OK
                        pass

        biz_id = ld.business_id if ld else None
        business = YelpBusiness.objects.filter(business_id=biz_id).first()
        
        logger.info(f"[AUTO-RESPONSE] Business information:")
        logger.info(f"[AUTO-RESPONSE] - Business ID: {biz_id}")
        logger.info(f"[AUTO-RESPONSE] - YelpBusiness found: {business is not None}")
        if business:
            logger.info(f"[AUTO-RESPONSE] - Business name: {business.name}")
            logger.info(f"[AUTO-RESPONSE] - Business timezone: {business.time_zone}")
        logger.info(f"[AUTO-RESPONSE] =======================================")

        # Check if AI is enabled for greeting generation
        use_ai = getattr(auto_settings, 'use_ai_greeting', False)
        
        # Enhanced logging for AI vs Template decision
        logger.info(f"[AUTO-RESPONSE] ======== MESSAGE GENERATION LOGIC ========")
        logger.info(f"[AUTO-RESPONSE] AI vs Template decision:")
        logger.info(f"[AUTO-RESPONSE] - use_ai_greeting setting: {use_ai}")
        logger.info(f"[AUTO-RESPONSE] - Message generation method: {'AI' if use_ai else 'Template-based'}")
        
        now = timezone.now()
        tz_name = business.time_zone if business else None
        within_hours = True
        
        logger.info(f"[AUTO-RESPONSE] Business hours calculation:")
        logger.info(f"[AUTO-RESPONSE] - Current UTC time: {now}")
        logger.info(f"[AUTO-RESPONSE] - Business timezone: {tz_name or 'None (using UTC)'}")
        
        if tz_name:
            tz = ZoneInfo(tz_name)
            local_now = now.astimezone(tz)
            logger.info(f"[AUTO-RESPONSE] - Local business time: {local_now}")
            
            days_setting = (
                auto_settings.greeting_open_days if phone_available else None
            )
            allowed_days = _parse_days(days_setting)
            logger.info(f"[AUTO-RESPONSE] - Business days setting: {days_setting}")
            logger.info(f"[AUTO-RESPONSE] - Allowed days: {allowed_days}")
            logger.info(f"[AUTO-RESPONSE] - Current weekday: {local_now.weekday()}")
            
            open_dt = local_now.replace(
                hour=auto_settings.greeting_open_from.hour,
                minute=auto_settings.greeting_open_from.minute,
                second=auto_settings.greeting_open_from.second,
                microsecond=0,
            )
            close_dt = local_now.replace(
                hour=auto_settings.greeting_open_to.hour,
                minute=auto_settings.greeting_open_to.minute,
                second=auto_settings.greeting_open_to.second,
                microsecond=0,
            )
            if close_dt <= open_dt:
                close_dt += timedelta(days=1)
                
            logger.info(f"[AUTO-RESPONSE] - Business open time: {open_dt}")
            logger.info(f"[AUTO-RESPONSE] - Business close time: {close_dt}")
            
            within_hours = (
                local_now.weekday() in allowed_days and open_dt <= local_now < close_dt
            )
            logger.info(f"[AUTO-RESPONSE] - Within business hours: {within_hours}")
        else:
            logger.info(f"[AUTO-RESPONSE] - No timezone configured, assuming within hours: {within_hours}")

        # Generate greeting message - AI or template-based
        logger.info(f"[AUTO-RESPONSE] ========= GREETING GENERATION =========")
        
        if use_ai:
            logger.info(f"[AUTO-RESPONSE] 🤖 USING AI for greeting generation")
            logger.info(f"[AUTO-RESPONSE] ========== AI GENERATION PATH ==========")
            logger.info(f"[AUTO-RESPONSE] AI generation path selected")
            logger.info(f"[AUTO-RESPONSE] use_ai_greeting setting: {use_ai}")
            logger.info(f"[AUTO-RESPONSE] Attempting to import OpenAI service...")
            
            try:
                from .ai_service import OpenAIService
                ai_service = OpenAIService()
                logger.info(f"[AUTO-RESPONSE] ✅ OpenAI service imported successfully")
                
                logger.info(f"[AUTO-RESPONSE] AI service availability check...")
                
                if ai_service.is_available():
                    logger.info(f"[AUTO-RESPONSE] ✅ AI service is available")
                    logger.info(f"[AUTO-RESPONSE] Proceeding with AI generation...")
                    
                    # Підготовка налаштувань бізнес-інформації для AI
                    business_data_settings = {
                        "include_rating": getattr(auto_settings, 'ai_include_rating', True),
                        "include_categories": getattr(auto_settings, 'ai_include_categories', True),
                        "include_phone": getattr(auto_settings, 'ai_include_phone', True),
                        "include_website": getattr(auto_settings, 'ai_include_website', False),
                        "include_price_range": getattr(auto_settings, 'ai_include_price_range', True),
                        "include_hours": getattr(auto_settings, 'ai_include_hours', True),
                        "include_reviews_count": getattr(auto_settings, 'ai_include_reviews_count', True),
                        "include_address": getattr(auto_settings, 'ai_include_address', False),
                        "include_transactions": getattr(auto_settings, 'ai_include_transactions', False)
                    }
                    
                    logger.info(f"[AUTO-RESPONSE] AI generation parameters:")
                    logger.info(f"[AUTO-RESPONSE] - response_style: {getattr(auto_settings, 'ai_response_style', 'auto')}")
                    logger.info(f"[AUTO-RESPONSE] - include_location: {getattr(auto_settings, 'ai_include_location', False)}")
                    logger.info(f"[AUTO-RESPONSE] - mention_response_time: {getattr(auto_settings, 'ai_mention_response_time', False)}")
                    logger.info(f"[AUTO-RESPONSE] - is_off_hours: {not within_hours}")
                    logger.info(f"[AUTO-RESPONSE] - custom_prompt available: {getattr(auto_settings, 'ai_custom_prompt', None) is not None}")
                    logger.info(f"[AUTO-RESPONSE] - business_data_settings: {business_data_settings}")
                    
                    logger.info(f"[AUTO-RESPONSE] Calling AI service...")
                    
                    # Generate AI greeting
                    ai_greeting = ai_service.generate_greeting_message(
                        lead_detail=ld,
                        business=business,
                        is_off_hours=not within_hours,
                        response_style=getattr(auto_settings, 'ai_response_style', 'auto'),
                        include_location=getattr(auto_settings, 'ai_include_location', False),
                        mention_response_time=getattr(auto_settings, 'ai_mention_response_time', False),
                        custom_prompt=getattr(auto_settings, 'ai_custom_prompt', None),
                        business_data_settings=business_data_settings,
                        max_length=getattr(auto_settings, 'ai_max_message_length', None),
                        business_ai_settings=auto_settings  # 🏢 Передаємо business AI налаштування
                    )
                    
                    if ai_greeting:
                        logger.info(f"[AUTO-RESPONSE] ✅ AI generated greeting successfully")
                        logger.info(f"[AUTO-RESPONSE] AI greeting preview: {ai_greeting[:100]}...")
                        logger.info(f"[AUTO-RESPONSE] AI greeting length: {len(ai_greeting)} characters")
                        greet_text = ai_greeting
                    else:
                        logger.warning(f"[AUTO-RESPONSE] ⚠️ AI generation returned empty result, using template fallback")
                        # Fallback to template
                        if within_hours:
                            greet_text = auto_settings.greeting_template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
                            logger.info(f"[AUTO-RESPONSE] Template fallback (within hours): {greet_text[:100]}...")
                        else:
                            greet_text = auto_settings.greeting_off_hours_template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
                            logger.info(f"[AUTO-RESPONSE] Template fallback (off hours): {greet_text[:100]}...")
                else:
                    logger.warning(f"[AUTO-RESPONSE] ⚠️ AI service not available, using template fallback")
                    logger.warning(f"[AUTO-RESPONSE] AI service unavailability reason: check API keys/network")
                    logger.info(f"[AUTO-RESPONSE] 🔄 SWITCHING TO TEMPLATE FALLBACK")
                    # Fallback to template
                    if within_hours:
                        greet_text = auto_settings.greeting_template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
                        logger.info(f"[AUTO-RESPONSE] Template fallback (within hours): {greet_text[:100]}...")
                    else:
                        greet_text = auto_settings.greeting_off_hours_template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
                        logger.info(f"[AUTO-RESPONSE] Template fallback (off hours): {greet_text[:100]}...")
                        
            except Exception as e:
                logger.error(f"[AUTO-RESPONSE] ❌ AI generation error: {e}")
                logger.exception(f"[AUTO-RESPONSE] AI generation exception details")
                # Fallback to template on any error
                logger.info(f"[AUTO-RESPONSE] 🔄 SWITCHING TO TEMPLATE FALLBACK due to AI error")
                if within_hours:
                    greet_text = auto_settings.greeting_template.format(name=name, jobs=jobs, sep=sep, greetings=greetings)
                    logger.info(f"[AUTO-RESPONSE] Template fallback (within hours): {greet_text[:100]}...")
                else:
                    greet_text = auto_settings.greeting_off_hours_template.format(name=name, jobs=jobs, sep=sep, greetings=greetings)
                    logger.info(f"[AUTO-RESPONSE] Template fallback (off hours): {greet_text[:100]}...")
        else:
            # Traditional template-based approach
            logger.info(f"[AUTO-RESPONSE] 📝 USING TEMPLATE-BASED greeting generation")
            logger.info(f"[AUTO-RESPONSE] ========== TEMPLATE GENERATION PATH ==========")
            logger.info(f"[AUTO-RESPONSE] Template generation path selected")
            logger.info(f"[AUTO-RESPONSE] use_ai_greeting setting: {use_ai} (AI disabled)")
            logger.info(f"[AUTO-RESPONSE] Template variables:")
            logger.info(f"[AUTO-RESPONSE] - name: '{name}'")
            logger.info(f"[AUTO-RESPONSE] - jobs: '{jobs}'")
            logger.info(f"[AUTO-RESPONSE] - sep: '{sep}'")
            logger.info(f"[AUTO-RESPONSE] - within_hours: {within_hours}")
            
            if within_hours:
                template = auto_settings.greeting_template
                logger.info(f"[AUTO-RESPONSE] Using regular hours template: {template[:100]}...")
                greet_text = template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
                logger.info(f"[AUTO-RESPONSE] ✅ Template generated (within hours)")
            else:
                template = auto_settings.greeting_off_hours_template
                logger.info(f"[AUTO-RESPONSE] Using off-hours template: {template[:100]}...")
                greet_text = template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
                logger.info(f"[AUTO-RESPONSE] ✅ Template generated (off hours)")
            
            logger.info(f"[AUTO-RESPONSE] Template result: {greet_text[:100]}...")
        
        # Final message logging
        logger.info(f"[AUTO-RESPONSE] ========== FINAL MESSAGE ==========")
        logger.info(f"[AUTO-RESPONSE] Generated greeting message:")
        logger.info(f"[AUTO-RESPONSE] - Full text: {greet_text}")
        logger.info(f"[AUTO-RESPONSE] - Length: {len(greet_text)} characters")
        logger.info(f"[AUTO-RESPONSE] - Generation method: {'AI' if use_ai else 'Template'}")
        logger.info(f"[AUTO-RESPONSE] ===============================")

        # Calculate due time with enhanced logging
        logger.info(f"[AUTO-RESPONSE] ========= GREETING TIMING DEBUG =========")
        logger.info(f"[AUTO-RESPONSE] Greeting delay (seconds): {auto_settings.greeting_delay}")
        logger.info(f"[AUTO-RESPONSE] Base time (now): {now.isoformat()}")
        logger.info(f"[AUTO-RESPONSE] Within business hours: {within_hours}")
        
        initial_due = now + timedelta(seconds=auto_settings.greeting_delay)
        logger.info(f"[AUTO-RESPONSE] Initial greeting due time: {initial_due.isoformat()}")
        
        if within_hours:
            due = adjust_due_time(
                initial_due,
                tz_name,
                auto_settings.greeting_open_from,
                auto_settings.greeting_open_to,
                days_setting,
            )
        else:
            due = initial_due
            
        logger.info(f"[AUTO-RESPONSE] Final greeting due time: {due.isoformat()}")
        countdown_greeting = (due - now).total_seconds()
        logger.info(f"[AUTO-RESPONSE] Greeting countdown (seconds): {countdown_greeting}")

        scheduled_texts = set()

        # ✅ DETAILED DUPLICATE DETECTION WITH EXTENSIVE LOGGING
        logger.info(f"[AUTO-RESPONSE] ======== DUPLICATE DETECTION CHECK ========")
        logger.info(f"[AUTO-RESPONSE] About to check if greeting was already sent...")
        logger.info(f"[AUTO-RESPONSE] Greeting text to check: '{greet_text[:100]}...'" + ("" if len(greet_text) <= 100 else " (truncated)"))
        logger.info(f"[AUTO-RESPONSE] Greeting text length: {len(greet_text)} characters")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        
        # Check if already sent via _already_sent function
        already_sent_result = _already_sent(lead_id, greet_text)
        logger.info(f"[AUTO-RESPONSE] _already_sent result: {already_sent_result}")
        
        # Check if there are active pending tasks with same text
        pending_tasks_count = LeadPendingTask.objects.filter(lead_id=lead_id, text=greet_text, active=True).count()
        logger.info(f"[AUTO-RESPONSE] Active pending tasks with same text: {pending_tasks_count}")
        
        if pending_tasks_count > 0:
            logger.info(f"[AUTO-RESPONSE] Found {pending_tasks_count} active pending task(s) with same text")
            pending_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, text=greet_text, active=True)[:3]
            for i, task in enumerate(pending_tasks):
                logger.info(f"[AUTO-RESPONSE] Pending task {i+1}: ID={task.id}, task_id={task.task_id}, created_at={task.created_at}")

        with transaction.atomic():
            if (
                already_sent_result
                or LeadPendingTask.objects.select_for_update()
                .filter(lead_id=lead_id, text=greet_text, active=True)
                .exists()
            ):
                logger.info(f"[AUTO-RESPONSE] ❌ GREETING DUPLICATE DETECTED")
                logger.info(f"[AUTO-RESPONSE] - Already sent: {already_sent_result}")
                logger.info(f"[AUTO-RESPONSE] - Active pending tasks: {pending_tasks_count > 0}")
                logger.info(f"[AUTO-RESPONSE] 🛑 SKIPPING GREETING - duplicate detected")
                logger.info(
                    "[AUTO-RESPONSE] Greeting already sent or queued → skipping"
                )
            elif due <= now:
                logger.info(f"[AUTO-RESPONSE] ✅ GREETING WILL BE SENT IMMEDIATELY")
                logger.info(f"[AUTO-RESPONSE] Due time: {due.isoformat()}")
                logger.info(f"[AUTO-RESPONSE] Current time: {now.isoformat()}")
                logger.info(f"[AUTO-RESPONSE] Sending greeting via Celery with countdown=0")
                logger.info(f"[AUTO-RESPONSE] 🚀 DISPATCHING GREETING TASK")
                
                send_follow_up.apply_async(
                    args=[lead_id, greet_text],
                    headers={"business_id": biz_id},
                    countdown=0,
                )
                logger.info(
                    "[AUTO-RESPONSE] ✅ Greeting dispatched immediately via Celery"
                )
                scheduled_texts.add(greet_text)
            else:
                logger.info(f"[AUTO-RESPONSE] ✅ GREETING WILL BE SCHEDULED")
                logger.info(f"[AUTO-RESPONSE] Due time: {due.isoformat()}")
                logger.info(f"[AUTO-RESPONSE] Current time: {now.isoformat()}")
                logger.info(f"[AUTO-RESPONSE] Countdown: {countdown_greeting} seconds")
                logger.info(f"[AUTO-RESPONSE] 🚀 SCHEDULING GREETING TASK")
                
                res = send_follow_up.apply_async(
                    args=[lead_id, greet_text],
                    headers={"business_id": biz_id},
                    countdown=countdown_greeting,
                )
                logger.info(f"[AUTO-RESPONSE] ✅ Celery task created with ID: {res.id}")
                logger.info(f"[AUTO-RESPONSE] Creating LeadPendingTask record...")
                
                try:
                    task_record = LeadPendingTask.objects.create(
                        lead_id=lead_id,
                        task_id=res.id,
                        text=greet_text,
                        phone_opt_in=phone_opt_in,
                        phone_available=phone_available,
                    )
                    logger.info(f"[AUTO-RESPONSE] ✅ LeadPendingTask created with ID: {task_record.id}")
                except IntegrityError:
                    logger.info(
                        "[AUTO-RESPONSE] ❌ Duplicate pending task already exists → skipping"
                    )
                else:
                    logger.info(
                        f"[AUTO-RESPONSE] ✅ Greeting scheduled at {due.isoformat()}"
                    )
                    scheduled_texts.add(greet_text)

        if phone_available:
            return

        # Use the same 'now' timestamp for consistent timing calculations
        # instead of calling timezone.now() again

        tpls = FollowUpTemplate.objects.filter(
            active=True,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available,
            business__business_id=biz_id,
        )
        if not tpls.exists():
            tpls = FollowUpTemplate.objects.filter(
                active=True,
                phone_opt_in=phone_opt_in,
                phone_available=phone_available,
                business__isnull=True,
            )
        business = YelpBusiness.objects.filter(business_id=biz_id).first()
        for tmpl in tpls:
            # Keep exact seconds precision - don't use int() which truncates
            delay = tmpl.delay.total_seconds()
            text = tmpl.template.format(name=name, jobs=jobs, sep=sep, reason=reason, greetings=greetings)
            
            # Enhanced logging for precise timing debug
            logger.info(f"[AUTO-RESPONSE] ========= FOLLOW-UP TIMING DEBUG =========")
            logger.info(f"[AUTO-RESPONSE] Template: '{tmpl.name}'")
            logger.info(f"[AUTO-RESPONSE] Raw delay (seconds): {delay}")
            logger.info(f"[AUTO-RESPONSE] Raw delay formatted: {tmpl.delay}")
            logger.info(f"[AUTO-RESPONSE] Base time (now): {now.isoformat()}")
            
            initial_due = now + timedelta(seconds=delay)
            logger.info(f"[AUTO-RESPONSE] Initial due time: {initial_due.isoformat()}")
            
            due = adjust_due_time(
                initial_due,
                business.time_zone if business else None,
                tmpl.open_from,
                tmpl.open_to,
            )
            
            logger.info(f"[AUTO-RESPONSE] Adjusted due time: {due.isoformat()}")
            countdown = max((due - now).total_seconds(), 0)
            logger.info(f"[AUTO-RESPONSE] Final countdown (seconds): {countdown}")
            with transaction.atomic():
                if (
                    _already_sent(lead_id, text)
                    or text in scheduled_texts
                    or LeadPendingTask.objects.select_for_update()
                    .filter(lead_id=lead_id, text=text, active=True)
                    .exists()
                ):
                    logger.info(
                        f"[AUTO-RESPONSE] Custom follow-up '{tmpl.name}' already sent or duplicate → skipping"
                    )
                else:
                    res = send_follow_up.apply_async(
                        args=[lead_id, text],
                        headers={"business_id": biz_id},
                        countdown=countdown,
                    )
                    try:
                        LeadPendingTask.objects.create(
                            lead_id=lead_id,
                            task_id=res.id,
                            text=text,
                            phone_opt_in=phone_opt_in,
                            phone_available=phone_available,
                        )
                    except IntegrityError:
                        logger.info(
                            "[AUTO-RESPONSE] Duplicate pending task already exists → skipping"
                        )
                    else:
                        logger.info(
                            f"[AUTO-RESPONSE] ✅ Custom follow-up '{tmpl.name}' scheduled at {due.isoformat()}"
                        )
                        scheduled_texts.add(text)
        
        # ✅ COMPLETION LOGGING
        logger.info(f"[AUTO-RESPONSE] ========== PROCESS COMPLETION ==========")
        logger.info(f"[AUTO-RESPONSE] _process_auto_response completed successfully")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Scenario: phone_opt_in={phone_opt_in}, phone_available={phone_available}")
        logger.info(f"[AUTO-RESPONSE] Messages scheduled: {len(scheduled_texts)}")
        logger.info(f"[AUTO-RESPONSE] Auto responses enabled: {auto_settings.enabled if auto_settings else 'N/A'}")
        logger.info(f"[AUTO-RESPONSE] AI generation used: {getattr(auto_settings, 'use_ai_greeting', False) if auto_settings else 'N/A'}")
        logger.info(f"[AUTO-RESPONSE] ✅ PROCESS AUTO RESPONSE COMPLETED")
        logger.info(f"[AUTO-RESPONSE] =======================================")
