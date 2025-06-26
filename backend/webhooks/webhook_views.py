import logging
import time
from datetime import timedelta
import requests
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
    YelpBusiness,
)
from .serializers import EventSerializer
from .utils import (
    get_valid_yelp_token,
    get_valid_business_token,
    get_token_for_lead,
    adjust_due_time,
)
from .tasks import send_follow_up
from .tasks import send_scheduled_message

logger = logging.getLogger(__name__)


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


class WebhookView(APIView):
    """Handle incoming webhook events from Yelp."""

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
                    upd["event_type"] = "NEW_LEAD"
                    logger.info(f"[WEBHOOK] Marked lead={lid} as NEW_LEAD")
        logger.info(f"[WEBHOOK] Lead IDs to process: {lead_ids}")

        for upd in updates:
            if upd.get("event_type") == "NEW_LEAD":
                lid = upd["lead_id"]
                if not ProcessedLead.objects.filter(lead_id=lid).exists():
                    pl = ProcessedLead.objects.create(
                        business_id=payload["data"]["id"],
                        lead_id=lid,
                    )
                    logger.info(f"[WEBHOOK] Created ProcessedLead id={pl.id} for lead={lid}")
                    self.handle_new_lead(lid)

        for lid in lead_ids:
            token = get_token_for_lead(lid)
            logger.info(f"[WEBHOOK] Using token for lead={lid} ending ...{token[-4:]}")
            url = f"https://api.yelp.com/v3/leads/{lid}/events"
            params = {"limit": 20}
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
            logger.info(f"[WEBHOOK] Yelp response status for lead={lid}: {resp.status_code}")

            if resp.status_code != 200:
                logger.error(f"[WEBHOOK] Failed to fetch events for lead={lid}: {resp.text}")
                continue

            events = resp.json().get("events", [])
            logger.info(f"[WEBHOOK] Received {len(events)} events for lead={lid}")

            for e in events:
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

        return Response({"status": "received"}, status=status.HTTP_201_CREATED)

    def handle_new_lead(self, lead_id: str):
        logger.info(f"[AUTO-RESPONSE] Handling new lead: {lead_id}")
        default_settings = AutoResponseSettings.objects.filter(id=1).first()
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        biz_settings = None
        if pl:
            biz_settings = AutoResponseSettings.objects.filter(business__business_id=pl.business_id).first()
            token = get_valid_business_token(pl.business_id)
        else:
            token = get_valid_yelp_token()

        if biz_settings is not None:
            if not biz_settings.enabled:
                logger.info("[AUTO-RESPONSE] Disabled for this business")
                return
            auto_settings = biz_settings
        else:
            if not (default_settings and default_settings.enabled):
                logger.info("[AUTO-RESPONSE] AutoResponseSettings not configured or disabled")
                return
            auto_settings = default_settings
        detail_url = f"https://api.yelp.com/v3/leads/{lead_id}"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(detail_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.error(f"[AUTO-RESPONSE] DETAIL ERROR lead={lead_id}, status={resp.status_code}")
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

        if auto_settings.export_to_sheets:
            try:
                from .utils import append_lead_to_sheet
                append_lead_to_sheet(detail_data)
                logger.info(f"[AUTO-RESPONSE] Lead {lead_id} exported to Google Sheets")
            except Exception as e:
                logger.error(f"[AUTO-RESPONSE] Sheets export error: {e}")

        name = ld.user_display_name if auto_settings.include_name else ""
        jobs = ", ".join(ld.project.get("job_names", [])) if auto_settings.include_jobs else ""
        sep = ", " if name and jobs else ""
        biz_id = ld.business_id if ld else None
        business = YelpBusiness.objects.filter(business_id=biz_id).first()

        greeting = auto_settings.greeting_template.format(name=name, jobs=jobs, sep=sep)

        now = timezone.now()
        due = adjust_due_time(
            now,
            business.time_zone if business else None,
            auto_settings.greeting_open_from,
            auto_settings.greeting_open_to,
        )

        if due <= now:
            resp = requests.post(
                f"{detail_url}/events",
                headers=headers,
                json={"request_content": greeting, "request_type": "TEXT"},
                timeout=10,
            )
            logger.info(f"[AUTO-RESPONSE] Greeting send status: {resp.status_code}")
        else:
            countdown = (due - now).total_seconds()
            send_follow_up.apply_async(
                args=[lead_id, greeting, token],
                headers={"business_id": biz_id},
                countdown=countdown,
            )
            logger.info(f"[AUTO-RESPONSE] Greeting scheduled at {due.isoformat()}")

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
            send_follow_up.apply_async(
                args=[lead_id, built_in, token],
                headers={"business_id": biz_id},
                countdown=countdown,
            )
            logger.info(
                f"[AUTO-RESPONSE] Built-in follow-up scheduled at {due2.isoformat()}"
            )

        tpls = FollowUpTemplate.objects.filter(active=True, business__business_id=biz_id)
        if not tpls.exists():
            tpls = FollowUpTemplate.objects.filter(active=True, business__isnull=True)
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
            send_follow_up.apply_async(
                args=[lead_id, text, token],
                headers={"business_id": biz_id},
                countdown=countdown,
            )
            logger.info(
                f"[AUTO-RESPONSE] Custom follow-up “{tmpl.name}” scheduled at {due.isoformat()}"
            )

        for sm in ScheduledMessage.objects.filter(lead_id=lead_id, active=True):
            delay = max((sm.next_run - now).total_seconds(), 0)
            send_scheduled_message.apply_async(
                args=[lead_id, sm.id],
                headers={"business_id": biz_id},
                countdown=delay,
            )
            logger.info(f"[SCHEDULED] Message #{sm.id} scheduled in {delay:.0f}s")
            sm.schedule_next()
