import logging
import time
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.utils.dateparse import parse_datetime
import re
import requests
from config import celery as config
from django.utils import timezone
from django.db import transaction, OperationalError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    Event,
    ProcessedLead,
    AutoResponseSettings,
    ScheduledMessage,
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
)
from .tasks import send_follow_up
from .tasks import send_scheduled_message

logger = logging.getLogger(__name__)

# Simple pattern to detect phone numbers like +380XXXXXXXXX or other
# international formats with optional spaces or dashes.
PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")


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
    logger.debug(
        f"[DB RETRY] Final attempt for {model.__name__}.update_or_create"
    )
    return model.objects.update_or_create(defaults=defaults or {}, **kwargs)


def _already_sent(lead_id: str, text: str) -> bool:
    """Return True if this lead already received exactly this text."""
    if LeadEvent.objects.filter(lead_id=lead_id, text=text).exists():
        return True
    # Consider tasks that are already scheduled or in progress to
    # avoid queuing duplicates while the first one hasn't finished yet
    return CeleryTaskLog.objects.filter(
        name__endswith="send_follow_up",
        args__0=lead_id,
        args__1=text,
        status__in=["SCHEDULED", "STARTED", "SUCCESS"],
    ).exists()


class WebhookView(APIView):
    """Handle incoming webhook events from Yelp."""

    def _is_new_lead(self, lead_id: str, business_id: str | None = None) -> dict:
        """Check Yelp events to verify if this lead is new.

        When ``business_id`` is provided the access token is obtained for that
        business.  Otherwise it falls back to :func:`get_token_for_lead`.

        Returns a JSON-like dict ``{"new_lead": bool}`` where ``new_lead`` is
        ``True`` when only a single consumer event exists.
        """
        if business_id:
            token = get_valid_business_token(business_id)
        else:
            token = get_token_for_lead(lead_id)
        if not token:
            logger.error("[WEBHOOK] No token available for lead=%s", lead_id)
            return {"new_lead": False}
        url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 2},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(
                f"[WEBHOOK] Failed to verify new lead {lead_id}: {resp.status_code}"
            )
            return {"new_lead": False}

        events = resp.json().get("events", [])
        is_new = len(events) == 1 and events[0].get("user_type") == "CONSUMER"
        return {"new_lead": is_new}

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
                if upd.get("event_type") != "NEW_LEAD" and not ProcessedLead.objects.filter(lead_id=lid).exists():
                    check = self._is_new_lead(lid, payload["data"].get("id"))
                    if check.get("new_lead"):
                        upd["event_type"] = "NEW_LEAD"
                        logger.info(f"[WEBHOOK] Marked lead={lid} as NEW_LEAD via events check")
                if upd.get("event_type") == "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT":
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    if updated:
                        self.handle_phone_opt_in(lid)
                if (
                    upd.get("event_type") == "NEW_EVENT"
                    and upd.get("user_type") == "CONSUMER"
                ):
                    content = upd.get("event_content", {}) or {}
                    text = content.get("text") or content.get("fallback_text", "")
                    has_phone = bool(text and PHONE_RE.search(text))
                    pending = LeadPendingTask.objects.filter(
                        lead_id=lid, phone_opt_in=False, phone_available=False, active=True
                    ).exists()
                    if has_phone:
                        updated = LeadDetail.objects.filter(
                            lead_id=lid, phone_in_text=False
                        ).update(phone_in_text=True)
                        trigger = updated or pending
                        if pending:
                            LeadDetail.objects.filter(lead_id=lid).update(phone_in_dialog=True)
                        if trigger:
                            reason = (
                                "Клієнт відповів із номером → переключено на сценарій phone available"
                                if pending
                                else None
                            )
                            self.handle_phone_available(lid, reason=reason)
                    elif pending:
                        reason = "Клієнт відповів, але номеру не знайдено"
                        self._cancel_no_phone_tasks(lid, reason=reason)
        logger.info(f"[WEBHOOK] Lead IDs to process: {lead_ids}")

        for upd in updates:
            if upd.get("event_type") == "NEW_LEAD":
                lid = upd["lead_id"]
                pl, created = ProcessedLead.objects.get_or_create(
                    business_id=payload["data"]["id"],
                    lead_id=lid,
                )
                if created:
                    logger.info(f"[WEBHOOK] Created ProcessedLead id={pl.id} for lead={lid}")
                    logger.info(f"[WEBHOOK] Calling handle_new_lead for lead={lid}")
                    self.handle_new_lead(lid)
                else:
                    logger.info(f"[WEBHOOK] Lead {lid} already processed; skipping handle_new_lead")

        biz_id = payload["data"].get("id")
        for lid in lead_ids:
            token = get_valid_business_token(biz_id)
            logger.info(
                f"[WEBHOOK] Using business token for lead={lid}: {token}"
            )
            url = f"https://api.yelp.com/v3/leads/{lid}/events"
            params = {"limit": 20}
            resp = requests.get(
                url, headers={"Authorization": f"Bearer {token}"}, params=params
            )
            logger.info(
                f"[WEBHOOK] Yelp response status for lead={lid}: {resp.status_code}"
            )

            if resp.status_code != 200:
                logger.error(f"[WEBHOOK] Failed to fetch events for lead={lid}: {resp.text}")
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
                    "text": e["event_content"].get("text") or e["event_content"].get("fallback_text", ""),
                    "cursor": e.get("cursor", ""),
                    "time_created": e.get("time_created"),
                    "raw": e,
                }
                logger.info(f"[WEBHOOK] Upserting LeadEvent id={eid} for lead={lid}")
                obj, created = safe_update_or_create(LeadEvent, defaults=defaults, event_id=eid)
                logger.info(f"[WEBHOOK] LeadEvent saved pk={obj.pk}, created={created}")

                processed_at = (
                    ProcessedLead.objects.filter(lead_id=lid)
                    .values_list("processed_at", flat=True)
                    .first()
                )
                event_dt = parse_datetime(defaults.get("time_created"))
                text = defaults.get("text", "")
                has_phone = bool(text and PHONE_RE.search(text))
                is_new = created
                if processed_at and event_dt:
                    is_new = is_new and event_dt > processed_at

                if not is_new and not has_phone:
                    logger.info("[WEBHOOK] Skipping old event without phone")
                    continue

                if e.get("event_type") == "CONSUMER_PHONE_NUMBER_OPT_IN_EVENT":
                    updated = LeadDetail.objects.filter(
                        lead_id=lid, phone_opt_in=False
                    ).update(phone_opt_in=True)
                    if updated:
                        self.handle_phone_opt_in(lid)

                if e.get("user_type") == "CONSUMER":
                    pending = LeadPendingTask.objects.filter(
                        lead_id=lid, phone_opt_in=False, phone_available=False, active=True
                    ).exists()
                    if has_phone:
                        LeadDetail.objects.filter(lead_id=lid).update(phone_in_text=True)
                        if pending:
                            LeadDetail.objects.filter(lead_id=lid).update(phone_in_dialog=True)
                            reason = (
                                "Клієнт відповів із номером → переключено на сценарій phone available"
                            )
                            self.handle_phone_available(lid, reason=reason)
                        else:
                            self.handle_phone_available(lid)
                    elif pending and is_new:
                        reason = "Клієнт відповів, але номеру не знайдено"
                        self._cancel_no_phone_tasks(lid, reason=reason)

        return Response({"status": "received"}, status=status.HTTP_201_CREATED)

    def handle_new_lead(self, lead_id: str):
        logger.info(f"[AUTO-RESPONSE] Handling new lead: {lead_id}")
        self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)

    def handle_phone_opt_in(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] Handling phone opt-in for lead: {lead_id}")
        self._cancel_no_phone_tasks(lead_id, reason)
        self._process_auto_response(lead_id, phone_opt_in=True, phone_available=False)

    def handle_phone_available(self, lead_id: str, reason: str | None = None):
        logger.info(f"[AUTO-RESPONSE] Handling phone available for lead: {lead_id}")
        self._cancel_no_phone_tasks(lead_id, reason)
        self._process_auto_response(lead_id, phone_opt_in=False, phone_available=True)

    def _cancel_no_phone_tasks(self, lead_id: str, reason: str | None = None):
        pending = LeadPendingTask.objects.filter(
            lead_id=lead_id, phone_opt_in=False, phone_available=False, active=True
        )
        for p in pending:
            try:
                config.app.control.revoke(p.task_id)
            except Exception as exc:
                logger.error(
                    f"[AUTO-RESPONSE] Error revoking task {p.task_id}: {exc}"
                )
            p.active = False
            p.save(update_fields=["active"])
            CeleryTaskLog.objects.filter(task_id=p.task_id).update(
                status="REVOKED", result=reason
            )

    def _process_auto_response(self, lead_id: str, phone_opt_in: bool, phone_available: bool):
        default_settings = AutoResponseSettings.objects.filter(
            business__isnull=True,
            phone_opt_in=phone_opt_in,
            phone_available=phone_available,
        ).first()
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        biz_settings = None
        if pl:
            biz_settings = AutoResponseSettings.objects.filter(
                business__business_id=pl.business_id,
                phone_opt_in=phone_opt_in,
                phone_available=phone_available,
            ).first()
            try:
                token = get_valid_business_token(pl.business_id)
                logger.debug(
                    f"[AUTO-RESPONSE] Obtained business token for {pl.business_id}: {token}"
                )
            except ValueError:
                logger.error(
                    f"[AUTO-RESPONSE] No token for business {pl.business_id}; skipping"
                )
                return
        else:
            logger.error(
                "[AUTO-RESPONSE] Cannot determine business for lead=%s", lead_id
            )
            return

        auto_settings = biz_settings if biz_settings is not None else default_settings
        if auto_settings is None:
            logger.info("[AUTO-RESPONSE] AutoResponseSettings not configured")

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
        ev_resp = requests.get(f"{detail_url}/events", headers=headers, params={"limit": 1}, timeout=10)
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

        detail_data = {
            "lead_id": lead_id,
            "business_id": d.get("business_id"),
            "conversation_id": d.get("conversation_id"),
            "temporary_email_address": d.get("temporary_email_address"),
            "temporary_email_address_expiry": d.get("temporary_email_address_expiry"),
            "time_created": d.get("time_created"),
            "last_event_time": last_time,
            "user_display_name": d.get("user", {}).get("display_name", ""),
            "project": {
                "survey_answers": survey_list,
                "location": raw_proj.get("location", {}),
                "additional_info": raw_proj.get("additional_info", ""),
                "availability": raw_proj.get("availability", {}),
                "job_names": raw_proj.get("job_names", []),
                "attachments": raw_proj.get("attachments", []),
            },
        }

        ld, created = safe_update_or_create(LeadDetail, defaults=detail_data, lead_id=lead_id)
        logger.info(f"[AUTO-RESPONSE] LeadDetail {'created' if created else 'updated'} pk={ld.pk}")

        # If a phone number is present in additional_info when the lead detail is
        # fetched for the first time, treat it as a real phone provided by the
        # consumer and switch to the phone available flow.
        if (
            not phone_available
            and PHONE_RE.search(detail_data["project"].get("additional_info", ""))
        ):
            if not ld.phone_in_additional_info:
                ld.phone_in_additional_info = True
                ld.save(update_fields=["phone_in_additional_info"])
            logger.info("[AUTO-RESPONSE] Phone found in additional_info")
            self.handle_phone_available(
                lead_id, reason="phone number found in additional_info"
            )
            return

        if auto_settings and auto_settings.export_to_sheets:
            try:
                from .utils import append_lead_to_sheet
                append_lead_to_sheet(detail_data)
                logger.info(f"[AUTO-RESPONSE] Lead {lead_id} exported to Google Sheets")
            except Exception as e:
                logger.error(f"[AUTO-RESPONSE] Sheets export error: {e}")

        if not auto_settings or not auto_settings.enabled:
            logger.info("[AUTO-RESPONSE] Auto responses disabled; skipping messages")
            return

        name = ld.user_display_name if auto_settings.include_name else ""
        jobs = ", ".join(ld.project.get("job_names", [])) if auto_settings.include_jobs else ""
        sep = ", " if name and jobs else ""
        biz_id = ld.business_id if ld else None
        business = YelpBusiness.objects.filter(business_id=biz_id).first()

        greeting = auto_settings.greeting_template.format(name=name, jobs=jobs, sep=sep)
        off_greeting = auto_settings.greeting_off_hours_template.format(name=name, jobs=jobs, sep=sep)

        now = timezone.now()
        tz_name = business.time_zone if business else None
        within_hours = True
        if tz_name:
            tz = ZoneInfo(tz_name)
            local_now = now.astimezone(tz)
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
            within_hours = open_dt <= local_now < close_dt

        if within_hours:
            due = adjust_due_time(
                now + timedelta(seconds=auto_settings.greeting_delay),
                tz_name,
                auto_settings.greeting_open_from,
                auto_settings.greeting_open_to,
            )
            greet_text = greeting
        else:
            due = now + timedelta(seconds=auto_settings.greeting_delay)
            greet_text = off_greeting

        if _already_sent(lead_id, greet_text):
            logger.info("[AUTO-RESPONSE] Greeting already sent → skipping")
        elif due <= now:
            send_follow_up.apply_async(
                args=[lead_id, greet_text, token],
                headers={"business_id": biz_id},
                countdown=0,
            )
            logger.info("[AUTO-RESPONSE] Greeting dispatched immediately via Celery")
        else:
            countdown = (due - now).total_seconds()
            res = send_follow_up.apply_async(
                args=[lead_id, greet_text, token],
                headers={"business_id": biz_id},
                countdown=countdown,
            )
            LeadPendingTask.objects.create(
                lead_id=lead_id,
                task_id=res.id,
                phone_opt_in=phone_opt_in,
                phone_available=phone_available,
            )
            logger.info(
                f"[AUTO-RESPONSE] Greeting scheduled at {due.isoformat()}"
            )

        if phone_available:
            return

        now = timezone.now()
        if auto_settings.follow_up_template and auto_settings.follow_up_delay:
            built_in = auto_settings.follow_up_template.format(name=name, jobs=jobs, sep=sep)
            due2 = adjust_due_time(
                now + timedelta(seconds=auto_settings.follow_up_delay),
                business.time_zone if business else None,
                auto_settings.follow_up_open_from,
                auto_settings.follow_up_open_to,
            )
            countdown = max((due2 - now).total_seconds(), 0)
            if _already_sent(lead_id, built_in):
                logger.info("[AUTO-RESPONSE] Built-in follow-up already sent → skipping")
            else:
                res = send_follow_up.apply_async(
                    args=[lead_id, built_in, token],
                    headers={"business_id": biz_id},
                    countdown=countdown,
                )
                LeadPendingTask.objects.create(
                    lead_id=lead_id,
                    task_id=res.id,
                    phone_opt_in=phone_opt_in,
                    phone_available=phone_available,
                )
                logger.info(
                    f"[AUTO-RESPONSE] Built-in follow-up scheduled at {due2.isoformat()}"
                )

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
            if _already_sent(lead_id, text):
                logger.info(
                    f"[AUTO-RESPONSE] Custom follow-up '{tmpl.name}' already sent → skipping"
                )
            else:
                res = send_follow_up.apply_async(
                    args=[lead_id, text, token],
                    headers={"business_id": biz_id},
                    countdown=countdown,
                )
                LeadPendingTask.objects.create(
                    lead_id=lead_id,
                    task_id=res.id,
                    phone_opt_in=phone_opt_in,
                    phone_available=phone_available,
                )
                logger.info(
                    f"[AUTO-RESPONSE] Custom follow-up “{tmpl.name}” scheduled at {due.isoformat()}"
                )

        for sm in ScheduledMessage.objects.filter(lead_id=lead_id, active=True):
            delay = max((sm.next_run - now).total_seconds(), 0)
            res = send_scheduled_message.apply_async(
                args=[lead_id, sm.id],
                headers={"business_id": biz_id},
                countdown=delay,
            )
            LeadPendingTask.objects.create(
                lead_id=lead_id,
                task_id=res.id,
                phone_opt_in=phone_opt_in,
                phone_available=phone_available,
            )
            logger.info(f"[SCHEDULED] Message #{sm.id} scheduled in {delay:.0f}s")
            sm.schedule_next()
