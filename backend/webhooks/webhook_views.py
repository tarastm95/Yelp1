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
            "[WEBHOOK] Verifying new lead via %s with params=%s",
            url,
            {"limit": 2},
        )
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 2},
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
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    if updated:
                        self.handle_phone_opt_in(lid)
                        
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
                        if pending:
                            LeadDetail.objects.filter(lead_id=lid).update(
                                phone_in_dialog=True
                            )
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
                if LeadEvent.objects.filter(
                    lead_id=lid, text=defaults["text"], from_backend=True
                ).exists():
                    defaults["from_backend"] = True
                logger.info(f"[WEBHOOK] Upserting LeadEvent id={eid} for lead={lid}")
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
                text = defaults.get("text", "")
                phone = _extract_phone(text)
                has_phone = bool(phone)
                
                # ❌ СТАРИЙ КОД: is_new = created
                # ✅ НОВИЙ КОД: Перевіряємо чи це справжня нова подія клієнта
                event_time_str = e.get("time_created")
                event_time = parse_datetime(event_time_str) if event_time_str else None
                
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
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    if updated:
                        self.handle_phone_opt_in(lid)

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
                        if pending:
                            LeadDetail.objects.filter(lead_id=lid).update(
                                phone_in_dialog=True
                            )
                            reason = "Client responded with a number → switched to the 'phone available' scenario"
                            logger.info(f"[WEBHOOK] 🔄 SWITCHING TO PHONE AVAILABLE scenario")
                            self.handle_phone_available(lid, reason=reason)
                        else:
                            logger.info(f"[WEBHOOK] 🔄 TRIGGERING PHONE AVAILABLE flow (no pending tasks)")
                            self.handle_phone_available(lid)
                    elif pending:
                        logger.info(f"[WEBHOOK] 🚫 CLIENT RESPONDED WITHOUT PHONE NUMBER")
                        logger.info(f"[WEBHOOK] Will cancel pending no-phone tasks")
                        reason = "Client responded, but no number was found"
                        self._cancel_no_phone_tasks(lid, reason=reason)
                    else:
                        logger.info(f"[WEBHOOK] ℹ️ CLIENT RESPONDED but no pending tasks to handle")
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
                    
                    # Спосіб 1: Перевірка по from_backend (стара логіка)
                    if defaults.get("from_backend"):
                        is_our_message = True
                        logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (from_backend=True)")
                    
                    # Спосіб 2: Перевірка чи текст відповідає активному завданню
                    if not is_our_message and text:
                        matching_tasks = LeadPendingTask.objects.filter(
                            lead_id=lid,
                            text=text,
                            active=True
                        ).exists()
                        if matching_tasks:
                            is_our_message = True
                            logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (matches active task)")
                        else:
                            logger.info(f"[WEBHOOK] ❌ Text does NOT match any active tasks")
                    
                    # Спосіб 3: Перевірка чи текст був відправлений раніше нашою системою
                    if not is_our_message and text:
                        sent_by_us = LeadEvent.objects.filter(
                            lead_id=lid,
                            text=text,
                            from_backend=True
                        ).exists()
                        if sent_by_us:
                            is_our_message = True
                            logger.info(f"[WEBHOOK] ✅ IDENTIFIED as our message (previously sent by backend)")
                        else:
                            logger.info(f"[WEBHOOK] ❌ Text was NOT previously sent by our backend")
                    
                    # Спосіб 4: Перевірка часу - якщо дуже скоро після обробки ліда, це ймовірно наше повідомлення
                    if not is_our_message and event_time and processed_at:
                        time_diff_seconds = (event_time - processed_at).total_seconds()
                        if 0 < time_diff_seconds < 300:  # Менше 5 хвилин після обробки
                            logger.info(f"[WEBHOOK] 🕐 Event happened {time_diff_seconds:.1f}s after processing")
                            logger.info(f"[WEBHOOK] This suggests it might be our automated message")
                            # Не встановлюємо is_our_message=True, але логуємо підозру
                        
                    if is_our_message:
                        logger.info(f"[WEBHOOK] 🤖 CONFIRMED: This is OUR automated message")
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
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Basic new lead (phone_opt_in=False, phone_available=False)")
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
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone opt-in received (phone_opt_in=True, phone_available=False)")
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
        logger.info(f"[AUTO-RESPONSE] Lead ID: {lead_id}")
        logger.info(f"[AUTO-RESPONSE] Reason: {reason or 'Not specified'}")
        logger.info(f"[AUTO-RESPONSE] Scenario: Phone number available (phone_opt_in=False, phone_available=True)")
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
        
        # Step 1: Look up settings
        logger.info(f"[AUTO-RESPONSE] 🔍 STEP 1: Looking up AutoResponseSettings")
        
        default_settings = AutoResponseSettings.objects.filter(
            business__isnull=True,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available,
        ).first()
        logger.info(f"[AUTO-RESPONSE] Default settings found: {default_settings is not None}")
        if default_settings:
            logger.info(f"[AUTO-RESPONSE] Default settings ID: {default_settings.id}, enabled: {default_settings.enabled}")
        
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
            
            # Step 2: Get authentication token
            logger.info(f"[AUTO-RESPONSE] 🔐 STEP 2: Getting authentication token")
            try:
                token = get_valid_business_token(pl.business_id)
                logger.info(f"[AUTO-RESPONSE] ✅ Successfully obtained business token")
                logger.debug(
                    f"[AUTO-RESPONSE] Obtained business token for {pl.business_id}: {token[:20]}..."
                )
            except ValueError as e:
                logger.error(
                    f"[AUTO-RESPONSE] ❌ No token for business {pl.business_id}; skipping auto-response"
                )
                logger.error(f"[AUTO-RESPONSE] Token error: {e}")
                return
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
        biz_id = pl.business_id if pl else None
        logger.info(
            "[AUTO-RESPONSE] Using AutoResponseSettings for business=%s, lead=%s, export_to_sheets=%s",
            biz_id,
            lead_id,
            getattr(auto_settings, "export_to_sheets", None),
        )

        detail_url = f"https://api.yelp.com/v3/leads/{lead_id}"
        headers = {"Authorization": f"Bearer {token}"}
        logger.debug(
            f"[AUTO-RESPONSE] Fetching lead details from {detail_url} using token {token}"
        )
        resp = requests.get(detail_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            source = f"business {pl.business_id}" if pl else "unknown"
            logger.error(
                f"[AUTO-RESPONSE] DETAIL ERROR lead={lead_id}, business_id={pl.business_id if pl else 'N/A'}, "
                f"token_source={source}, token={token}, status={resp.status_code}, body={resp.text}"
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

        # If a phone number is present in additional_info when the lead detail is
        # fetched for the first time, treat it as a real phone provided by the
        # consumer and switch to the phone available flow.
        if not phone_available and PHONE_RE.search(
            detail_data["project"].get("additional_info", "")
        ):
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

            if not ld.phone_in_additional_info:
                ld.phone_in_additional_info = True
                ld.save(update_fields=["phone_in_additional_info"])
            if phone_number:
                ld.phone_number = phone_number
                ld.save(update_fields=["phone_number"])
            logger.info("[AUTO-RESPONSE] Phone found in additional_info")
            self.handle_phone_available(
                lead_id, reason="phone number found in additional_info"
            )
            return

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

        if not auto_settings or not auto_settings.enabled:
            logger.info("[AUTO-RESPONSE] Auto responses disabled; skipping messages")
            return

        name = ld.user_display_name
        jobs = ", ".join(ld.project.get("job_names", []))
        sep = ", " if name and jobs else ""
        biz_id = ld.business_id if ld else None
        business = YelpBusiness.objects.filter(business_id=biz_id).first()

        greeting = auto_settings.greeting_template.format(name=name, jobs=jobs, sep=sep)
        off_greeting = auto_settings.greeting_off_hours_template.format(
            name=name, jobs=jobs, sep=sep
        )

        now = timezone.now()
        tz_name = business.time_zone if business else None
        within_hours = True
        if tz_name:
            tz = ZoneInfo(tz_name)
            local_now = now.astimezone(tz)
            days_setting = (
                auto_settings.greeting_open_days if phone_available else None
            )
            allowed_days = _parse_days(days_setting)
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
            within_hours = (
                local_now.weekday() in allowed_days and open_dt <= local_now < close_dt
            )

        if within_hours:
            due = adjust_due_time(
                now + timedelta(seconds=auto_settings.greeting_delay),
                tz_name,
                auto_settings.greeting_open_from,
                auto_settings.greeting_open_to,
                days_setting,
            )
            greet_text = greeting
        else:
            due = now + timedelta(seconds=auto_settings.greeting_delay)
            greet_text = off_greeting

        scheduled_texts = set()

        with transaction.atomic():
            if (
                _already_sent(lead_id, greet_text)
                or LeadPendingTask.objects.select_for_update()
                .filter(lead_id=lead_id, text=greet_text, active=True)
                .exists()
            ):
                logger.info(
                    "[AUTO-RESPONSE] Greeting already sent or queued → skipping"
                )
            elif due <= now:
                send_follow_up.apply_async(
                    args=[lead_id, greet_text],
                    headers={"business_id": biz_id},
                    countdown=0,
                )
                logger.info(
                    "[AUTO-RESPONSE] Greeting dispatched immediately via Celery"
                )
                scheduled_texts.add(greet_text)
            else:
                countdown = (due - now).total_seconds()
                res = send_follow_up.apply_async(
                    args=[lead_id, greet_text],
                    headers={"business_id": biz_id},
                    countdown=countdown,
                )
                try:
                    LeadPendingTask.objects.create(
                        lead_id=lead_id,
                        task_id=res.id,
                        text=greet_text,
                        phone_opt_in=phone_opt_in,
                        phone_available=phone_available,
                    )
                except IntegrityError:
                    logger.info(
                        "[AUTO-RESPONSE] Duplicate pending task already exists → skipping"
                    )
                else:
                    logger.info(
                        f"[AUTO-RESPONSE] Greeting scheduled at {due.isoformat()}"
                    )
                    scheduled_texts.add(greet_text)

        if phone_available:
            return

        now = timezone.now()

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
            delay = int(tmpl.delay.total_seconds())
            text = tmpl.template.format(name=name, jobs=jobs, sep=sep)
            due = adjust_due_time(
                now + timedelta(seconds=delay),
                business.time_zone if business else None,
                tmpl.open_from,
                tmpl.open_to,
            )
            countdown = max((due - now).total_seconds(), 0)
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
                            f"[AUTO-RESPONSE] Custom follow-up “{tmpl.name}” scheduled at {due.isoformat()}"
                        )
                        scheduled_texts.add(text)
