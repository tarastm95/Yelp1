# utils.py
import requests
from datetime import timedelta, time, timezone as dt_timezone
from django.utils import timezone
from zoneinfo import ZoneInfo
from django.conf import settings
import logging
from .models import (
    YelpToken,
    LeadDetail,
    ProcessedLead,
    YelpBusiness,
    LeadEvent,
    CeleryTaskLog,
    LeadPendingTask,
)
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
    logger.debug("[TOKEN] Requesting new tokens via refresh_yelp_token")
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
    logger.debug(
        f"[TOKEN] refresh_yelp_token response {resp.status_code}: {resp.text}"
    )
    resp.raise_for_status()
    return resp.json()


def rotate_refresh_token(refresh_token: str) -> dict:
    """Rotate refresh token via Yelp endpoint if configured."""
    if not getattr(settings, "YELP_ROTATE_URL", None):
        return refresh_yelp_token(refresh_token)
    logger.debug("[TOKEN] Rotating refresh token via Yelp endpoint")
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
    logger.debug(
        f"[TOKEN] rotate_refresh_token response {resp.status_code}: {resp.text}"
    )
    resp.raise_for_status()
    return resp.json()


def update_shared_refresh_token(old_refresh: str, new_data: dict):
    """Apply new access/refresh token to every YelpToken using old_refresh."""
    tokens = YelpToken.objects.filter(refresh_token=old_refresh)
    if not tokens:
        return
    expires = new_data.get("expires_in")
    update_data = {
        "access_token": new_data["access_token"],
        "refresh_token": new_data.get("refresh_token", old_refresh),
    }
    if expires:
        update_data["expires_at"] = timezone.now() + timedelta(seconds=expires)
    tokens.update(**update_data)


def get_valid_business_token(business_id: str) -> str:
    """Return a fresh access_token for the given business_id."""
    logger.debug(f"[TOKEN] Fetching token for business={business_id}")
    try:
        yt = YelpToken.objects.get(business_id=business_id)
    except YelpToken.DoesNotExist:
        raise ValueError(f"No token for business {business_id}")

    if yt.expires_at and yt.expires_at <= timezone.now():
        logger.info(f"[TOKEN] Refreshing expired token for business={business_id}")
        old_refresh = yt.refresh_token
        data = rotate_refresh_token(old_refresh)
        update_shared_refresh_token(old_refresh, data)
        yt.access_token = data["access_token"]
        yt.refresh_token = data.get("refresh_token", yt.refresh_token)
        expires = data.get("expires_in")
        if expires:
            yt.expires_at = timezone.now() + timedelta(seconds=expires)
        yt.save()
    logger.debug(
        f"[TOKEN] Returning business token for {business_id}: {yt.access_token}"
    )
    return yt.access_token


def get_token_for_lead(lead_id: str) -> str | None:
    """Return a fresh access token for the business owning the given lead.

    Returns ``None`` when the business is unknown or no token exists.
    """
    logger.debug(f"[TOKEN] Fetching token for lead={lead_id}")
    detail = LeadDetail.objects.filter(lead_id=lead_id).first()
    if detail:
        business_id = detail.business_id
        logger.debug(
            f"[TOKEN] Found business_id from LeadDetail: {business_id}"
        )
    else:
        pl = ProcessedLead.objects.filter(lead_id=lead_id).first()
        if not pl:
            logger.error(f"[TOKEN] Business unknown for lead={lead_id}")
            return None
        business_id = pl.business_id
        logger.debug(
            f"[TOKEN] Found business_id from ProcessedLead: {business_id}"
        )

    logger.info(
        f"[TOKEN] lead={lead_id} belongs to business={business_id}"
    )

    try:
        token = get_valid_business_token(business_id)
    except ValueError:
        logger.error(f"[TOKEN] No token for business {business_id}")
        return None
    logger.debug(f"[TOKEN] Returning token for lead={lead_id}: {token}")
    return token


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _parse_days(day_str: str | None) -> set[int]:
    days = set()
    if not day_str:
        return set(range(7))
    for part in day_str.split(","):
        name = part.strip()
        if name in DAY_NAMES:
            days.add(DAY_NAMES.index(name))
    return days if days else set(range(7))


