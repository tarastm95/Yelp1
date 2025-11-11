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
    """Return UTC datetime within business hours and allowed days, preserving exact seconds."""
    if not tz_name:
        return base_dt
    
    # Special case: 24/7 working hours (00:00-00:00) - no adjustment needed
    if start == time(0, 0) and end == time(0, 0):
        return base_dt
        
    tz = ZoneInfo(tz_name)
    local = base_dt.astimezone(tz)
    allowed = _parse_days(days)
    
    # Preserve original seconds and microseconds from the scheduled time
    original_second = local.second
    original_microsecond = local.microsecond
    
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
            hour=start.hour, minute=start.minute, second=original_second, microsecond=original_microsecond
        )
    elif local >= close_dt:
        local += timedelta(days=1)
        while local.weekday() not in allowed:
            local += timedelta(days=1)
        local = local.replace(
            hour=start.hour, minute=start.minute, second=original_second, microsecond=original_microsecond
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
    
    This function uses database-level locking to prevent race conditions.
    """
    from django.db import transaction
    from .webhook_views import normalize_text
    
    # 🔧 FIX: Normalize text before checking duplicates (consistent with storage)
    normalized_text = normalize_text(text)
    logger.debug(f"[DUP CHECK] Text normalization for duplicate check:")
    logger.debug(f"[DUP CHECK] - Original: '{text[:100]}...'")
    logger.debug(f"[DUP CHECK] - Normalized: '{normalized_text[:100]}...'")
    logger.debug(f"[DUP CHECK] - Normalization changed text: {text != normalized_text}")
    
    with transaction.atomic():
        # Exact match check with select_for_update to prevent race conditions
        event_exists = LeadEvent.objects.filter(lead_id=lead_id, text=normalized_text).exists()

        # Use select_for_update to lock rows during duplicate check
        task_qs = LeadPendingTask.objects.select_for_update().filter(
            lead_id=lead_id,
            text=normalized_text,
            active=True,
        )
        logger.debug(f"[DUP CHECK] Before exclude: {task_qs.count()} tasks found")
        if exclude_task_id:
            logger.debug(f"[DUP CHECK] Excluding task_id: {exclude_task_id}")
            task_qs = task_qs.exclude(task_id=exclude_task_id)
            logger.debug(f"[DUP CHECK] After exclude: {task_qs.count()} tasks found")
        else:
            logger.debug(f"[DUP CHECK] No exclude_task_id provided")

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
            logger.info(f"[DUP CHECK] Original message: '{text[:100]}...'")
            logger.info(f"[DUP CHECK] Normalized message: '{normalized_text[:100]}...'")
            if text != normalized_text:
                logger.info(f"[DUP CHECK] 🔄 Text was normalized for duplicate detection")
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


def create_lead_pending_task_safe(lead_id: str, text: str, task_id: str, phone_available: bool) -> bool:
    """
    Safely create a LeadPendingTask with proper IntegrityError handling.
    
    Returns:
        bool: True if task was created successfully, False if duplicate exists
    """
    from django.db import IntegrityError, transaction
    from .models import LeadPendingTask
    from .webhook_views import normalize_text
    
    # 🔧 FIX: Normalize text before storing (consistent with other storage)
    normalized_text = normalize_text(text)
    logger.debug(f"[SAFE CREATE] Text normalization:")
    logger.debug(f"[SAFE CREATE] - Original: '{text[:50]}...'")
    logger.debug(f"[SAFE CREATE] - Normalized: '{normalized_text[:50]}...'")
    logger.debug(f"[SAFE CREATE] - Normalization changed text: {text != normalized_text}")
    
    try:
        with transaction.atomic():
            # Double-check for duplicates with locking
            existing = LeadPendingTask.objects.select_for_update().filter(
                lead_id=lead_id, 
                text=normalized_text, 
                active=True
            ).exists()
            
            if existing:
                logger.info(f"[SAFE CREATE] Task already exists for lead={lead_id}, text='{normalized_text[:50]}...'")
                return False
                
            LeadPendingTask.objects.create(
                lead_id=lead_id,
                text=normalized_text,
                task_id=task_id,
                phone_available=phone_available,
                active=True,
            )
            logger.info(f"[SAFE CREATE] ✅ Created LeadPendingTask for lead={lead_id}, task_id={task_id}")
            return True
            
    except IntegrityError as e:
        logger.info(f"[SAFE CREATE] ⚠️ IntegrityError handled for lead={lead_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"[SAFE CREATE] ❌ Unexpected error creating task for lead={lead_id}: {e}")
        logger.exception("Full exception details")
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
        
        morning_greeting = "Good morning"
        afternoon_greeting = "Good afternoon"
        evening_greeting = "Good evening"
        night_greeting = "Hello"
    else:
        morning_start = greeting_settings.morning_start
        morning_end = greeting_settings.morning_end
        afternoon_start = greeting_settings.afternoon_start
        afternoon_end = greeting_settings.afternoon_end
        evening_start = greeting_settings.evening_start
        evening_end = greeting_settings.evening_end
        
        morning_greeting = greeting_settings.morning_greeting
        afternoon_greeting = greeting_settings.afternoon_greeting
        evening_greeting = greeting_settings.evening_greeting
        night_greeting = greeting_settings.night_greeting
    
    current_time_only = current_time.time()
    
    # Determine greeting based on time - simple and clean
    if morning_start <= current_time_only < morning_end:
        return morning_greeting
    elif afternoon_start <= current_time_only < afternoon_end:
        return afternoon_greeting
    elif evening_start <= current_time_only < evening_end:
        return evening_greeting
    else:
        # Night (after evening_end or before morning_start)
        return night_greeting


# ===== DATABASE LOGGING SYSTEM =====

import logging
from django.utils import timezone

def log_lead_activity(
    lead_id: str,
    activity_type: str,
    event_name: str, 
    message: str,
    component: str = 'BACKEND',
    business_id: str = None,
    task_id: str = None,
    **metadata
):
    """
    Universal lead logging function that saves to both console and database.
    
    Args:
        lead_id: Lead identifier
        activity_type: WEBHOOK, PLANNING, EXECUTION, ANALYSIS, ERROR
        event_name: Function/event name (e.g., 'handle_new_lead', 'send_follow_up')
        message: Human-readable log message
        component: BACKEND, WORKER, SCHEDULER, API
        business_id: Optional business identifier
        task_id: Optional task identifier
        **metadata: Additional structured data
    
    Examples:
        log_lead_activity(
            lead_id="ABC123",
            activity_type="PLANNING",
            event_name="template_planning",
            message="Planning follow-up message #1",
            template_name="Custom 5",
            delay_seconds=15.0,
            countdown=15.0
        )
    """
    # Console logging (existing behavior)
    logger = logging.getLogger(f'lead.{lead_id}')
    logger.info(f"[{activity_type}] {message}")
    
    # Database logging (new persistent storage)
    try:
        from .models import LeadActivityLog
        
        LeadActivityLog.objects.create(
            lead_id=lead_id,
            activity_type=activity_type,
            component=component,
            event_name=event_name,
            message=message,
            business_id=business_id,
            task_id=task_id,
            metadata=metadata
        )
    except Exception as e:
        # Never let logging errors break the main flow
        logger.error(f"[DB-LOG] Failed to save lead activity log: {e}")


def get_lead_activity_summary(lead_id: str) -> dict:
    """Get activity summary for a lead"""
    try:
        from .models import LeadActivityLog
        from django.db.models import Count
        
        logs = LeadActivityLog.objects.filter(lead_id=lead_id)
        
        summary = logs.values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get first and last activities as serializable data
        first_activity = logs.order_by('timestamp').first()
        last_activity = logs.order_by('-timestamp').first()
        
        return {
            'total_logs': logs.count(),
            'first_activity': {
                'timestamp': first_activity.timestamp,
                'activity_type': first_activity.activity_type,
                'message': first_activity.message,
            } if first_activity else None,
            'last_activity': {
                'timestamp': last_activity.timestamp,
                'activity_type': last_activity.activity_type,
                'message': last_activity.message,
            } if last_activity else None,
            'by_type': {item['activity_type']: item['count'] for item in summary}
        }
    except Exception as e:
        logger.error(f"[DB-LOG] Failed to get lead summary: {e}")
        return {'error': str(e)}


def cleanup_old_lead_logs(days: int = 30):
    """Clean up lead activity logs older than specified days"""
    try:
        from .models import LeadActivityLog
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(days=days)
        deleted_count, _ = LeadActivityLog.objects.filter(timestamp__lt=cutoff).delete()
        
        logger.info(f"[DB-LOG] Cleaned up {deleted_count} old lead activity logs (older than {days} days)")
        return deleted_count
    except Exception as e:
        logger.error(f"[DB-LOG] Failed to cleanup old logs: {e}")
        return 0


# ===== ERROR TRACKING SYSTEM =====

import uuid
import traceback
import inspect

def log_system_error(
    error_type: str,
    error_message: str,
    exception: Exception = None,
    severity: str = 'MEDIUM',
    lead_id: str = None,
    business_id: str = None,
    task_id: str = None,
    **metadata
):
    """
    Universal error logging function for system-wide error tracking.
    
    Args:
        error_type: API_ERROR, DJANGO_ERROR, TASK_ERROR, etc.
        error_message: Human-readable error description
        exception: Python exception object (if available)
        severity: LOW, MEDIUM, HIGH, CRITICAL
        lead_id: Associated lead (if applicable)
        business_id: Associated business (if applicable)
        task_id: Associated task (if applicable)
        **metadata: Additional context data
    """
    try:
        from .models import SystemErrorLog
        
        # Generate unique error ID
        error_id = str(uuid.uuid4())[:8]
        
        # Extract caller information
        frame = inspect.currentframe().f_back
        component = frame.f_globals.get('__name__', 'unknown')
        function_name = frame.f_code.co_name
        line_number = frame.f_lineno
        
        # Extract exception details
        exception_type = ""
        tb = ""
        if exception:
            exception_type = exception.__class__.__name__
            tb = traceback.format_exc()
        
        # Console logging
        logger = logging.getLogger('system.errors')
        logger.error(f"[{error_type}] {error_message}")
        if exception:
            logger.exception(f"[{error_type}] Exception details")
        
        # Database logging
        SystemErrorLog.objects.create(
            error_id=error_id,
            error_type=error_type,
            severity=severity,
            component=component,
            function_name=function_name,
            line_number=line_number,
            error_message=error_message,
            exception_type=exception_type,
            traceback=tb,
            lead_id=lead_id,
            business_id=business_id,
            task_id=task_id,
            metadata=metadata
        )
        
        return error_id
        
    except Exception as e:
        # Never let error logging break the main flow
        logger.error(f"[ERROR-LOG] Failed to log error: {e}")
        return None


def log_performance_metric(
    metric_type: str,
    value: float,
    unit: str = 'count',
    component: str = '',
    business_id: str = None,
    **metadata
):
    """Log performance metrics for system monitoring"""
    try:
        from .models import SystemHealthMetric
        
        SystemHealthMetric.objects.create(
            metric_type=metric_type,
            value=value,
            unit=unit,
            component=component,
            business_id=business_id,
            metadata=metadata
        )
        
        # Console logging for critical metrics
        if metric_type in ['QUEUE_LENGTH', 'API_RESPONSE_TIME'] and value > 100:
            logger.warning(f"[PERFORMANCE] High {metric_type}: {value}{unit}")
            
    except Exception as e:
        logger.error(f"[METRIC-LOG] Failed to log metric: {e}")


def get_system_health_summary() -> dict:
    """Get current system health status"""
    try:
        from .models import SystemErrorLog, SystemHealthMetric, CeleryTaskLog
        from django.db.models import Count, Q
        from datetime import timedelta
        
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # Error statistics
        recent_errors = SystemErrorLog.objects.filter(timestamp__gte=last_hour)
        critical_errors = recent_errors.filter(severity='CRITICAL').count()
        high_errors = recent_errors.filter(severity='HIGH').count()
        unresolved_errors = SystemErrorLog.objects.filter(resolved=False).count()
        
        # Task statistics
        recent_tasks = CeleryTaskLog.objects.filter(finished_at__gte=last_hour)
        total_tasks = recent_tasks.count()
        failed_tasks = recent_tasks.filter(status='FAILURE').count()
        success_rate = ((total_tasks - failed_tasks) / total_tasks * 100) if total_tasks > 0 else 100
        
        # Performance metrics
        latest_metrics = {}
        for metric_type in ['API_RESPONSE_TIME', 'QUEUE_LENGTH', 'MEMORY_USAGE']:
            latest = SystemHealthMetric.objects.filter(
                metric_type=metric_type
            ).order_by('-timestamp').first()
            if latest:
                latest_metrics[metric_type] = {
                    'value': latest.value,
                    'unit': latest.unit,
                    'timestamp': latest.timestamp
                }
        
        # Overall health score (0-100)
        health_score = 100
        if critical_errors > 0:
            health_score -= 50
        if high_errors > 0:
            health_score -= min(high_errors * 10, 30)
        if success_rate < 95:
            health_score -= (95 - success_rate)
        if unresolved_errors > 5:
            health_score -= min(unresolved_errors * 2, 20)
            
        health_score = max(0, health_score)
        
        return {
            'health_score': health_score,
            'status': 'HEALTHY' if health_score > 80 else 'WARNING' if health_score > 60 else 'CRITICAL',
            'errors': {
                'critical_last_hour': critical_errors,
                'high_last_hour': high_errors,
                'total_unresolved': unresolved_errors
            },
            'tasks': {
                'total_last_hour': total_tasks,
                'failed_last_hour': failed_tasks,
                'success_rate': round(success_rate, 1)
            },
            'metrics': latest_metrics,
            'last_updated': now
        }
        
    except Exception as e:
        logger.error(f"[HEALTH] Failed to get system health: {e}")
        return {
            'health_score': 0,
            'status': 'ERROR',
            'error': str(e)
        }


def schedule_follow_ups_after_greeting(lead_id: str, business_id: str):
    """
    🎯 CRITICAL: Schedule follow-ups AFTER greeting completes.
    This is called from send_follow_up task when sequence_number == 0.
    """
    from .models import FollowUpTemplate, AutoResponseSettings
    from .tasks import generate_and_send_follow_up
    from django_rq import get_queue
    
    logger.info(f"[FOLLOW-UP-SCHEDULE] 🎯 SCHEDULING FOLLOW-UPS AFTER GREETING")
    logger.info(f"[FOLLOW-UP-SCHEDULE] ========================================")
    logger.info(f"[FOLLOW-UP-SCHEDULE] Lead ID: {lead_id}")
    logger.info(f"[FOLLOW-UP-SCHEDULE] Business ID: {business_id}")
    logger.info(f"[FOLLOW-UP-SCHEDULE] Trigger: Greeting just completed")
    logger.info(f"[FOLLOW-UP-SCHEDULE] Base time: NOW (greeting completion time)")
    
    now = timezone.now()
    
    try:
        # Get lead details
        lead_detail = LeadDetail.objects.get(lead_id=lead_id)
        name = lead_detail.user_display_name or "there"
        jobs = ", ".join(lead_detail.project.get("job_names", []))
        phone_available = lead_detail.phone_opt_in
        
        # Get templates
        tpls = FollowUpTemplate.objects.filter(
            active=True,
            phone_available=phone_available,
            business__business_id=business_id,
        ).order_by('delay')
        
        if not tpls.exists():
            tpls = FollowUpTemplate.objects.filter(
                active=True,
                phone_available=phone_available,
                business__isnull=True,
            ).order_by('delay')
        
        if not tpls.exists():
            logger.info(f"[FOLLOW-UP-SCHEDULE] No follow-up templates found")
            return
        
        business = YelpBusiness.objects.filter(business_id=business_id).first()
        
        logger.info(f"[FOLLOW-UP-SCHEDULE] Found {tpls.count()} templates to schedule")
        logger.info(f"[FOLLOW-UP-SCHEDULE] Customer: {name}")
        logger.info(f"[FOLLOW-UP-SCHEDULE] Jobs: {jobs}")
        
        # Find greeting task to link follow-ups
        greeting_task = LeadPendingTask.objects.filter(
            lead_id=lead_id,
            sequence_number=0,
            active=True
        ).first()
        
        previous_task_id = greeting_task.task_id if greeting_task else None
        current_sequence = 1  # Follow-ups start from 1
        
        # Determine AI mode
        ai_mode = 'TEMPLATE'
        try:
            ai_settings = AutoResponseSettings.objects.filter(
                business__business_id=business_id,
                phone_available=phone_available
            ).first()
            
            if ai_settings:
                if ai_settings.use_sample_replies and ai_settings.mode == 'ai_generated':
                    ai_mode = 'AI_VECTOR'
                elif ai_settings.mode == 'ai_generated':
                    ai_mode = 'AI_FULL'
        except Exception as e:
            logger.warning(f"[FOLLOW-UP-SCHEDULE] Could not determine AI mode: {e}")
        
        # Schedule each template
        queue = get_queue('default')
        
        for tmpl in tpls:
            delay = tmpl.delay.total_seconds()
            
            logger.info(f"[FOLLOW-UP-SCHEDULE] 📋 Template: {tmpl.name}")
            logger.info(f"[FOLLOW-UP-SCHEDULE] - Delay: {delay}s from NOW")
            logger.info(f"[FOLLOW-UP-SCHEDULE] - Sequence: #{current_sequence}")
            logger.info(f"[FOLLOW-UP-SCHEDULE] - AI mode: {ai_mode}")
            
            # Calculate due time from NOW (greeting completion)
            initial_due = now + timedelta(seconds=delay)
            
            due = adjust_due_time(
                initial_due,
                business.time_zone if business else None,
                tmpl.open_from,
                tmpl.open_to,
            )
            
            countdown = max((due - now).total_seconds(), 0)
            
            logger.info(f"[FOLLOW-UP-SCHEDULE] - Due time: {due.isoformat()}")
            logger.info(f"[FOLLOW-UP-SCHEDULE] - Countdown: {countdown}s")
            
            # Check if already scheduled
            existing_task = LeadPendingTask.objects.filter(
                lead_id=lead_id,
                sequence_number=current_sequence,
                active=True
            ).exists()
            
            if existing_task:
                logger.info(f"[FOLLOW-UP-SCHEDULE] ⚠️ Sequence #{current_sequence} already exists - skipping")
                current_sequence += 1
                continue
            
            # Schedule task
            res = queue.enqueue_in(
                timedelta(seconds=countdown),
                generate_and_send_follow_up,
                lead_id,
                tmpl.id,
                business_id,
                ai_mode,
            )
            
            logger.info(f"[FOLLOW-UP-SCHEDULE] ✅ Task scheduled: {res.id}")
            
            # Create CeleryTaskLog
            CeleryTaskLog.objects.update_or_create(
                task_id=res.id,
                defaults={
                    'name': 'generate_and_send_follow_up',
                    'args': [lead_id, tmpl.id, business_id, ai_mode],
                    'kwargs': {},
                    'eta': due,
                    'status': 'SCHEDULED',
                    'business_id': business_id,
                }
            )
            
            # Generate message text immediately for display in UI
            # This pre-generates the text so it shows in Scheduled tab
            try:
                # Get time-based greeting
                greetings = get_time_based_greeting(business_id) if business_id else "Hello"
                reason = ""
                sep = "\n"
                
                # Generate text based on template
                text = tmpl.template.format(
                    name=name,
                    jobs=jobs,
                    sep=sep,
                    reason=reason,
                    greetings=greetings
                )
                
                logger.info(f"[FOLLOW-UP-SCHEDULE] 📝 Generated text preview: {text[:50]}...")
            except Exception as gen_err:
                logger.warning(f"[FOLLOW-UP-SCHEDULE] Failed to generate text: {gen_err}")
                text = f"[Template: {tmpl.name}] {tmpl.template[:100]}"
            
            # Create LeadPendingTask
            try:
                task_record = LeadPendingTask.objects.create(
                    lead_id=lead_id,
                    task_id=res.id,
                    text=text,  # Pre-generated text for UI display
                    template_id=tmpl.id,
                    ai_mode=ai_mode,
                    phone_available=phone_available,
                    sequence_number=current_sequence,
                    previous_task_id=previous_task_id,
                    status='PENDING'
                )
                logger.info(f"[FOLLOW-UP-SCHEDULE] ✅ LeadPendingTask created: {task_record.pk}")
                
                # Update for next iteration
                previous_task_id = res.id
                current_sequence += 1
                
            except Exception as e:
                logger.error(f"[FOLLOW-UP-SCHEDULE] ❌ Failed to create LeadPendingTask: {e}")
        
        logger.info(f"[FOLLOW-UP-SCHEDULE] ✅ COMPLETED - {tpls.count()} follow-ups scheduled")
        
    except Exception as e:
        logger.error(f"[FOLLOW-UP-SCHEDULE] ❌ Error scheduling follow-ups: {e}")
        logger.exception(e)

