import logging
import time
import unicodedata
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
    logger.info(f"[PHONE-REGEX] 📞 _extract_phone called with text: '{text}'")
    logger.info(f"[PHONE-REGEX] - Text type: {type(text)}")
    logger.info(f"[PHONE-REGEX] - Text length: {len(text) if text else 0}")
    
    if not text:
        logger.info(f"[PHONE-REGEX] ❌ No text provided - returning None")
        return None
        
    logger.info(f"[PHONE-REGEX] 🔍 Searching for phone patterns using regex: {PHONE_RE.pattern}")
    
    matches_found = list(PHONE_RE.finditer(text))
    logger.info(f"[PHONE-REGEX] - Found {len(matches_found)} potential phone matches")
    
    for i, m in enumerate(matches_found):
        candidate = m.group()
        digits = re.sub(r"\D", "", candidate)
        logger.info(f"[PHONE-REGEX] - Match {i+1}: '{candidate}'")
        logger.info(f"[PHONE-REGEX] - Digits only: '{digits}'")
        logger.info(f"[PHONE-REGEX] - Digits length: {len(digits)}")
        logger.info(f"[PHONE-REGEX] - Is valid length (>=10): {len(digits) >= 10}")
        logger.info(f"[PHONE-REGEX] - Matches date pattern: {bool(DATE_RE.fullmatch(candidate))}")
        
        if len(digits) >= 10 and not DATE_RE.fullmatch(candidate):
            logger.info(f"[PHONE-REGEX] ✅ Valid phone number found: '{candidate}'")
            return candidate
        else:
            logger.info(f"[PHONE-REGEX] ❌ Invalid phone number (too short or date-like): '{candidate}'")
    
    logger.info(f"[PHONE-REGEX] ❌ No valid phone numbers found in text")
    return None