def adjust_due_time(base_dt, tz_name: str | None, start: time, end: time, days: str | None = None):
    """Return UTC datetime within business hours and allowed days."""
    if not tz_name:
        return base_dt
    tz = ZoneInfo(tz_name)
    local = base_dt.astimezone(tz)
    allowed = _parse_days(days)
    open_dt = local.replace(
        hour=start.hour, minute=start.minute, second=start.second, microsecond=0
    )
    close_dt = local.replace(
        hour=end.hour, minute=end.minute, second=end.second, microsecond=0
    )
    if close_dt <= open_dt:
        close_dt += timedelta(days=1)
    if local.weekday() not in allowed or local < open_dt:
        while local.weekday() not in allowed:
            local += timedelta(days=1)
        local = local.replace(
            hour=start.hour, minute=start.minute, second=start.second, microsecond=0
        )
    elif local >= close_dt:
        local += timedelta(days=1)
        while local.weekday() not in allowed:
            local += timedelta(days=1)
        local = local.replace(
            hour=start.hour, minute=start.minute, second=start.second, microsecond=0
        )
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
    # 🔧 FIX: Визначаємо lead_id та biz_id на початку функції щоб уникнути UnboundLocalError
    biz_id = detail_data.get("business_id", "Unknown")
    lead_id = detail_data.get("lead_id", "Unknown")
    
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

            creds = Credentials.from_service_account_info(
                info, scopes=settings.GS_SCOPES
            )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.GS_SPREADSHEET_ID).sheet1

        # Формуємо рядок відповідно до нових стовпців
        proj = detail_data.get("project", {}) or {}

        logger.info(
            "[SHEETS] Appending lead %s for business %s to spreadsheet %s",
            lead_id,
            biz_id,
            settings.GS_SPREADSHEET_ID,
        )
        tz_name = None
        if biz_id and biz_id != "Unknown":
            business = YelpBusiness.objects.filter(business_id=biz_id).first()
            tz_name = business.time_zone if business else None

        # The export to Google Sheets omits the business and lead hyperlinks.
        # Columns now contain only plain identifiers and lead details.
        row = [
            _format_time(detail_data.get("time_created"), tz_name),  # created at
            biz_id or "",
            lead_id or "",
            detail_data.get("user_display_name"),
            ", ".join(proj.get("job_names", [])),
            _format_survey_answers(proj.get("survey_answers", [])),
            _format_availability(proj.get("availability", {})),
            _format_location(proj.get("location", {})),
            detail_data.get("phone_number", ""),
            _format_attachments(proj.get("attachments", [])),
            detail_data.get("phone_opt_in", False),
        ]

        # Use USER_ENTERED so formulas like HYPERLINK() are parsed correctly
        sheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(
            "[SHEETS] Successfully appended lead %s for business %s to spreadsheet %s",
            lead_id,
            biz_id,
            settings.GS_SPREADSHEET_ID,
        )
    except Exception as e:
        # 🔧 FIX: Безпечна обробка exception без UnboundLocalError
        try:
            logger.exception(
                "[SHEETS] Failed to append lead %s for business %s to spreadsheet %s: %s",
                lead_id,
                biz_id,
                settings.GS_SPREADSHEET_ID,
                e,
            )
        except NameError:
            # Якщо змінні все ще не визначені (дуже рідкісний випадок)
            logger.exception(
                "[SHEETS] Failed to append lead to spreadsheet %s: %s",
                getattr(settings, 'GS_SPREADSHEET_ID', 'Unknown'),
                e,
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

            creds = Credentials.from_service_account_info(
                info, scopes=settings.GS_SCOPES
            )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.GS_SPREADSHEET_ID).sheet1
        cell = sheet.find(lead_id)
        if not cell:
            logger.warning(f"[SHEETS] Lead id {lead_id} not found for update")
            return
        row_idx = cell.row
        # Phone number column is now 9th (1-indexed) after removing hyperlinks
        phone_col = 9
        sheet.update_cell(row_idx, phone_col, phone_number)
        logger.info(
            f"[SHEETS] Updated phone for lead {lead_id} in spreadsheet {settings.GS_SPREADSHEET_ID}"
        )
    except Exception as e:
        logger.exception(
            f"[SHEETS] Failed to update phone for lead {lead_id} in spreadsheet {settings.GS_SPREADSHEET_ID}: {e}"
        )


def _already_sent(lead_id: str, text: str, exclude_task_id: str | None = None) -> bool:
    """Return ``True`` if this lead already received exactly the given text.

    ``exclude_task_id`` allows ignoring the pending task entry for the current
    job when checking duplicates.
    """
    # Exact match check
    event_exists = LeadEvent.objects.filter(lead_id=lead_id, text=text).exists()

    task_qs = LeadPendingTask.objects.filter(
        lead_id=lead_id,
        text=text,
        active=True,
    )
    if exclude_task_id:
        task_qs = task_qs.exclude(task_id=exclude_task_id)

    task_exists = task_qs.exists()
    
    # Enhanced logging for duplicate detection
    if event_exists or task_exists:
        logger.debug(
            "[DUP CHECK] Follow-up for lead=%s already sent or queued: events=%s tasks=%s",
            lead_id,
            event_exists,
            list(task_qs.values_list("task_id", "active"))[:5],
        )
        logger.info(f"[DUP CHECK] ✅ EXACT DUPLICATE found for lead={lead_id}")
        logger.info(f"[DUP CHECK] Message: '{text[:100]}...'")
        return True
    else:
        logger.debug("[DUP CHECK] No prior follow-up found for lead=%s", lead_id)
        
        # 🔍 Enhanced duplicate detection for similar content
        # Check for messages with similar patterns but different job specifications
        similar_patterns = [
            # Common template variations that might be duplicates
            "about your project",
            "about your Remodeling project", 
            "about your remodeling project",
            "regarding your project",
            "regarding your Remodeling project"
        ]
        
        existing_events = LeadEvent.objects.filter(lead_id=lead_id, user_type="BUSINESS")
        for event in existing_events:
            event_text = event.text.lower()
            current_text = text.lower()
            
            # Check if both texts contain similar greeting patterns
            for pattern in similar_patterns:
                if pattern in event_text and any(p in current_text for p in similar_patterns):
                    # Calculate simple similarity
                    if _texts_are_similar(event.text, text):
                        logger.warning(f"[DUP CHECK] ⚠️ SIMILAR MESSAGE detected for lead={lead_id}")
                        logger.warning(f"[DUP CHECK] Existing: '{event.text[:100]}...'")
                        logger.warning(f"[DUP CHECK] Current:  '{text[:100]}...'")
                        logger.warning(f"[DUP CHECK] This might be a job_names variation duplicate")
                        # Note: Return False for now, but log for analysis
                        break
        
        return False


