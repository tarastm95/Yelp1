# utils.py
import requests
from datetime import timedelta, time, timezone as dt_timezone
from django.utils import timezone
from zoneinfo import ZoneInfo
from django.conf import settings
import logging
from .models import AutoResponseSettings, YelpToken, LeadDetail, ProcessedLead
import gspread
from google.oauth2.service_account import Credentials
from django.conf import settings
import json

# Fallback UTC constant for older Django versions without timezone.utc
UTC = getattr(timezone, "utc", dt_timezone.utc)
logger = logging.getLogger(__name__)


def refresh_yelp_token(refresh_token: str) -> dict:
    """Request new tokens using refresh_token."""
    resp = requests.post(
        settings.YELP_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.YELP_CLIENT_ID,
            "client_secret": settings.YELP_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def rotate_refresh_token(refresh_token: str) -> dict:
    """Rotate refresh token via Yelp endpoint if configured."""
    if not getattr(settings, "YELP_ROTATE_URL", None):
        return refresh_yelp_token(refresh_token)
    resp = requests.post(
        settings.YELP_ROTATE_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.YELP_CLIENT_ID,
            "client_secret": settings.YELP_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

def get_valid_yelp_token():
    s, _ = AutoResponseSettings.objects.get_or_create(id=1)
    # якщо токен протух або не заданий
    if not s.access_token or (s.token_expires_at and s.token_expires_at <= timezone.now()):
        tok = rotate_refresh_token(s.refresh_token)
        s.access_token    = tok['access_token']
        s.refresh_token   = tok.get('refresh_token', s.refresh_token)
        s.token_expires_at = timezone.now() + timedelta(seconds=tok['expires_in'])
        s.save()
    return s.access_token


def get_valid_business_token(business_id: str) -> str:
    """Return a fresh access_token for the given business_id."""
    try:
        yt = YelpToken.objects.get(business_id=business_id)
    except YelpToken.DoesNotExist:
        raise ValueError(f"No token for business {business_id}")

    if yt.expires_at and yt.expires_at <= timezone.now():
        data = rotate_refresh_token(yt.refresh_token)
        yt.access_token = data["access_token"]
        yt.refresh_token = data.get("refresh_token", yt.refresh_token)
        expires = data.get("expires_in")
        if expires:
            yt.expires_at = timezone.now() + timedelta(seconds=expires)
        yt.save()

    return yt.access_token


def get_token_for_lead(lead_id: str) -> str:
    """Return a fresh access token for the business owning the given lead."""
    detail = LeadDetail.objects.filter(lead_id=lead_id).first()
    if detail:
        business_id = detail.business_id
    else:
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        if not pl:
            # fallback to global token if business unknown
            return get_valid_yelp_token()
        business_id = pl.business_id

    return get_valid_business_token(business_id)


def adjust_due_time(base_dt, tz_name: str | None, start: time, end: time):
    """Return UTC datetime within business hours."""
    if not tz_name:
        return base_dt
    tz = ZoneInfo(tz_name)
    local = base_dt.astimezone(tz)
    open_dt = local.replace(hour=start.hour, minute=start.minute, second=start.second, microsecond=0)
    close_dt = local.replace(hour=end.hour, minute=end.minute, second=end.second, microsecond=0)
    if close_dt <= open_dt:
        close_dt += timedelta(days=1)
    if local < open_dt:
        local = open_dt
    elif local >= close_dt:
        local = open_dt + timedelta(days=1)
    return local.astimezone(UTC)

GS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def append_lead_to_sheet(detail_data: dict):
    """
    Додає новий рядок до Google Sheets із полями detail_data.
    Використовує облікові дані із settings.GOOGLE_SERVICE_ACCOUNT_INFO.
    Логує успіх чи помилку.
    """
    try:
        if getattr(settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None):
            creds = Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=settings.GS_SCOPES,
            )
        else:
            # Підготуємо облікові дані як dict
            info = settings.GOOGLE_SERVICE_ACCOUNT_INFO.copy()
            # Приведемо private_key до єдиного рядка з реальними \n
            pk = info.get("private_key")
            if isinstance(pk, (list, tuple)):
                # Склеюємо кожен рядок із переносом
                pk = "\n".join(pk)
            elif isinstance(pk, bytes):
                pk = pk.decode("utf-8")
            # Тепер замінимо всі літеральні "\n" у середині на справжні переходи рядків
            if isinstance(pk, str):
                info["private_key"] = pk.replace("\\n", "\n")

            creds = Credentials.from_service_account_info(info, scopes=settings.GS_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.GS_SPREADSHEET_ID).sheet1

        # Формуємо рядок відповідно до ваших стовпців
        row = [
            detail_data.get("lead_id"),
            detail_data.get("business_id"),
            detail_data.get("conversation_id"),
            detail_data.get("temporary_email_address"),
            detail_data.get("temporary_email_address_expiry"),
            detail_data.get("time_created"),
            detail_data.get("last_event_time"),
            detail_data.get("user_display_name"),
            json.dumps(detail_data["project"].get("survey_answers", []), ensure_ascii=False),
            detail_data["project"].get("additional_info", ""),
            json.dumps(detail_data["project"].get("location", {}), ensure_ascii=False),
            json.dumps(detail_data["project"].get("availability", {}), ensure_ascii=False),
            ", ".join(detail_data["project"].get("job_names", [])),
            json.dumps(detail_data["project"].get("attachments", []), ensure_ascii=False),
        ]

        sheet.append_row(row)
        logger.info(
            f"[SHEETS] Successfully appended lead {detail_data.get('lead_id')} "
            f"to spreadsheet {settings.GS_SPREADSHEET_ID}"
        )
    except Exception as e:
        logger.error(
            f"[SHEETS] Failed to append lead {detail_data.get('lead_id')} "
            f"to spreadsheet {settings.GS_SPREADSHEET_ID}: {e}",
            exc_info=True
        )