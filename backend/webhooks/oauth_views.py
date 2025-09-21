import uuid
import logging
import time
from datetime import timedelta
from urllib.parse import urlencode
from django.shortcuts import redirect
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from .models import (
    YelpOAuthState,
    YelpToken,
    YelpBusiness,
    ProcessedLead,
    LeadDetail,
    LeadEvent,
)
from .webhook_views import safe_update_or_create, _extract_phone

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

logger = logging.getLogger(__name__)


def fetch_and_store_lead(access_token: str, lead_id: str) -> None:
    """Fetch lead detail and latest events from Yelp and store them."""
    headers = {"Authorization": f"Bearer {access_token}"}
    detail_url = f"https://api.yelp.com/v3/leads/{lead_id}"
    try:
        d_resp = requests.get(detail_url, headers=headers, timeout=10)
        if d_resp.status_code != 200:
            logger.error(
                f"Failed to fetch lead detail for {lead_id}: status={d_resp.status_code}"
            )
            return
        detail = d_resp.json()

        ev_resp = requests.get(
            f"{detail_url}/events",
            headers=headers,
            params={"limit": 20},
            timeout=10,
        )
        events = ev_resp.json().get("events", []) if ev_resp.status_code == 200 else []
        last_time = events[0]["time_created"] if events else None

        raw_proj = detail.get("project", {}) or {}
        raw_answers = raw_proj.get("survey_answers", []) or []
        if isinstance(raw_answers, dict):
            survey_list = [
                {"question_text": q, "answer_text": a if isinstance(a, list) else [a]}
                for q, a in raw_answers.items()
            ]
        else:
            survey_list = raw_answers

        phone_number = _extract_phone(raw_proj.get("additional_info", "")) or ""

        detail_data = {
            "lead_id": lead_id,
            "business_id": detail.get("business_id"),
            "conversation_id": detail.get("conversation_id"),
            "temporary_email_address": detail.get("temporary_email_address"),
            "temporary_email_address_expiry": detail.get("temporary_email_address_expiry"),
            "time_created": detail.get("time_created"),
            "last_event_time": last_time,
            "user_display_name": detail.get("user", {}).get("display_name", ""),
            "phone_number": phone_number,
            "phone_opt_in": detail.get("phone_opt_in", False),
            "project": {
                "survey_answers": survey_list,
                "location": raw_proj.get("location", {}),
                "additional_info": raw_proj.get("additional_info", ""),
                "availability": raw_proj.get("availability", {}),
                "job_names": raw_proj.get("job_names", []),
                "attachments": raw_proj.get("attachments", []),
            },
        }

        safe_update_or_create(LeadDetail, defaults=detail_data, lead_id=lead_id)

        for e in events:
            defaults = {
                "lead_id": lead_id,
                "event_type": e.get("event_type"),
                "user_type": e.get("user_type"),
                "user_id": e.get("user_id"),
                "user_display_name": e.get("user_display_name", ""),
                "text": e.get("event_content", {}).get("fallback_text", ""),
                "cursor": e.get("cursor", ""),
                "time_created": e.get("time_created"),
                "raw": e,
            }
            phone = _extract_phone(defaults["text"])
            if phone:
                LeadDetail.objects.filter(lead_id=lead_id).update(phone_number=phone)
                try:
                    from .utils import update_phone_in_sheet
                    update_phone_in_sheet(lead_id, phone)
                except Exception:
                    logger.exception("[WEBHOOK] Failed to update phone in sheet")
            safe_update_or_create(LeadEvent, defaults=defaults, event_id=e.get("id"))
    except requests.RequestException as exc:
        logger.error(f"Failed to fetch lead data for {lead_id}: {exc}")



@csrf_exempt
def yelp_auth_callback_view(request):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "No code provided"}, status=400)

    token_url = settings.YELP_TOKEN_URL
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.YELP_CLIENT_ID,
        "client_secret": settings.YELP_CLIENT_SECRET,
        "redirect_uri": settings.YELP_OAUTH_REDIRECT_URI,
        "code": code,
    }
    resp = requests.post(token_url, data=data)
    if resp.status_code == 200:
        return JsonResponse(resp.json())
    return JsonResponse(
        {"error": "Failed to get token", "details": resp.text}, status=400
    )


@api_view(["POST"])
def save_yelp_state(request):
    state = request.data.get("state")
    if not state:
        return Response({"error": "No state provided"}, status=status.HTTP_400_BAD_REQUEST)
    expires_at = timezone.now() + timezone.timedelta(minutes=10)
    YelpOAuthState.objects.create(state=state, expires_at=expires_at)
    return Response({"status": "ok"})