def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for accurate comparison by handling Unicode and special characters."""
    if not text:
        return text
    
    # Normalize Unicode characters (NFKC handles compatibility characters)
    normalized = unicodedata.normalize('NFKC', text)
    
    # Replace various apostrophe types with standard ASCII apostrophe
    apostrophe_variants = [''', ''', '`', '´']
    for variant in apostrophe_variants:
        normalized = normalized.replace(variant, "'")
    
    # Replace various quote types with standard ASCII quotes
    quote_variants = ['"', '"', '„', '‚', '«', '»']
    for variant in quote_variants:
        normalized = normalized.replace(variant, '"')
    
    # Replace various dash types with standard ASCII dash
    dash_variants = ['–', '—', '−']
    for variant in dash_variants:
        normalized = normalized.replace(variant, '-')
    
    # Strip whitespace
    normalized = normalized.strip()
    
    return normalized


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
                    logger.info(f"[WEBHOOK] ========== PHONE OPT-IN EVENT → NO PHONE SCENARIO ==========")
                    logger.info(f"[WEBHOOK] Lead ID: {lid}")
                    logger.info(f"[WEBHOOK] Event type: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT")
                    logger.info(f"[WEBHOOK] 🔄 UNIFIED LOGIC: Phone opt-in → No Phone scenario")
                    logger.info(f"[WEBHOOK] =================== PHONE OPT-IN EVENT DETAILS ===================")
                    logger.info(f"[WEBHOOK] 📱 Consumer agreed to provide phone number via Yelp interface")
                    logger.info(f"[WEBHOOK] 🎯 NEW BEHAVIOR: Will use No Phone scenario instead of separate logic")
                    logger.info(f"[WEBHOOK] 📋 What happens next:")
                    logger.info(f"[WEBHOOK] - LeadDetail.phone_opt_in set to True (for frontend badge)")
                    logger.info(f"[WEBHOOK] - No separate phone opt-in tasks created")
                    logger.info(f"[WEBHOOK] - Uses existing No Phone templates and follow-ups")
                    logger.info(f"[WEBHOOK] - Frontend shows 'Phone Opt-In' badge for identification")
                    logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True (for frontend display)")
                    
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    
                    logger.info(f"[WEBHOOK] LeadDetail update result:")
                    logger.info(f"[WEBHOOK] - Records updated: {updated}")
                    logger.info(f"[WEBHOOK] - phone_opt_in set to True for tracking purposes")
                    
                    if updated:
                        logger.info(f"[WEBHOOK] ✅ Phone opt-in flag updated successfully")
                        logger.info(f"[WEBHOOK] 🎯 NEW BEHAVIOR: Using No Phone scenario for phone opt-in")
                        logger.info(f"[WEBHOOK] Phone opt-in leads will use same templates as No Phone leads")
                        logger.info(f"[WEBHOOK] ✅ No additional handler needed - No Phone scenario handles everything")
                    else:
                        logger.warning(f"[WEBHOOK] ⚠️ No LeadDetail records updated")
                        logger.warning(f"[WEBHOOK] This means the lead already had phone_opt_in=True")
                    
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
                        logger.info(f"[WEBHOOK] 💬 REGULAR CONSUMER RESPONSE - cancelling no-phone tasks")
                        self._cancel_no_phone_tasks(lid, reason=reason)
                        
                        # Check what tasks remain after no-phone cancellation
                        remaining_after_regular = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                        logger.info(f"[WEBHOOK] 📊 TASKS AFTER NO-PHONE CANCELLATION: {remaining_after_regular.count()}")
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
            elif upd.get("event_type") == "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT":
                # Handle phone opt-in event to set badge for frontend
                logger.info(f"[WEBHOOK] 📱 CONSUMER_PHONE_NUMBER_OPT_IN_EVENT detected (main handler)")
                logger.info(f"[WEBHOOK] ========== PHONE OPT-IN → NO PHONE SCENARIO (MAIN LOOP) ========")
                logger.info(f"[WEBHOOK] Lead ID: {lid}")
                logger.info(f"[WEBHOOK] Event type: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT")
                logger.info(f"[WEBHOOK] 🔄 UNIFIED LOGIC: Phone opt-in → No Phone scenario")
                logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True (for frontend display)")
                
                updated = LeadDetail.objects.filter(
                    lead_id=lid, phone_opt_in=False
                ).update(phone_opt_in=True)
                
                logger.info(f"[WEBHOOK] LeadDetail update result:")
                logger.info(f"[WEBHOOK] - Records updated: {updated}")
                logger.info(f"[WEBHOOK] - phone_opt_in set to True for tracking purposes")
                
                if updated:
                    logger.info(f"[WEBHOOK] ✅ Phone opt-in badge set successfully for frontend")
                else:
                    logger.warning(f"[WEBHOOK] ⚠️ No LeadDetail records updated")
                    logger.warning(f"[WEBHOOK] This means the lead already had phone_opt_in=True")
                
                logger.info(f"[WEBHOOK] =======================================")
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
                logger.info(f"[WEBHOOK] 🔍 CHECKING LeadEvent for exact text match")
                logger.info(f"[WEBHOOK] - Lead ID: {lid}")
                logger.info(f"[WEBHOOK] - Text length: {len(text) if text else 0}")
                logger.info(f"[WEBHOOK] - Text hash: {hash(text) if text else 'None'}")
                logger.info(f"[WEBHOOK] - Text preview: '{text[:100]}...' " + ("" if len(text) <= 100 else f"(+{len(text)-100} more chars)"))
                
                existing_events = LeadEvent.objects.filter(lead_id=lid, from_backend=True)
                logger.info(f"[WEBHOOK] - Found {existing_events.count()} existing from_backend=True events")
                
                if existing_events.exists():
                    logger.info(f"[WEBHOOK] - Comparing with existing texts:")
                    for i, event in enumerate(existing_events[:3]):
                        normalized_event_text = normalize_text_for_comparison(event.text)
                        text_match = normalized_event_text == normalized_text
                        logger.info(f"[WEBHOOK]   Event {i+1}: match={text_match}, length={len(event.text)}, hash={hash(event.text)}")
                        logger.info(f"[WEBHOOK]   Event {i+1} normalized: hash={hash(normalized_event_text)}")
                        logger.info(f"[WEBHOOK]   Event {i+1} text: '{event.text[:100]}...' " + ("" if len(event.text) <= 100 else f"(+{len(event.text)-100} more chars)"))
                
                # Normalize text for comparison
                normalized_text = normalize_text_for_comparison(text)
                logger.info(f"[WEBHOOK] - Normalized text: '{normalized_text}'")
                logger.info(f"[WEBHOOK] - Normalized hash: {hash(normalized_text) if normalized_text else 'None'}")
                
                if normalized_text and LeadEvent.objects.filter(
                    lead_id=lid, text=normalized_text, from_backend=True
                ).exists():
                    defaults["from_backend"] = True
                    logger.info(f"[WEBHOOK] ✅ EXACT MATCH FOUND - Setting from_backend=True (previously sent by us)")
                else:
                    logger.info(f"[WEBHOOK] ❌ NO EXACT MATCH - from_backend remains False")
                
                # Спосіб 2: Перевірка чи текст співпадає з активним або недавнім LeadPendingTask
                if not defaults["from_backend"] and text:
                    logger.info(f"[WEBHOOK] 🔍 CHECKING LeadPendingTask for text match")
                    
                    # Показати всі завдання для цього ліда
                    all_tasks = LeadPendingTask.objects.filter(lead_id=lid)
                    logger.info(f"[WEBHOOK] - Found {all_tasks.count()} total LeadPendingTask records for lead")
                    
                    # Активні завдання (заплановані фоловапи)
                    active_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                    logger.info(f"[WEBHOOK] - Found {active_tasks.count()} active tasks")
                    
                    for i, task in enumerate(active_tasks[:5]):
                        normalized_task_text = normalize_text_for_comparison(task.text)
                        text_match = normalized_task_text == normalized_text
                        logger.info(f"[WEBHOOK]   Active Task {i+1}: match={text_match}, length={len(task.text)}, hash={hash(task.text)}")
                        logger.info(f"[WEBHOOK]   Active Task {i+1} normalized: hash={hash(normalized_task_text)}")
                        logger.info(f"[WEBHOOK]   Active Task {i+1} text: '{task.text[:100]}...' " + ("" if len(task.text) <= 100 else f"(+{len(task.text)-100} more chars)"))
                    
                    matching_active = LeadPendingTask.objects.filter(
                        lead_id=lid, text=normalized_text, active=True
                    ).exists()
                    
                    # Недавно виконані завдання (останні 10 хвилин)
                    from django.utils import timezone
                    ten_minutes_ago = timezone.now() - timezone.timedelta(minutes=10)
                    recent_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=False, created_at__gte=ten_minutes_ago)
                    logger.info(f"[WEBHOOK] - Found {recent_tasks.count()} recent tasks (last 10 min)")
                    
                    for i, task in enumerate(recent_tasks[:5]):
                        normalized_task_text = normalize_text_for_comparison(task.text)
                        text_match = normalized_task_text == normalized_text
                        logger.info(f"[WEBHOOK]   Recent Task {i+1}: match={text_match}, length={len(task.text)}, hash={hash(task.text)}")
                        logger.info(f"[WEBHOOK]   Recent Task {i+1} normalized: hash={hash(normalized_task_text)}")
                        logger.info(f"[WEBHOOK]   Recent Task {i+1} text: '{task.text[:100]}...' " + ("" if len(task.text) <= 100 else f"(+{len(task.text)-100} more chars)"))
                    
                    matching_recent = LeadPendingTask.objects.filter(
                        lead_id=lid, text=normalized_text, active=False, created_at__gte=ten_minutes_ago
                    ).exists()
                    
                    if matching_active or matching_recent:
                        defaults["from_backend"] = True
                        logger.info(f"[WEBHOOK] ✅ TASK MATCH FOUND - Setting from_backend=True (matches LeadPendingTask)")
                        logger.info(f"[WEBHOOK] Active match: {matching_active}, Recent match: {matching_recent}")
                    else:
                        logger.info(f"[WEBHOOK] ❌ NO TASK MATCH - from_backend remains False")
                
                # Other detection methods removed - LeadEvent + LeadPendingTask checks are sufficient
                
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
                logger.info(f"[WEBHOOK] 🔍 DETAILED EVENT ANALYSIS for lead={lid}, event_id={eid}")
                logger.info(f"[WEBHOOK] =================== IS_NEW CALCULATION ===================")
                logger.info(f"[WEBHOOK] Event details:")
                logger.info(f"[WEBHOOK] - Event ID: {eid}")
                logger.info(f"[WEBHOOK] - Event type: {e.get('event_type')}")
                logger.info(f"[WEBHOOK] - User type: {e.get('user_type')}")
                logger.info(f"[WEBHOOK] - User display name: '{e.get('user_display_name', '')}'")
                logger.info(f"[WEBHOOK] - Text: '{text[:50]}...'")
                logger.info(f"[WEBHOOK] - Time created: {event_time_str}")
                logger.info(f"[WEBHOOK] IS_NEW components:")
                logger.info(f"[WEBHOOK] - created (new in DB): {created}")
                logger.info(f"[WEBHOOK] - event_time exists: {event_time is not None}")
                logger.info(f"[WEBHOOK] - processed_at exists: {processed_at is not None}")
                if event_time and processed_at:
                    time_diff = (event_time - processed_at).total_seconds()
                    logger.info(f"[WEBHOOK] - event_time > processed_at: {event_time > processed_at}")
                    logger.info(f"[WEBHOOK] - Time difference: {time_diff:.1f} seconds")
                else:
                    logger.info(f"[WEBHOOK] - Cannot compare times (missing data)")
                
                is_really_new_event = (
                    created and 
                    event_time and 
                    processed_at and 
                    event_time > processed_at
                )
                
                logger.info(f"[WEBHOOK] 🎯 FINAL IS_NEW RESULT: {is_really_new_event}")
                logger.info(f"[WEBHOOK] ========================================")
                
                # Замінюємо is_new на is_really_new_event
                is_new = is_really_new_event

                if e.get("event_type") == "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT":
                    logger.info(f"[WEBHOOK] 📱 CONSUMER_PHONE_NUMBER_OPT_IN_EVENT detected (second handler)")
                    logger.info(f"[WEBHOOK] ========== PHONE OPT-IN → NO PHONE SCENARIO (EVENTS LOOP) ========")
                    logger.info(f"[WEBHOOK] Lead ID: {lid}")
                    logger.info(f"[WEBHOOK] Event ID: {eid}")
                    logger.info(f"[WEBHOOK] Event type: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT")
                    logger.info(f"[WEBHOOK] 🔄 UNIFIED LOGIC: Phone opt-in → No Phone scenario")
                    logger.info(f"[WEBHOOK] =================== PHONE OPT-IN EVENT DETAILS ===================")
                    logger.info(f"[WEBHOOK] 📱 Consumer agreed to provide phone number via Yelp interface")
                    logger.info(f"[WEBHOOK] 🎯 NEW BEHAVIOR: Will use No Phone scenario instead of separate logic")
                    logger.info(f"[WEBHOOK] 📋 What happens next:")
                    logger.info(f"[WEBHOOK] - LeadDetail.phone_opt_in set to True (for frontend badge)")
                    logger.info(f"[WEBHOOK] - No separate phone opt-in tasks created")
                    logger.info(f"[WEBHOOK] - Uses existing No Phone templates and follow-ups")
                    logger.info(f"[WEBHOOK] - Frontend shows 'Phone Opt-In' badge for identification")
                    logger.info(f"[WEBHOOK] About to update LeadDetail.phone_opt_in to True (for frontend display)")
                    
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    
                    logger.info(f"[WEBHOOK] LeadDetail update result:")
                    logger.info(f"[WEBHOOK] - Records updated: {updated}")
                    logger.info(f"[WEBHOOK] - phone_opt_in set to True for tracking purposes")
                    
                    if updated:
                        logger.info(f"[WEBHOOK] ✅ Phone opt-in flag updated successfully")
                        logger.info(f"[WEBHOOK] 🎯 NEW BEHAVIOR: Phone opt-in uses No Phone scenario")
                        logger.info(f"[WEBHOOK] Phone opt-in leads will get No Phone templates and follow-ups")
                        logger.info(f"[WEBHOOK] ✅ No separate handler needed - unified with No Phone scenario")
                    else:
                        logger.warning(f"[WEBHOOK] ⚠️ No LeadDetail records updated")
                        logger.warning(f"[WEBHOOK] This means the lead already had phone_opt_in=True")
                    
                    logger.info(f"[WEBHOOK] ==============================================")

                if is_new and e.get("user_type") == "CONSUMER":
                    logger.info(f"[WEBHOOK] 👤 PROCESSING CONSUMER EVENT as TRULY NEW")
                    logger.info(f"[WEBHOOK] Event ID: {eid}")
                    logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                    logger.info(f"[WEBHOOK] Has phone in text: {has_phone}")
                    if has_phone:
                        logger.info(f"[WEBHOOK] Extracted phone: {phone}")
                    
                    # 🔄 UNIFIED LOGIC: Phone opt-in responses treated as No Phone responses
                    logger.info(f"[WEBHOOK] 🔍 CHECKING FOR PHONE OPT-IN CONSUMER RESPONSE")
                    ld_flags = LeadDetail.objects.filter(lead_id=lid).values("phone_opt_in", "phone_number").first()
                    logger.info(f"[WEBHOOK] LeadDetail flags: {ld_flags}")
                    
                    # Show existing tasks before any processing
                    all_existing_tasks = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                    logger.info(f"[WEBHOOK] 📊 ALL EXISTING ACTIVE TASKS: {all_existing_tasks.count()}")
                    for task in all_existing_tasks:
                        logger.info(f"[WEBHOOK] - Task {task.task_id}: phone_available={task.phone_available}")
                    
                    if (ld_flags and ld_flags.get("phone_opt_in")):
                        logger.info(f"[WEBHOOK] 📱 PHONE OPT-IN CONSUMER RESPONSE → TREAT AS NO PHONE")
                        logger.info(f"[WEBHOOK] ========== PHONE OPT-IN → NO PHONE UNIFIED LOGIC ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Phone opt-in flag: {ld_flags.get('phone_opt_in')}")
                        logger.info(f"[WEBHOOK] 🔄 UNIFIED RESPONSE LOGIC: Phone opt-in → No Phone")
                        logger.info(f"[WEBHOOK] =================== PHONE OPT-IN CONSUMER RESPONSE ===================")
                        logger.info(f"[WEBHOOK] 📱 This is a phone opt-in lead that consumer is responding to")
                        logger.info(f"[WEBHOOK] 🎯 NEW SYSTEM: Phone opt-in responses treated as No Phone responses")
                        logger.info(f"[WEBHOOK] 📋 What this means:")
                        logger.info(f"[WEBHOOK] - Uses No Phone cancellation logic")
                        logger.info(f"[WEBHOOK] - Uses No Phone SMS templates")
                        logger.info(f"[WEBHOOK] - Frontend still shows 'Phone Opt-In' badge")
                        logger.info(f"[WEBHOOK] - Unified experience with regular no-phone responses")
                        
                        if not has_phone:
                            # Споживач відповів без номера - використовуємо No Phone логіку
                            reason = "Consumer replied to phone opt-in flow (treated as No Phone response)"
                            logger.info(f"[WEBHOOK] 💬 USING NO PHONE LOGIC for phone opt-in response")
                            self._cancel_no_phone_tasks(lid, reason=reason)
                            
                            # Check what tasks remain after cancellation
                            remaining_tasks = LeadPendingTask.objects.filter(lid=lid, active=True)
                            logger.info(f"[WEBHOOK] 📊 TASKS AFTER NO PHONE CANCELLATION: {remaining_tasks.count()}")
                            
                            # Send customer reply SMS (No Phone scenario)
                            logger.info(f"[WEBHOOK] 📱 SENDING No Phone scenario SMS for phone opt-in response")
                            self._send_customer_reply_sms_only(lid)
                        else:
                            # Споживач надав номер - переключаємося на Phone Available
                            logger.info(f"[WEBHOOK] 📞 Phone opt-in consumer provided phone → Phone Available scenario")
                            
                            # Update LeadDetail with phone
                            ld = LeadDetail.objects.get(lead_id=lid)
                            ld.phone_in_text = True
                            ld.phone_number = phone
                            ld.phone_sms_sent = False
                            ld.save(update_fields=['phone_in_text', 'phone_number', 'phone_sms_sent'])
                            
                            reason = "Phone opt-in consumer provided phone → Phone Available scenario"
                            logger.info(f"[WEBHOOK] 🚀 SWITCHING to handle_phone_available")
                            self.handle_phone_available(lid, reason=reason)
                        
                        logger.info(f"[WEBHOOK] ==============================================")
                        continue  # Skip regular pending tasks logic
                    
                    pending = LeadPendingTask.objects.filter(
                        lead_id=lid,
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
                        
                        # Use .save() instead of .update() to trigger post_save signal for SMS notifications
                        ld = LeadDetail.objects.get(lead_id=lid)
                        ld.phone_in_text = True
                        ld.phone_number = phone
                        # Reset phone_sms_sent to allow SMS notification when phone is actually found
                        ld.phone_sms_sent = False
                        logger.info(f"[WEBHOOK] 🔄 Reset phone_sms_sent=False to allow SMS notification with real phone number")
                        ld.save(update_fields=['phone_in_text', 'phone_number', 'phone_sms_sent'])
                        
                        logger.info(f"[WEBHOOK] ✅ LeadDetail updated with phone information (triggers SMS signal)")
                        logger.info(f"[WEBHOOK] - phone_in_text: {ld.phone_in_text}")
                        logger.info(f"[WEBHOOK] - phone_number: {ld.phone_number}")
                        
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
                            logger.info(f"[WEBHOOK] This will call _process_auto_response with phone_available=True")
                            self.handle_phone_available(lid, reason=reason)
                            logger.info(f"[WEBHOOK] ✅ handle_phone_available completed")
                        else:
                            logger.info(f"[WEBHOOK] 🔄 NO PENDING TASKS - triggering phone available flow")
                            logger.info(f"[WEBHOOK] 🚀 TRIGGERING handle_phone_available (no pending tasks)")
                            logger.info(f"[WEBHOOK] This will call _process_auto_response with phone_available=True")
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
                        logger.info(f"[WEBHOOK] ❗ Customer Reply scenario - cancelling tasks + sending Customer Reply SMS")
                        logger.info(f"[WEBHOOK] 🎯 SMS DECISION ANALYSIS:")
                        logger.info(f"[WEBHOOK] - Scenario: Customer Reply (phone_available=False)")
                        logger.info(f"[WEBHOOK] - Current behavior: Cancel pending tasks + Customer Reply SMS")
                        
                        reason = "Client responded, but no number was found"
                        logger.info(f"[WEBHOOK] 💬 REGULAR CONSUMER RESPONSE - cancelling no-phone tasks")
                        self._cancel_no_phone_tasks(lid, reason=reason)
                        
                        # Check what tasks remain after no-phone cancellation
                        remaining_after_regular = LeadPendingTask.objects.filter(lead_id=lid, active=True)
                        logger.info(f"[WEBHOOK] 📊 TASKS AFTER NO-PHONE CANCELLATION: {remaining_after_regular.count()}")
                        
                        # Send SMS notification for Customer Reply (without follow-up)
                        logger.info(f"[WEBHOOK] 📱 SENDING Customer Reply SMS (no follow-up)")
                        self._send_customer_reply_sms_only(lid)
                    else:
                        logger.info(f"[WEBHOOK] ℹ️ CLIENT RESPONDED but no pending tasks to handle")
                        logger.info(f"[WEBHOOK] ========== CUSTOMER REPLY SCENARIO (NO PENDING TASKS) ==========")
                        logger.info(f"[WEBHOOK] Lead ID: {lid}")
                        logger.info(f"[WEBHOOK] Event ID: {eid}")
                        logger.info(f"[WEBHOOK] Event text: '{text[:100]}...'" + ("" if len(text) <= 100 else " (truncated)"))
                        logger.info(f"[WEBHOOK] Has pending no-phone tasks: {pending}")
                        logger.info(f"[WEBHOOK] Phone number found in text: {has_phone}")
                        logger.info(f"[WEBHOOK] ❗ Customer Reply scenario detected - no pending tasks to cancel")
                        logger.info(f"[WEBHOOK] 🎯 SMS DECISION ANALYSIS:")
                        logger.info(f"[WEBHOOK] - Scenario: Customer Reply (phone_available=False)")
                        logger.info(f"[WEBHOOK] - Current behavior: Customer Reply SMS (no follow-up)")
                        
                        # Send SMS notification for Customer Reply (without follow-up)
                        logger.info(f"[WEBHOOK] 📱 SENDING Customer Reply SMS (no follow-up)")
                        self._send_customer_reply_sms_only(lid)
                else:
                    # Simplified event processing with detailed logging
                    user_type = e.get("user_type")
                    logger.info(f"[WEBHOOK] 🔍 OTHER EVENT PROCESSING:")
                    logger.info(f"[WEBHOOK] - Event type: {e.get('event_type')}")
                    logger.info(f"[WEBHOOK] - User type: '{user_type}'")
                    logger.info(f"[WEBHOOK] - Is new: {is_new}")
                    logger.info(f"[WEBHOOK] - Text: '{text[:50]}...'")
                    logger.info(f"[WEBHOOK] - Created in DB: {created}")
                    
                    # Check for BIZ events that might be manual business messages
                    if user_type == "BIZ" and text:
                        logger.info(f"[WEBHOOK] 🏢 BIZ EVENT DETECTED - Checking if manual or automated")
                        logger.info(f"[WEBHOOK] Business message: '{text[:100]}...'")
                        
                        # CRITICAL: Analyze what Yelp returned vs what we sent
                        logger.info(f"[WEBHOOK] 🔍 YELP FORMAT ANALYSIS:")
                        logger.info(f"[WEBHOOK] ========== YELP RETURNED TEXT ==========")
                        logger.info(f"[WEBHOOK] YELP RETURNED:")
                        logger.info(f"[WEBHOOK] - Full text: '{text}'")
                        logger.info(f"[WEBHOOK] - Length: {len(text)}")
                        logger.info(f"[WEBHOOK] - Hash: {hash(text)}")
                        logger.info(f"[WEBHOOK] - Type: {type(text)}")
                        
                        # Check for Unicode characters in Yelp response
                        import unicodedata
                        unicode_chars = []
                        for i, char in enumerate(text):
                            if ord(char) > 127:  # Non-ASCII
                                unicode_chars.append(f"pos {i}: '{char}' (U+{ord(char):04X}) name={unicodedata.name(char, 'UNKNOWN')}")
                        
                        if unicode_chars:
                            logger.info(f"[WEBHOOK] - Unicode chars in Yelp response: {unicode_chars[:10]}")
                        else:
                            logger.info(f"[WEBHOOK] - Yelp returned pure ASCII text")
                        
                        logger.info(f"[WEBHOOK] ===========================================")
                        
                        # Check if this is our automated message
                        is_our_automated_message = defaults.get("from_backend", False)
                        
                        if is_our_automated_message:
                            logger.info(f"[WEBHOOK] 🤖 AUTOMATED BIZ MESSAGE - This is our own follow-up")
                            logger.info(f"[WEBHOOK] No action needed - system behavior is expected")
                        else:
                            logger.info(f"[WEBHOOK] 👨‍💼 MANUAL BIZ MESSAGE - Business responded manually in dashboard")
                            logger.info(f"[WEBHOOK] 🛑 CANCELLING ALL FOLLOW-UP TASKS - Business took over conversation")
                            self._cancel_all_tasks(lid, reason=f"Business responded manually in Yelp dashboard: '{text[:50]}...'")
                            logger.info(f"[WEBHOOK] ✅ All follow-up tasks cancelled for lead={lid}")
                    
                    elif user_type == "CONSUMER":
                        logger.info(f"[WEBHOOK] 📝 CONSUMER EVENT DETECTED")
                        if created:
                            logger.info(f"[WEBHOOK] Consumer event recorded but timing check determines: is_new={is_new}")
                        else:
                            logger.info(f"[WEBHOOK] Consumer event already existed in DB")
                    
                    else:
                        logger.info(f"[WEBHOOK] 📄 OTHER EVENT TYPE - no specific action")

        return Response({"status": "received"}, status=status.HTTP_201_CREATED)

    def handle_new_lead(self, lead_id: str):
        logger.info(f"[AUTO-RESPONSE] 🆕 STARTING handle_new_lead")
        logger.info(f"[AUTO-RESPONSE] =================== NEW LEAD HANDLER ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: NEW_LEAD")
        logger.info(f"[AUTO-RESPONSE] Scenario: New lead processing (will create LeadDetail + follow-ups, no SMS)")
        logger.info(f"[AUTO-RESPONSE] Trigger reason: ProcessedLead was created for this lead")
        logger.info(f"[AUTO-RESPONSE] About to determine scenario for new lead")
        
        try:
            # Check if this is a phone opt-in lead for detailed logging
            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
            is_phone_optin = ld and ld.phone_opt_in
            
            logger.info(f"[AUTO-RESPONSE] 🔄 UNIFIED NO PHONE LOGIC")
            logger.info(f"[AUTO-RESPONSE] =================== NEW LEAD PROCESSING ===================")
            logger.info(f"[AUTO-RESPONSE] Lead type: {'📱 PHONE OPT-IN LEAD' if is_phone_optin else '💬 REGULAR LEAD'}")
            logger.info(f"[AUTO-RESPONSE] phone_opt_in flag: {is_phone_optin}")
            logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: NO PHONE / CUSTOMER REPLY (unified)")
            
            if is_phone_optin:
                logger.info(f"[AUTO-RESPONSE] 📱 PHONE OPT-IN LEAD PROCESSING:")
                logger.info(f"[AUTO-RESPONSE] - This lead agreed to provide phone number via Yelp")
                logger.info(f"[AUTO-RESPONSE] - Will use No Phone templates (unified logic)")
                logger.info(f"[AUTO-RESPONSE] - Frontend will show 'Phone Opt-In' badge for tracking")
                logger.info(f"[AUTO-RESPONSE] - Same follow-ups as regular no-phone leads")
            else:
                logger.info(f"[AUTO-RESPONSE] 💬 REGULAR NO PHONE LEAD PROCESSING:")
                logger.info(f"[AUTO-RESPONSE] - Standard lead without phone number")
                logger.info(f"[AUTO-RESPONSE] - Will use No Phone templates")
                logger.info(f"[AUTO-RESPONSE] - Standard follow-up sequence")
            
            logger.info(f"[AUTO-RESPONSE] Creating No Phone scenario tasks for lead")
            self._process_auto_response(lead_id, phone_available=False)
            logger.info(f"[AUTO-RESPONSE] ✅ No Phone scenario tasks created")
            
            logger.info(f"[AUTO-RESPONSE] ✅ handle_new_lead completed successfully for {lead_id}")
        except Exception as e:
            logger.error(f"[AUTO-RESPONSE] ❌ handle_new_lead failed for {lead_id}: {e}")
            logger.exception(f"[AUTO-RESPONSE] Exception details for handle_new_lead")
            raise

    # handle_phone_opt_in function REMOVED - phone opt-in now uses No Phone scenario
    # Phone opt-in leads are processed using the same logic as regular no-phone leads
    # This simplifies the system from 3 scenarios to 2 scenarios:
    # 1. No Phone/Customer Reply (phone_available=False) - includes phone opt-in
    # 2. Phone Available (phone_available=True)

    def handle_phone_available(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 📞 STARTING handle_phone_available")
        logger.info(f"[AUTO-RESPONSE] =================== PHONE AVAILABLE SCENARIO ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Handler type: PHONE_AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: Phone Available (1 of 2 scenarios)")
        logger.info(f"[AUTO-RESPONSE] Trigger: Phone number found in consumer text")
        logger.info(f"[AUTO-RESPONSE] Parameters: phone_available=True")
        logger.info(f"[AUTO-RESPONSE] Templates: Will use Phone Available templates and follow-ups")
        
        # Check existing tasks before making changes
        existing_tasks = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📋 EXISTING ACTIVE TASKS BEFORE PHONE AVAILABLE PROCESSING:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {existing_tasks.count()}")
        
        for task in existing_tasks:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_available={task.phone_available}, text='{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] 📞 SCENARIO SELECTED: PHONE AVAILABLE")
        logger.info(f"[AUTO-RESPONSE] ========== PHONE NUMBER PROVIDED SCENARIO ==========")
        
        # ⭐ SMART FRESHNESS CHECK: Skip only if ProcessedLead is OLD (not created recently)
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        logger.info(f"[AUTO-RESPONSE] ProcessedLead exists for {lead_id}: {pl is not None}")
        
        if pl:
            time_since_processed = timezone.now() - pl.processed_at
            
            logger.info(f"[AUTO-RESPONSE] ProcessedLead freshness check:")
            logger.info(f"[AUTO-RESPONSE] - Processed at: {pl.processed_at}")
            logger.info(f"[AUTO-RESPONSE] - Time since processed: {time_since_processed.total_seconds():.1f} seconds")
            logger.info(f"[AUTO-RESPONSE] - Scenario: Phone Found - NO FRESHNESS LIMIT")
            logger.info(f"[AUTO-RESPONSE] ✅ Proceeding with phone available auto-response (no time restrictions for Phone Found scenario)")
            logger.info(f"[AUTO-RESPONSE] Phone Found scenario allows auto-response regardless of ProcessedLead age")
        else:
            logger.info(f"[AUTO-RESPONSE] ✅ No ProcessedLead found - proceeding with phone available flow")
        logger.info(f"[AUTO-RESPONSE] Step 1: Cancelling no-phone tasks")
        
        try:
            self._cancel_no_phone_tasks(lead_id, reason)
            logger.info(f"[AUTO-RESPONSE] Step 2: Starting auto-response for phone available scenario")
            self._process_auto_response(lead_id, phone_available=True)
            logger.info(f"[AUTO-RESPONSE] ✅ handle_phone_available completed successfully for {lead_id}")
        except Exception as e:
            logger.error(f"[AUTO-RESPONSE] ❌ handle_phone_available failed for {lead_id}: {e}")
            logger.exception(f"[AUTO-RESPONSE] Exception details for handle_phone_available")
            raise

    def _send_customer_reply_sms_only(self, lead_id: str):
        """Send SMS notification for Customer Reply scenario without follow-up messages."""
        logger.info(f"[CUSTOMER-REPLY-SMS] 🔧 STARTING _send_customer_reply_sms_only")
        logger.info(f"[CUSTOMER-REPLY-SMS] Lead ID: {lead_id}")
        
        # Check if SMS was already sent for this lead
        ld = LeadDetail.objects.filter(lead_id=lead_id).first()
        if not ld:
            logger.error(f"[CUSTOMER-REPLY-SMS] ❌ No LeadDetail found for lead_id={lead_id}")
            return
            
        if getattr(ld, 'phone_sms_sent', False):
            logger.info(f"[CUSTOMER-REPLY-SMS] 🚫 SKIPPING Customer Reply SMS for lead {lead_id}")
            logger.info(f"[CUSTOMER-REPLY-SMS] Reason: SMS already sent for this lead (phone_sms_sent=True)")
            logger.info(f"[CUSTOMER-REPLY-SMS] Policy: Maximum one SMS per lead")
            return
        
        # Get ProcessedLead to find business
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        if not pl:
            logger.error(f"[CUSTOMER-REPLY-SMS] ❌ No ProcessedLead found for lead_id={lead_id}")
            return
        
        logger.info(f"[CUSTOMER-REPLY-SMS] Business ID: {pl.business_id}")
        
        # 🔒 CRITICAL: Check if SMS notifications are enabled for this business
        logger.info(f"[CUSTOMER-REPLY-SMS] 🔔 CHECKING SMS NOTIFICATIONS STATUS")
        business = YelpBusiness.objects.filter(business_id=pl.business_id).first()
        
        if business:
            logger.info(f"[CUSTOMER-REPLY-SMS] Business found: {business.name}")
            logger.info(f"[CUSTOMER-REPLY-SMS] SMS notifications enabled: {business.sms_notifications_enabled}")
            
            if not business.sms_notifications_enabled:
                logger.info(f"[CUSTOMER-REPLY-SMS] 🚫 SMS NOTIFICATIONS DISABLED for business: {pl.business_id}")
                logger.info(f"[CUSTOMER-REPLY-SMS] Business admin has turned off SMS notifications")
                logger.info(f"[CUSTOMER-REPLY-SMS] 🛑 EARLY RETURN - SMS disabled for this business")
                logger.info(f"[CUSTOMER-REPLY-SMS] This prevents unwanted SMS messages")
                return
            else:
                logger.info(f"[CUSTOMER-REPLY-SMS] ✅ SMS NOTIFICATIONS ENABLED for business: {pl.business_id}")
                logger.info(f"[CUSTOMER-REPLY-SMS] Proceeding with SMS sending")
        else:
            logger.warning(f"[CUSTOMER-REPLY-SMS] ⚠️ Business not found for business_id: {pl.business_id}")
            logger.warning(f"[CUSTOMER-REPLY-SMS] Cannot check SMS enable status - proceeding with caution")
        
        logger.info(f"[CUSTOMER-REPLY-SMS] ✅ SMS allowed - no previous SMS sent for this lead")
        
        # Get NotificationSettings for SMS
        from .models import NotificationSetting
        notification_settings = NotificationSetting.objects.exclude(
            phone_number=""
        ).exclude(message_template="")
        
        # Look for business-specific notification settings
        business_settings = notification_settings.filter(
            business__business_id=pl.business_id
        )
        logger.info(f"[CUSTOMER-REPLY-SMS] Found {business_settings.count()} notification settings for business {pl.business_id}")
        
        if not business_settings.exists():
            logger.warning(f"[CUSTOMER-REPLY-SMS] ⚠️ No NotificationSettings found for business {pl.business_id}")
            return
        
        # LIMIT TO FIRST SETTING ONLY to prevent duplicate SMS
        business_settings_list = list(business_settings)
        if len(business_settings_list) > 1:
            logger.info(f"[CUSTOMER-REPLY-SMS] ⚠️ Multiple NotificationSettings found ({len(business_settings_list)}), using only the first one")
            business_settings_list = business_settings_list[:1]
        
        for setting in business_settings_list:
            try:
                # Format message for Customer Reply SMS
                business_name = pl.business.name if hasattr(pl, 'business') and pl.business else pl.business_id
                yelp_link = f"https://biz.yelp.com/leads_center/{pl.business_id}/leads/{lead_id}"
                
                # Get customer phone number if available
                customer_phone = pl.phone_number if pl and hasattr(pl, 'phone_number') and pl.phone_number else ""
                
                message = setting.message_template.format(
                    business_id=pl.business_id,
                    lead_id=lead_id,
                    business_name=business_name,
                    customer_name="Customer",
                    timestamp=timezone.now().isoformat(),
                    phone=customer_phone,
                    reason="Customer Reply",  # Fixed reason
                    greetings="Hello",
                    yelp_link=yelp_link
                )
                
                logger.info(f"[CUSTOMER-REPLY-SMS] 📤 Sending Customer Reply SMS to {setting.phone_number}")
                
                from .twilio_utils import send_sms
                sid = send_sms(
                    to=setting.phone_number,
                    body=message,
                    lead_id=lead_id,
                    business_id=pl.business_id,
                    purpose="customer_reply"
                )
                
                # Mark SMS as sent to prevent future SMS for this lead
                ld.phone_sms_sent = True
                ld.save(update_fields=['phone_sms_sent'])
                
                logger.info(f"[CUSTOMER-REPLY-SMS] ✅ Customer Reply SMS sent successfully!")
                logger.info(f"[CUSTOMER-REPLY-SMS] - SID: {sid}")
                logger.info(f"[CUSTOMER-REPLY-SMS] - To: {setting.phone_number}")
                logger.info(f"[CUSTOMER-REPLY-SMS] - Purpose: customer_reply")
                logger.info(f"[CUSTOMER-REPLY-SMS] 🏁 Marked phone_sms_sent=True for lead {lead_id} to prevent future SMS")
                
            except Exception as sms_error:
                logger.error(f"[CUSTOMER-REPLY-SMS] ❌ Customer Reply SMS failed: {sms_error}")
                logger.exception(f"[CUSTOMER-REPLY-SMS] SMS sending exception")

    def _process_new_lead_follow_up_only(self, lead_id: str):
        """Process new lead follow-up messages without SMS notifications."""
        logger.info(f"[NEW-LEAD-FOLLOW-UP] 🔧 STARTING _process_new_lead_follow_up_only")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Lead ID: {lead_id}")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] This function sends ONLY follow-up messages, NO SMS")
        
        # Get ProcessedLead to find business
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        if not pl:
            logger.error(f"[NEW-LEAD-FOLLOW-UP] ❌ No ProcessedLead found for lead_id={lead_id}")
            return
        
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Business ID: {pl.business_id}")
        
        # Get authentication token for Yelp API
        logger.info(f"[NEW-LEAD-FOLLOW-UP] 🔐 Getting authentication token")
        try:
            from .utils import get_valid_business_token
            token = get_valid_business_token(pl.business_id)
            logger.info(f"[NEW-LEAD-FOLLOW-UP] ✅ Successfully obtained business token")
        except ValueError as e:
            logger.warning(f"[NEW-LEAD-FOLLOW-UP] ⚠️ No token for business {pl.business_id}: {e}")
            logger.warning(f"[NEW-LEAD-FOLLOW-UP] Cannot send follow-up messages without token")
            return
        
        # Skip SMS processing entirely - go straight to follow-up scheduling
        logger.info(f"[NEW-LEAD-FOLLOW-UP] 📱 SKIPPING SMS processing for new leads")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] 🎯 PROCEEDING WITH follow-up scheduling only")
        
        # Process follow-up messages (copy from _process_auto_response but without SMS)
        from .models import FollowUpTemplate, YelpBusiness
        from .utils import adjust_due_time
        from django.db import transaction
        from django.utils import timezone
        from datetime import timedelta
        import django_rq
        
        # Get customer name and job details for template formatting
        customer_name = getattr(pl, 'customer_name', 'Customer')
        if not customer_name or customer_name.strip() == '':
            customer_name = 'Customer'
        
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Customer name: '{customer_name}'")
        
        # Get job details from ProcessedLead and apply mappings
        job_names = ["your project"]  # default
        
        # Try to get job names from ProcessedLead
        if hasattr(pl, 'project_data') and pl.project_data:
            try:
                import json
                project = json.loads(pl.project_data) if isinstance(pl.project_data, str) else pl.project_data
                if isinstance(project, dict) and 'job_names' in project:
                    job_names = project['job_names']
            except Exception as e:
                logger.warning(f"[NEW-LEAD-FOLLOW-UP] Error parsing project_data: {e}")
        
        # Apply job mappings using existing method
        mapped_job_names = self._apply_job_mappings(job_names)
        jobs = ', '.join(mapped_job_names) if mapped_job_names else "your project"
        sep = ", "
        
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Original jobs: {job_names}")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Mapped jobs: '{jobs}', Separator: '{sep}'")
        
        # Get follow-up templates for new leads (phone_available=False)
        now = timezone.now()
        phone_available = False
        
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Looking for FollowUpTemplate with phone_available=False")
        
        tpls = FollowUpTemplate.objects.filter(
            active=True,
            phone_available=phone_available,
            business__business_id=pl.business_id,
        )
        if not tpls.exists():
            tpls = FollowUpTemplate.objects.filter(
                active=True,
                phone_available=phone_available,
                business__isnull=True,
            )
        
        logger.info(f"[NEW-LEAD-FOLLOW-UP] Found {tpls.count()} follow-up templates")
        
        if not tpls.exists():
            logger.warning(f"[NEW-LEAD-FOLLOW-UP] ⚠️ No follow-up templates found for new leads")
            return
        
        business = YelpBusiness.objects.filter(business_id=pl.business_id).first()
        scheduled_count = 0
        
        for tmpl in tpls:
            delay = tmpl.delay.total_seconds()
            text = tmpl.template.format(
                name=customer_name, 
                jobs=jobs, 
                sep=sep, 
                reason="New Lead",  # Fixed reason for new leads
                greetings="Hello"
            )
            
            logger.info(f"[NEW-LEAD-FOLLOW-UP] Scheduling template: '{tmpl.name}' with delay: {tmpl.delay}")
            
            initial_due = now + timedelta(seconds=delay)
            due = adjust_due_time(
                initial_due,
                business.time_zone if business else None,
                tmpl.open_from,
                tmpl.open_to,
            )
            
            countdown = max((due - now).total_seconds(), 0)
            
            logger.info(f"[NEW-LEAD-FOLLOW-UP] Scheduling follow-up in {countdown} seconds")
            
            with transaction.atomic():
                try:
                    from .models import LeadPendingTask
                    normalized_task_text = normalize_text_for_comparison(text)
                    LeadPendingTask.objects.create(
                        lead_id=lead_id,
                        text=normalized_task_text,  # Store normalized text
                        task_id="",  # Will be set when task is enqueued
                        phone_available=phone_available,
                        active=True,
                    )
                    
                    queue = django_rq.get_queue("default")
                    job = queue.enqueue_in(
                        timedelta(seconds=countdown),
                        "webhooks.tasks.send_follow_up",
                        lead_id,
                        text,
                        business_id=pl.business_id,
                    )
                    
                    # Update task with job ID
                    LeadPendingTask.objects.filter(
                        lead_id=lead_id, text=text, task_id=""
                    ).update(task_id=job.id)
                    
                    scheduled_count += 1
                    logger.info(f"[NEW-LEAD-FOLLOW-UP] ✅ Scheduled follow-up '{tmpl.name}' with job ID: {job.id}")
                    
                except Exception as e:
                    logger.error(f"[NEW-LEAD-FOLLOW-UP] ❌ Failed to schedule follow-up '{tmpl.name}': {e}")
        
        logger.info(f"[NEW-LEAD-FOLLOW-UP] ✅ NEW LEAD FOLLOW-UP COMPLETED")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] - Lead ID: {lead_id}")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] - Follow-ups scheduled: {scheduled_count}")
        logger.info(f"[NEW-LEAD-FOLLOW-UP] - SMS sent: 0 (disabled for new leads)")

    def _cancel_no_phone_tasks(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_no_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] =================== TASK CANCELLATION ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] TARGET: Tasks with phone_available=False, active=True")
        
        # Show all active tasks first
        all_active = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📊 ALL ACTIVE TASKS BEFORE CANCELLATION:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {all_active.count()}")
        
        for task in all_active:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_available={task.phone_available}, active={task.active}")
            logger.info(f"[AUTO-RESPONSE]   Text: '{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] 🔍 FILTERING FOR CANCELLATION TARGET:")
        
        pending = LeadPendingTask.objects.filter(
            lead_id=lead_id, phone_available=False, active=True
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

    def _cancel_pre_phone_tasks(self, lead_id: str, reason: str | None = None):
        """Cancel all pre-phone tasks including phone opt-in tasks."""
        logger.info(f"[AUTO-RESPONSE] 🚫 STARTING _cancel_pre_phone_tasks")
        logger.info(f"[AUTO-RESPONSE] =================== PRE-PHONE TASK CANCELLATION ===================")
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Cancellation reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] TARGET: Tasks with phone_available=False AND active=True")
        
        # Show all active tasks first
        all_active = LeadPendingTask.objects.filter(lead_id=lead_id, active=True)
        logger.info(f"[AUTO-RESPONSE] 📊 ALL ACTIVE TASKS BEFORE PRE-PHONE CANCELLATION:")
        logger.info(f"[AUTO-RESPONSE] - Total active tasks: {all_active.count()}")
        
        for task in all_active:
            logger.info(f"[AUTO-RESPONSE] - Task {task.task_id}: phone_available={task.phone_available}, active={task.active}")
            logger.info(f"[AUTO-RESPONSE]   Text: '{task.text[:50]}...'")
        
        logger.info(f"[AUTO-RESPONSE] 🔍 FILTERING FOR PRE-PHONE CANCELLATION TARGET:")
        
        # Cancel phone_available=False tasks (No Phone scenario)
        pending = LeadPendingTask.objects.filter(
            lead_id=lead_id, 
            phone_available=False,
            active=True
        )
        pending_count = pending.count()
        logger.info(f"[AUTO-RESPONSE] Found {pending_count} pending pre-phone tasks to cancel")
        
        if pending_count == 0:
            logger.info(f"[AUTO-RESPONSE] No pre-phone tasks to cancel for {lead_id}")
            return
            
        queue = django_rq.get_queue("default")
        scheduler = django_rq.get_scheduler("default")
        
        cancelled_count = 0
        error_count = 0
        
        for p in pending:
            logger.info(f"[AUTO-RESPONSE] Cancelling task: {p.task_id} for lead {lead_id}")
            logger.info(f"[AUTO-RESPONSE] Task details: phone_available={p.phone_available}")
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
            
        logger.info(f"[AUTO-RESPONSE] 📊 _cancel_pre_phone_tasks summary for {lead_id}:")
        logger.info(f"[AUTO-RESPONSE] - Tasks found: {pending_count}")
        logger.info(f"[AUTO-RESPONSE] - Tasks cancelled successfully: {cancelled_count}")
        logger.info(f"[AUTO-RESPONSE] - Tasks with errors: {error_count}")
        logger.info(f"[AUTO-RESPONSE] ✅ _cancel_pre_phone_tasks completed")

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
        self, lead_id: str, phone_available: bool
    ):
        logger.info(f"[AUTO-RESPONSE] 🔧 STARTING _process_auto_response")
        logger.info(f"[AUTO-RESPONSE] =================== SCENARIO PROCESSING ===================")
        logger.info(f"[AUTO-RESPONSE] Parameters:")
        logger.info(f"[AUTO-RESPONSE] - Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] - phone_available: {phone_available}")
        
        # Determine scenario name and reason for SMS (2-scenario system)
        if phone_available:
            scenario_name = "📞 PHONE AVAILABLE"
            reason = "Phone Number Found"
            scenario_description = "Lead provided phone number in text or consumer response"
        else:
            scenario_name = "💬 NO PHONE / CUSTOMER REPLY"
            reason = "Customer Reply"
            scenario_description = "Regular lead without phone OR phone opt-in lead (unified)"
        
        logger.info(f"[AUTO-RESPONSE] 🎯 SCENARIO: {scenario_name}")
        logger.info(f"[AUTO-RESPONSE] Description: {scenario_description}")
        logger.info(f"[AUTO-RESPONSE] SMS Reason: {reason}")
        logger.info(f"[AUTO-RESPONSE] =================== SCENARIO DETAILS ===================")
        logger.info(f"[AUTO-RESPONSE] System now uses 2 scenarios instead of 3:")
        logger.info(f"[AUTO-RESPONSE] 1. 💬 No Phone/Customer Reply (phone_available=False)")
        logger.info(f"[AUTO-RESPONSE] 2. 📞 Phone Available (phone_available=True)")
        logger.info(f"[AUTO-RESPONSE] Current scenario parameters:")
        logger.info(f"[AUTO-RESPONSE] - phone_available={phone_available}")
        logger.info(f"[AUTO-RESPONSE] Will look for AutoResponseSettings with these parameters")
        
        # Step 1: Look up settings
        logger.info(f"[AUTO-RESPONSE] 🔍 STEP 1: Looking up AutoResponseSettings")
        logger.info(f"[AUTO-RESPONSE] ========== SMS SETTINGS LOOKUP ==========")
        logger.info(f"[AUTO-RESPONSE] Search criteria:")
        logger.info(f"[AUTO-RESPONSE] - business__isnull=True (global settings)")
        logger.info(f"[AUTO-RESPONSE] - phone_available={phone_available}")
        
        # Debug: Show all AutoResponseSettings in database
        all_auto_settings = AutoResponseSettings.objects.all()
        logger.info(f"[AUTO-RESPONSE] 📊 ALL AutoResponseSettings in database:")
        if all_auto_settings.exists():
            for setting in all_auto_settings:
                logger.info(f"[AUTO-RESPONSE] - ID={setting.id}, business={setting.business}, phone_available={setting.phone_available}, enabled={setting.enabled}")
                if hasattr(setting, 'sms_on_customer_reply'):
                    logger.info(f"[AUTO-RESPONSE]   sms_on_customer_reply={setting.sms_on_customer_reply}, sms_on_phone_found={setting.sms_on_phone_found}, sms_on_phone_opt_in={setting.sms_on_phone_opt_in}")
        else:
            logger.info(f"[AUTO-RESPONSE] ❌ NO AutoResponseSettings found in database!")
        
        default_settings = AutoResponseSettings.objects.filter(
            business__isnull=True,
            phone_available=phone_available,
        ).first()
        logger.info(f"[AUTO-RESPONSE] 🎯 Default settings found: {default_settings is not None}")
        if default_settings:
            logger.info(f"[AUTO-RESPONSE] ✅ Default settings details:")
            logger.info(f"[AUTO-RESPONSE] - ID: {default_settings.id}")
            logger.info(f"[AUTO-RESPONSE] - enabled: {default_settings.enabled}")
            logger.info(f"[AUTO-RESPONSE] - phone_available: {default_settings.phone_available}")
            if hasattr(default_settings, 'sms_on_customer_reply'):
                logger.info(f"[AUTO-RESPONSE] - sms_on_customer_reply: {default_settings.sms_on_customer_reply}")
                logger.info(f"[AUTO-RESPONSE] - sms_on_phone_found: {default_settings.sms_on_phone_found}")
                logger.info(f"[AUTO-RESPONSE] - sms_on_phone_opt_in: {default_settings.sms_on_phone_opt_in}")
        else:
            logger.error(f"[AUTO-RESPONSE] ❌ NO MATCHING AutoResponseSettings!")
            logger.error(f"[AUTO-RESPONSE] This means SMS won't be sent for {reason} scenario")
            logger.error(f"[AUTO-RESPONSE] Need AutoResponseSettings with business=null, phone_available={phone_available}")
        
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
            if phone_available:
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
                
                # Get NotificationSettings for this business to send SMS
                from .models import NotificationSetting
                notification_settings = NotificationSetting.objects.exclude(
                    phone_number=""
                ).exclude(message_template="")
                
                if pl and pl.business_id:
                    # Look for business-specific notification settings
                    business_settings = notification_settings.filter(
                        business__business_id=pl.business_id
                    )
                    logger.info(f"[AUTO-RESPONSE] Found {business_settings.count()} notification settings for business {pl.business_id}")
                    
                    if business_settings.exists():
                        # LIMIT TO FIRST SETTING ONLY to prevent duplicate SMS
                        business_settings_list = list(business_settings)
                        if len(business_settings_list) > 1:
                            logger.info(f"[AUTO-RESPONSE] ⚠️ Multiple NotificationSettings found ({len(business_settings_list)}), using only the first one")
                            logger.info(f"[AUTO-RESPONSE] This prevents duplicate AutoResponse SMS notifications")
                            logger.info(f"[AUTO-RESPONSE] Available settings:")
                            for i, s in enumerate(business_settings_list, 1):
                                logger.info(f"[AUTO-RESPONSE] - Setting #{i}: ID={s.id}, phone={s.phone_number}")
                            business_settings_list = business_settings_list[:1]  # Take only the first setting
                            logger.info(f"[AUTO-RESPONSE] Selected setting: ID={business_settings_list[0].id}, phone={business_settings_list[0].phone_number}")
                        
                        for setting in business_settings_list:
                            ld = LeadDetail.objects.filter(lead_id=lead_id).first()
                            if phone_available and ld and getattr(ld, "phone_sms_sent", False):
                                logger.info(
                                    f"[AUTO-RESPONSE] 🚫 Skipping AutoResponseSettings SMS for lead {lead_id} - phone_sms_sent already True"
                                )
                                continue
                            try:
                                # Format message for AutoResponseSettings SMS
                                business_name = pl.business.name if hasattr(pl, 'business') and pl.business else pl.business_id
                                yelp_link = f"https://biz.yelp.com/leads_center/{pl.business_id}/leads/{lead_id}"
                                
                                # Get customer phone number if available
                                customer_phone = pl.phone_number if pl and hasattr(pl, 'phone_number') and pl.phone_number else ""
                                
                                message = setting.message_template.format(
                                    business_id=pl.business_id,
                                    lead_id=lead_id,
                                    business_name=business_name,
                                    customer_name="Customer",  # We don't have customer name here
                                    timestamp=timezone.now().isoformat(),
                                    phone=customer_phone,  # Real customer phone number or empty
                                    reason=reason,
                                    greetings="Hello",
                                    yelp_link=yelp_link
                                )
                                
                                logger.info(f"[AUTO-RESPONSE] 📤 Sending AutoResponseSettings SMS to {setting.phone_number}")
                                
                                from .twilio_utils import send_sms
                                sid = send_sms(
                                    to=setting.phone_number,
                                    body=message,
                                    lead_id=lead_id,
                                    business_id=pl.business_id,
                                    purpose="auto_response"
                                )
                                if phone_available and ld and not getattr(ld, "phone_sms_sent", False):
                                    ld.phone_sms_sent = True
                                    ld.save(update_fields=["phone_sms_sent"])
                                    logger.info(
                                        f"[AUTO-RESPONSE] 🏁 Marked phone_sms_sent=True for lead {lead_id} after AutoResponse SMS"
                                    )
                                
                                logger.info(f"[AUTO-RESPONSE] ✅ AutoResponseSettings SMS sent successfully!")
                                logger.info(f"[AUTO-RESPONSE] - SID: {sid}")
                                logger.info(f"[AUTO-RESPONSE] - To: {setting.phone_number}")
                                logger.info(f"[AUTO-RESPONSE] - Scenario: {reason}")
                                
                            except Exception as sms_error:
                                logger.error(f"[AUTO-RESPONSE] ❌ AutoResponseSettings SMS failed: {sms_error}")
                                logger.exception(f"[AUTO-RESPONSE] SMS sending exception")
                    else:
                        logger.warning(f"[AUTO-RESPONSE] ⚠️ No NotificationSettings found for business {pl.business_id}")
                        logger.warning(f"[AUTO-RESPONSE] SMS decision was True but no phone numbers to send to")
                else:
                    logger.error(f"[AUTO-RESPONSE] ❌ Cannot send SMS - no business context found")
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

        # 🔍 DETAILED PHONE NUMBER EXTRACTION DEBUG
        additional_info_raw = raw_proj.get("additional_info", "")
        logger.info(f"[PHONE-EXTRACTION] 📞 PHONE NUMBER EXTRACTION DEBUG:")
        logger.info(f"[PHONE-EXTRACTION] - additional_info raw: '{additional_info_raw}'")
        logger.info(f"[PHONE-EXTRACTION] - additional_info type: {type(additional_info_raw)}")
        logger.info(f"[PHONE-EXTRACTION] - additional_info length: {len(additional_info_raw)}")
        
        phone_number = _extract_phone(additional_info_raw) or ""
        
        logger.info(f"[PHONE-EXTRACTION] - _extract_phone result: '{phone_number}'")
        logger.info(f"[PHONE-EXTRACTION] - phone_number type: {type(phone_number)}")
        logger.info(f"[PHONE-EXTRACTION] - phone_number length: {len(phone_number) if phone_number else 0}")
        logger.info(f"[PHONE-EXTRACTION] - phone_number bool: {bool(phone_number)}")
        logger.info(f"[PHONE-EXTRACTION] - Final phone_number value: '{phone_number}'")

        # 🔍 DETAILED LEAD DATA PREPARATION DEBUG
        logger.info(f"[LEAD-DATA] 📋 PREPARING DETAIL_DATA:")
        logger.info(f"[LEAD-DATA] - phone_number for detail_data: '{phone_number}'")
        logger.info(f"[LEAD-DATA] - phone_number type: {type(phone_number)}")
        logger.info(f"[LEAD-DATA] - phone_number bool: {bool(phone_number)}")

        display_name = d.get("user", {}).get("display_name", "")
        first_name = display_name.split()[0] if display_name else ""

        existing_ld = LeadDetail.objects.filter(lead_id=lead_id).first()
        phone_opt_in_value = d.get("phone_opt_in", False)
        if existing_ld and existing_ld.phone_opt_in:
            phone_opt_in_value = True

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
            "phone_opt_in": phone_opt_in_value,
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
        
        # 🔍 DETAILED DATABASE SAVE VERIFICATION
        logger.info(f"[LEAD-SAVE] 💾 LEADDETAL SAVE VERIFICATION:")
        logger.info(f"[LEAD-SAVE] - Created: {created}")
        logger.info(f"[LEAD-SAVE] - LeadDetail.id: {ld.id}")
        logger.info(f"[LEAD-SAVE] - LeadDetail.phone_number from DB: '{ld.phone_number}'")
        logger.info(f"[LEAD-SAVE] - LeadDetail.phone_number type: {type(ld.phone_number)}")
        logger.info(f"[LEAD-SAVE] - LeadDetail.phone_number bool: {bool(ld.phone_number)}")
        logger.info(f"[LEAD-SAVE] - Original phone_number variable: '{phone_number}'")

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
                logger.info(f"[PHONE-SAVE] 💾 SAVING PHONE NUMBER TO DATABASE:")
                logger.info(f"[PHONE-SAVE] - Before save: ld.phone_number = '{ld.phone_number}'")
                logger.info(f"[PHONE-SAVE] - New value to save: '{phone_number}'")
                logger.info(f"[PHONE-SAVE] - Phone type: {type(phone_number)}")
                logger.info(f"[PHONE-SAVE] - Phone length: {len(phone_number)}")
                
                ld.phone_number = phone_number
                ld.save(update_fields=["phone_number"])
                
                logger.info(f"[PHONE-SAVE] - After save: ld.phone_number = '{ld.phone_number}'")
                logger.info(f"[PHONE-SAVE] ✅ Phone number saved successfully to LeadDetail")
            
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
                    normalized_greet_text = normalize_text_for_comparison(greet_text)
                    task_record = LeadPendingTask.objects.create(
                        lead_id=lead_id,
                        task_id=res.id,
                        text=normalized_greet_text,  # Store normalized text
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
            phone_available=phone_available,
            business__business_id=biz_id,
        )
        if not tpls.exists():
            tpls = FollowUpTemplate.objects.filter(
                active=True,
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
                        normalized_followup_text = normalize_text_for_comparison(text)
                        LeadPendingTask.objects.create(
                            lead_id=lead_id,
                            task_id=res.id,
                            text=normalized_followup_text,  # Store normalized text
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
        logger.info(f"[AUTO-RESPONSE] Scenario: phone_available={phone_available}")
        logger.info(f"[AUTO-RESPONSE] Messages scheduled: {len(scheduled_texts)}")
        logger.info(f"[AUTO-RESPONSE] Auto responses enabled: {auto_settings.enabled if auto_settings else 'N/A'}")
        logger.info(f"[AUTO-RESPONSE] AI generation used: {getattr(auto_settings, 'use_ai_greeting', False) if auto_settings else 'N/A'}")
        logger.info(f"[AUTO-RESPONSE] ✅ PROCESS AUTO RESPONSE COMPLETED")
        logger.info(f"[AUTO-RESPONSE] =======================================")