def _texts_are_similar(text1: str, text2: str, similarity_threshold: float = 0.8) -> bool:
    """Check if two texts are similar enough to be considered potential duplicates."""
    import difflib
    
    # Normalize texts
    t1 = text1.lower().strip()
    t2 = text2.lower().strip()
    
    # Calculate similarity ratio
    ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
    
    return ratio >= similarity_threshold


def get_time_based_greeting(business_id: str = None, current_time=None):
    """
    Get time-based greeting for a business or global default
    
    Args:
        business_id: Business ID for business-specific greetings
        current_time: datetime object (defaults to now in business timezone)
    
    Returns:
        str: Appropriate greeting based on time of day
    """
    from datetime import datetime, time
    from django.utils import timezone
    from .models import TimeBasedGreeting, YelpBusiness
    
    if current_time is None:
        current_time = timezone.now()
    
    # Get greeting settings
    greeting_settings = None
    
    if business_id:
        try:
            business = YelpBusiness.objects.get(business_id=business_id)
            greeting_settings = TimeBasedGreeting.objects.filter(business=business).first()
            
            # Convert to business timezone if available
            if business.time_zone:
                import pytz
                try:
                    business_tz = pytz.timezone(business.time_zone)
                    current_time = current_time.astimezone(business_tz)
                except:
                    pass  # Use UTC if timezone conversion fails
        except YelpBusiness.DoesNotExist:
            pass
    
    # Fall back to global default if no business-specific settings
    if not greeting_settings:
        greeting_settings = TimeBasedGreeting.objects.filter(business__isnull=True).first()
    
    # Use default values if no settings found
    if not greeting_settings:
        morning_start = time(5, 0)
        morning_end = time(12, 0)
        afternoon_start = time(12, 0) 
        afternoon_end = time(17, 0)
        evening_start = time(17, 0)
        evening_end = time(21, 0)
        
        morning_formal = "Good morning"
        morning_casual = "Morning!"
        afternoon_formal = "Good afternoon"
        afternoon_casual = "Hi"
        evening_formal = "Good evening"
        evening_casual = "Evening!"
        night_greeting = "Hello"
        default_style = "formal"
    else:
        morning_start = greeting_settings.morning_start
        morning_end = greeting_settings.morning_end
        afternoon_start = greeting_settings.afternoon_start
        afternoon_end = greeting_settings.afternoon_end
        evening_start = greeting_settings.evening_start
        evening_end = greeting_settings.evening_end
        
        morning_formal = greeting_settings.morning_formal
        morning_casual = greeting_settings.morning_casual
        afternoon_formal = greeting_settings.afternoon_formal
        afternoon_casual = greeting_settings.afternoon_casual
        evening_formal = greeting_settings.evening_formal
        evening_casual = greeting_settings.evening_casual
        night_greeting = greeting_settings.night_greeting
        default_style = greeting_settings.default_style
    
    current_time_only = current_time.time()
    
    # Determine greeting based on time
    if morning_start <= current_time_only < morning_end:
        # Morning
        if default_style == 'casual':
            return morning_casual
        elif default_style == 'mixed':
            # Use formal for early morning, casual later
            return morning_formal if current_time_only < time(9, 0) else morning_casual
        else:  # formal
            return morning_formal
    
    elif afternoon_start <= current_time_only < afternoon_end:
        # Afternoon
        if default_style == 'casual':
            return afternoon_casual
        elif default_style == 'mixed':
            return afternoon_casual  # Afternoon is usually less formal
        else:  # formal
            return afternoon_formal
    
    elif evening_start <= current_time_only < evening_end:
        # Evening
        if default_style == 'casual':
            return evening_casual
        elif default_style == 'mixed':
            return evening_casual  # Evening is usually casual
        else:  # formal
            return evening_formal
    
    else:
        # Night (after evening_end or before morning_start)
        return night_greeting

