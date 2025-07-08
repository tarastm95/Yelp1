# utils.py
import requests
from datetime import timedelta, time, timezone as dt_timezone
from django.utils import timezone
from zoneinfo import ZoneInfo
from django.conf import settings
import logging
from .models import YelpToken, LeadDetail, ProcessedLead, YelpBusiness
from django.utils.dateparse import parse_datetime
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



def get_valid_business_token(business_id: str) -> str:
    """Return a fresh access_token for the given business_id."""
    logger.debug(f"[TOKEN] Fetching token for business={business_id}")
    try:
        yt = YelpToken.objects.get(business_id=business_id)
    except YelpToken.DoesNotExist:
        raise ValueError(f"No token for business {business_id}")

    if yt.expires_at and yt.expires_at <= timezone.now():
        logger.info(f"[TOKEN] Refreshing expired token for business={business_id}")
        data = rotate_refresh_token(yt.refresh_token)
        yt.access_token = data["access_token"]
        yt.refresh_token = data.get("refresh_token", yt.refresh_token)
        expires = data.get("expires_in")
        if expires:
            yt.expires_at = timezone.now() + timedelta(seconds=expires)
        yt.save()
    logger.debug(f"[TOKEN] Returning business token for {business_id}: {yt.access_token}")
    return yt.access_token


def get_token_for_lead(lead_id: str) -> str | None:
    """Return a fresh access token for the business owning the given lead.

    Returns ``None`` when the business is unknown or no token exists.
    """
    logger.debug(f"[TOKEN] Fetching token for lead={lead_id}")
    detail = LeadDetail.objects.filter(lead_id=lead_id).first()
    if detail:
        business_id = detail.business_id
        logger.debug(f"[TOKEN] Found business_id from LeadDetail: {business_id}")
    else:
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        if not pl:
            logger.error(f"[TOKEN] Business unknown for lead={lead_id}")
            return None
        business_id = pl.business_id
        logger.debug(f"[TOKEN] Found business_id from ProcessedLead: {business_id}")

    try:
        token = get_valid_business_token(business_id)
    except ValueError:
        logger.error(f"[TOKEN] No token for business {business_id}")
        return None
    logger.debug(f"[TOKEN] Returning token for lead={lead_id}: {token}")
    return token


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


def _format_time(dt_string: str, tz_name: str | None = None) -> str:
    """Return human readable time like 'May 18, 2025, 08:20:37'.

    If ``tz_name`` is provided, convert the datetime to that timezone before
    formatting.
    """
    if not dt_string:
        return ""
    dt = parse_datetime(dt_string)
    if not dt:
        return dt_string
    if tz_name:
        try:
            dt = dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
    return dt.strftime("%b %d, %Y, %H:%M:%S")


def _yelp_business_link(business_id: str) -> str:
    """Return clickable link to Yelp business page."""
    if not business_id:
        return ""
    url = f"https://biz.yelp.com/biz/{business_id}"
    return f'=HYPERLINK("{url}"; "{business_id}")'


def _yelp_lead_link(lead_id: str) -> str:
    """Return clickable link to Yelp lead page."""
    if not lead_id:
        return ""
    url = f"https://biz.yelp.com/leads/{lead_id}"
    return f'=HYPERLINK("{url}"; "{lead_id}")'


def _format_survey_answers(answers) -> str:
    """Format survey answers from JSON list to readable text."""
    if not answers:
        return ""
    lines = []
    for item in answers:
        q = item.get("question_text", "")
        ans = item.get("answer_text", [])
        if isinstance(ans, list):
            ans_text = " – ".join(ans)
        else:
            ans_text = str(ans)
        lines.append(f"• {q} – {ans_text}")
    return "\n".join(lines)


def _format_availability(av) -> str:
    if not av:
        return ""
    status = av.get("status", "")
    dates = av.get("dates", [])
    return f"{status} — {', '.join(dates)}" if dates else status


def _format_location(loc) -> str:
    if not loc:
        return ""
    return ", ".join(f"{k}: {v}" for k, v in loc.items())


def _format_attachments(atts) -> str:
    if not atts:
        return ""
    lines = []
    for att in atts:
        name = att.get("resource_name") or att.get("id")
        url = att.get("url", "")
        lines.append(f"• {name}: {url}")
    return "\n".join(lines)


def append_lead_to_sheet(detail_data: dict):
    """Append a new row to Google Sheets using detail_data.

    Logs the outcome and re-raises any exception so callers can handle it.
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

        # Формуємо рядок відповідно до нових стовпців
        proj = detail_data.get("project", {}) or {}

        biz_id = detail_data.get("business_id")
        lead_id = detail_data.get("lead_id")
        tz_name = None
        if biz_id:
            business = YelpBusiness.objects.filter(business_id=biz_id).first()
            tz_name = business.time_zone if business else None

        row = [
            _format_time(detail_data.get("time_created"), tz_name),
            biz_id or "",
            _yelp_business_link(biz_id),
            lead_id or "",
            _yelp_lead_link(lead_id),
            detail_data.get("user_display_name"),
            ", ".join(proj.get("job_names", [])),
            _format_survey_answers(proj.get("survey_answers", [])),
            _format_availability(proj.get("availability", {})),
            _format_location(proj.get("location", {})),
            detail_data.get("phone_number", ""),
            _format_attachments(proj.get("attachments", [])),
        ]

        # Use USER_ENTERED so formulas like HYPERLINK() are parsed correctly
        sheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(
            f"[SHEETS] Successfully appended lead {detail_data.get('lead_id')} "
            f"to spreadsheet {settings.GS_SPREADSHEET_ID}"
        )
    except Exception as e:
        logger.exception(
            f"[SHEETS] Failed to append lead {detail_data.get('lead_id')} "
            f"to spreadsheet {settings.GS_SPREADSHEET_ID}: {e}"
        )
        raise


def update_phone_in_sheet(lead_id: str, phone_number: str):
    """Update phone number for a lead in Google Sheets."""
    try:
        if getattr(settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None):
            creds = Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=settings.GS_SCOPES,
            )
        else:
            info = settings.GOOGLE_SERVICE_ACCOUNT_INFO.copy()
            pk = info.get("private_key")
            if isinstance(pk, (list, tuple)):
                pk = "\n".join(pk)
            elif isinstance(pk, bytes):
                pk = pk.decode("utf-8")
            if isinstance(pk, str):
                info["private_key"] = pk.replace("\\n", "\n")

            creds = Credentials.from_service_account_info(info, scopes=settings.GS_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.GS_SPREADSHEET_ID).sheet1
        cell = sheet.find(lead_id)
        if not cell:
            logger.warning(f"[SHEETS] Lead id {lead_id} not found for update")
            return
        row_idx = cell.row
        # Phone number column is 11th (1-indexed) after reordering
        phone_col = 11
        sheet.update_cell(row_idx, phone_col, phone_number)
        logger.info(
            f"[SHEETS] Updated phone for lead {lead_id} in spreadsheet {settings.GS_SPREADSHEET_ID}"
        )
    except Exception as e:
        logger.exception(
            f"[SHEETS] Failed to update phone for lead {lead_id} in spreadsheet {settings.GS_SPREADSHEET_ID}: {e}"
        )