class YelpAuthInitView(APIView):
    def get(self, request, *args, **kwargs):
        state = uuid.uuid4().hex
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        YelpOAuthState.objects.create(state=state, expires_at=expires_at)

        params = {
            "client_id": settings.YELP_CLIENT_ID,
            "response_type": "code",
            "state": state,
            "redirect_uri": settings.YELP_OAUTH_REDIRECT_URI,
            "scope": " ".join(settings.YELP_OAUTH_SCOPES),
        }
        auth_url = f"{settings.YELP_AUTHORIZATION_URL}?{urlencode(params)}"
        return Response({"authorization_url": auth_url})


class YelpAuthCallbackView(APIView):
    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")

        if error:
            return redirect(f"{settings.FRONTEND_URL}/callback?error={error}")
        if not code or not state:
            return redirect(f"{settings.FRONTEND_URL}/callback?error=missing_params")

        try:
            state_obj = YelpOAuthState.objects.get(
                state=state, is_used=False, expires_at__gt=timezone.now()
            )
        except YelpOAuthState.DoesNotExist:
            return redirect(f"{settings.FRONTEND_URL}/callback?error=invalid_state")

        state_obj.is_used = True
        state_obj.save()

        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.YELP_CLIENT_ID,
            "client_secret": settings.YELP_CLIENT_SECRET,
            "redirect_uri": settings.YELP_OAUTH_REDIRECT_URI,
            "code": code,
        }

        try:
            resp = requests.post(
                settings.YELP_TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                logger.error(f"Yelp token exchange failed: {resp.text}")
                return redirect(f"{settings.FRONTEND_URL}/callback?error=token_exchange_failed")

            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in")

            if not access_token:
                return redirect(f"{settings.FRONTEND_URL}/callback?error=token_error")


            biz_resp = requests.get(
                "https://partner-api.yelp.com/token/v1/businesses",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if biz_resp.status_code == 200:
                biz_ids = biz_resp.json().get("business_ids", [])
                for bid in biz_ids:
                    YelpToken.objects.update_or_create(
                        business_id=bid,
                        defaults={
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "expires_at": timezone.now() + timedelta(seconds=expires_in),
                        },
                    )
                    try:
                        det_resp = requests.get(
                            f"https://api.yelp.com/v3/businesses/{bid}",
                            headers={"Authorization": f"Bearer {settings.YELP_API_KEY}"},
                            timeout=10,
                        )
                        if det_resp.status_code == 200:
                            det = det_resp.json()
                            name = det.get("name", "")
                            loc = ", ".join(det.get("location", {}).get("display_address", []))
                            lat = det.get("coordinates", {}).get("latitude")
                            lng = det.get("coordinates", {}).get("longitude")
                            tz = ""
                            if lat is not None and lng is not None:
                                try:
                                    tz_resp = requests.get(
                                        "https://maps.googleapis.com/maps/api/timezone/json",
                                        params={
                                            "location": f"{lat},{lng}",
                                            "timestamp": int(time.time()),
                                            "key": settings.GOOGLE_TIMEZONE_API_KEY,
                                        },
                                        timeout=10,
                                    )
                                    if tz_resp.status_code == 200:
                                        tz = tz_resp.json().get("timeZoneId", "")
                                except requests.RequestException as e:
                                    logger.error(f"Failed to fetch timezone for {bid}: {e}")

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
                            YelpBusiness.objects.update_or_create(
                                business_id=bid,
                                defaults={
                                    "name": name,
                                    "location": loc,
                                    "time_zone": tz,
                                    "open_days": open_days,
                                    "open_hours": open_hours,
                                    "details": det,
                                },
                            )
                        try:
                            lid_resp = requests.get(
                                f"https://api.yelp.com/v3/businesses/{bid}/lead_ids",
                                headers={"Authorization": f"Bearer {access_token}"},
                                timeout=10,
                            )
                            if lid_resp.status_code == 200:
                                for lid in lid_resp.json().get("lead_ids", []):
                                    ProcessedLead.objects.get_or_create(
                                        business_id=bid, lead_id=lid
                                    )
                                    fetch_and_store_lead(access_token, lid)
                            else:
                                logger.error(
                                    f"Failed to fetch lead_ids for {bid}: status={lid_resp.status_code}"
                                )
                        except requests.RequestException as e:
                            logger.error(f"Failed to fetch lead_ids for {bid}: {e}")
                    except requests.RequestException as e:
                        logger.error(f"Failed to fetch business details for {bid}: {e}")

            return redirect(f"{settings.FRONTEND_URL}/callback?access_token={access_token}")
        except requests.RequestException as e:
            logger.error(f"OAuth request error: {e}")
            return redirect(f"{settings.FRONTEND_URL}/callback?error=token_request_failed")
