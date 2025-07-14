# webhooks/tasks.py

import logging
import requests
from requests import HTTPError
from celery import shared_task
from django.utils import timezone

from .models import (
    ScheduledMessage,
    ScheduledMessageHistory,
    LeadDetail,
    LeadScheduledMessageHistory,
    LeadScheduledMessage,
    YelpToken,
    CeleryTaskLog,
)
from django.db import transaction
from .utils import (
    get_token_for_lead,
    get_valid_business_token,
    rotate_refresh_token,
    update_shared_refresh_token,
)

logger = logging.getLogger(__name__)


def _extract_yelp_error(resp: requests.Response) -> str:
    """Return readable error text from a Yelp API response."""
    try:
        data = resp.json()
        return (
            data.get("error_description")
            or data.get("description")
            or resp.text
        )
    except Exception:
        return resp.text


def _scheduled_message_pending(lead_id: str, sched_id: int) -> bool:
    """Return True if a ScheduledMessage task is already queued."""
    qs = CeleryTaskLog.objects.filter(
        name__endswith="send_scheduled_message",
        args__0=lead_id,
        args__1=sched_id,
        status__in=["SCHEDULED", "STARTED"],
    )
    exists = qs.exists()
    if exists:
        logger.debug(
            "[DUP CHECK] ScheduledMessage %s for lead=%s pending tasks=%s",
            sched_id,
            lead_id,
            list(qs.values_list("task_id", "status"))[:5],
        )
    else:
        logger.debug(
            "[DUP CHECK] No pending ScheduledMessage task for lead=%s id=%s",
            lead_id,
            sched_id,
        )
    return exists


def _lead_scheduled_message_pending(sched_id: int) -> bool:
    """Return True if a LeadScheduledMessage task is already queued."""
    qs = CeleryTaskLog.objects.filter(
        name__endswith="send_lead_scheduled_message",
        args__0=sched_id,
        status__in=["SCHEDULED", "STARTED"],
    )
    exists = qs.exists()
    if exists:
        logger.debug(
            "[DUP CHECK] LeadScheduledMessage %s pending tasks=%s",
            sched_id,
            list(qs.values_list("task_id", "status"))[:5],
        )
    else:
        logger.debug("[DUP CHECK] No pending LeadScheduledMessage for id=%s", sched_id)
    return exists


@shared_task(bind=True)
def send_follow_up(self, lead_id: str, text: str):
    """
    Одноразова відправка follow-up повідомлення без повторних спроб.
    """
    biz_id = getattr(self.request, "headers", {}).get("business_id")
    token = None
    if biz_id:
        try:
            token = get_valid_business_token(biz_id)
        except Exception as exc:
            logger.error(
                f"[FOLLOW-UP] Error fetching token for business={biz_id}: {exc}"
            )
    if not token:
        token = get_token_for_lead(lead_id)
    if not token:
        logger.error(f"[FOLLOW-UP] No token available for lead={lead_id}")
        return
    url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"request_content": text, "request_type": "TEXT"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"[FOLLOW-UP] Sent to lead={lead_id}")
    except Exception as exc:
        if isinstance(exc, HTTPError) and exc.response is not None:
            message = _extract_yelp_error(exc.response)
            if exc.response.status_code in (401, 403):
                logger.error(
                    f"[FOLLOW-UP] Invalid or expired token for lead={lead_id}: {message}"
                )
            else:
                logger.error(
                    f"[FOLLOW-UP] HTTP {exc.response.status_code} for lead={lead_id}: {message}"
                )
        else:
            logger.error(f"[FOLLOW-UP] Error sending to lead={lead_id}: {exc}")
        raise


@shared_task
def send_due_scheduled_messages():
    """
    Знаходить усі ScheduledMessage, у яких next_run <= зараз,
    і негайно шикує їх на виконання send_scheduled_message.
    Використовує блокування рядків, щоб уникнути дублювання між
    одночасними викликами.
    """
    now = timezone.now()
    with transaction.atomic():
        due_list = (
            ScheduledMessage.objects.select_for_update(skip_locked=True)
            .filter(active=True, next_run__lte=now)
        )

        for sched in due_list:
            if _scheduled_message_pending(sched.lead_id, sched.id):
                logger.info(
                    f"[SCHEDULED] Message #{sched.id} already queued → skipping"
                )
                continue
            biz_id = (
                LeadDetail.objects.filter(lead_id=sched.lead_id)
                .values_list("business_id", flat=True)
                .first()
            )
            sched.next_run = timezone.now() + timezone.timedelta(seconds=1)
            sched.save(update_fields=["next_run"])
            send_scheduled_message.apply_async(
                args=[sched.lead_id, sched.id],
                headers={"business_id": biz_id},
                countdown=0,
            )


@shared_task(bind=True, default_retry_delay=60, max_retries=3)
def send_scheduled_message(self, lead_id: str, scheduled_id: int):
    """
    Відправляє заплановане повідомлення з пов’язаного FollowUpTemplate,
    логуючи результат у ScheduledMessageHistory та переплановуючи next_run.
    """
    try:
        sm = ScheduledMessage.objects.get(pk=scheduled_id, active=True)
    except ScheduledMessage.DoesNotExist:
        logger.warning(f"[SCHEDULED] Message #{scheduled_id} not found or inactive")
        return

    # Збираємо дані для підстановки в шаблон
    detail = LeadDetail.objects.filter(lead_id=lead_id).first()
    name = detail.user_display_name if detail else ""
    jobs = ", ".join(detail.project.get("job_names", [])) if detail else ""
    sep = ", " if name and jobs else ""

    tpl = sm.template  # це FK → FollowUpTemplate
    text = tpl.template.format(name=name, jobs=jobs, sep=sep)

    # Виконуємо POST до Yelp
    token = get_token_for_lead(lead_id)
    url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"request_content": text, "request_type": "TEXT"}

    status = "error"
    error = ""
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        status = "success"
        logger.info(f"[SCHEDULED] Sent msg #{sm.id} to lead={lead_id}")

        # Переплановуємо next_run згідно з delay з FollowUpTemplate
        sm.next_run = timezone.now() + tpl.delay
        sm.save(update_fields=['next_run'])
    except Exception as exc:
        error = str(exc)
        if isinstance(exc, HTTPError) and exc.response is not None:
            message = _extract_yelp_error(exc.response)
            error = message
            if exc.response.status_code in (401, 403):
                logger.error(
                    f"[SCHEDULED] Invalid or expired token for lead={lead_id}: {message}"
                )
            else:
                logger.error(
                    f"[SCHEDULED] HTTP {exc.response.status_code} for lead={lead_id}: {message}"
                )
        else:
            logger.error(f"[SCHEDULED] Error sending msg #{sm.id}: {exc}")

        # Деактивуємо, щоб не спамити помилками
        sm.active = False
        sm.save(update_fields=['active'])

    # Логуємо результат виконання
    ScheduledMessageHistory.objects.create(
        scheduled=sm,
        status=status,
        error=error[:2000]
    )

@shared_task
def send_due_lead_scheduled_messages():
    """
    Знаходимо всі LeadScheduledMessage з next_run <= зараз
    і миттєво посилаємо їх на виконання send_lead_scheduled_message.
    Використовуємо блокування рядків, щоб уникнути дублювання між
    одночасними викликами.
    """
    now = timezone.now()
    with transaction.atomic():
        due = (
            LeadScheduledMessage.objects.select_for_update(skip_locked=True)
            .filter(active=True, next_run__lte=now)
        )
        for msg in due:
            if _lead_scheduled_message_pending(msg.id):
                logger.info(
                    f"[LEAD SCHEDULED] #{msg.id} already queued → skipping"
                )
                continue
            biz_id = (
                LeadDetail.objects.filter(lead_id=msg.lead_id)
                .values_list("business_id", flat=True)
                .first()
            )
            msg.next_run = timezone.now() + timezone.timedelta(seconds=1)
            msg.save(update_fields=["next_run"])
            send_lead_scheduled_message.apply_async(
                args=[msg.id],
                headers={"business_id": biz_id},
                countdown=0,
            )


@shared_task(bind=True, default_retry_delay=60, max_retries=3)
def send_lead_scheduled_message(self, scheduled_id: int):
    """
    Відправляє разове заплановане повідомлення LeadScheduledMessage,
    логує результат у LeadScheduledMessageHistory і, якщо active, переплановує next_run.
    """
    try:
        msg = LeadScheduledMessage.objects.get(pk=scheduled_id, active=True)
    except LeadScheduledMessage.DoesNotExist:
        logger.warning(f"[LEAD SCHEDULED] #{scheduled_id} not found or inactive")
        return

    # Формуємо текст із підстановкою name/jobs/sep
    detail = LeadDetail.objects.filter(lead_id=msg.lead_id).first()
    name = detail.user_display_name if detail else ""
    jobs = ", ".join(detail.project.get("job_names", [])) if detail else ""
    sep = ", " if name and jobs else ""
    content = msg.content.format(name=name, jobs=jobs, sep=sep)

    token = get_token_for_lead(msg.lead_id)
    url = f"https://api.yelp.com/v3/leads/{msg.lead_id}/events"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"request_content": content, "request_type": "TEXT"}

    status = "error"
    error = ""
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        status = "success"
        logger.info(f"[LEAD SCHEDULED] Sent #{msg.id} to {msg.lead_id}")

        # Для одноразового повідомлення—деактивуємо або можна залишити active=False
        msg.active = False
        msg.save(update_fields=['active'])
    except Exception as exc:
        error = str(exc)
        if isinstance(exc, HTTPError) and exc.response is not None:
            message = _extract_yelp_error(exc.response)
            error = message
            if exc.response.status_code in (401, 403):
                logger.error(
                    f"[LEAD SCHEDULED] Invalid or expired token for lead={msg.lead_id}: {message}"
                )
            else:
                logger.error(
                    f"[LEAD SCHEDULED] HTTP {exc.response.status_code} for lead={msg.lead_id}: {message}"
                )
        else:
            logger.error(f"[LEAD SCHEDULED] Error #{msg.id}: {exc}")
        # дезактивуємо, щоб не спамити помилками
        msg.active = False
        msg.save(update_fields=['active'])

    # Логуємо історію
    LeadScheduledMessageHistory.objects.create(
        scheduled=msg,
        status=status,
        error=error[:2000]
    )


@shared_task
def refresh_expiring_tokens():
    """Proactively refresh tokens expiring soon."""
    margin = timezone.now() + timezone.timedelta(minutes=10)
    tokens = YelpToken.objects.filter(expires_at__lte=margin)
    if not tokens:
        logger.debug("[TOKEN REFRESH] No tokens require refresh")
    for tok in tokens:
        logger.info(f"[TOKEN REFRESH] Attempting refresh for {tok.business_id}")
        try:
            old_refresh = tok.refresh_token
            data = rotate_refresh_token(old_refresh)
            update_shared_refresh_token(old_refresh, data)
            tok.access_token = data["access_token"]
            tok.refresh_token = data.get("refresh_token", tok.refresh_token)
            exp = data.get("expires_in")
            if exp:
                tok.expires_at = timezone.now() + timezone.timedelta(seconds=exp)
            tok.save()
            logger.info(
                f"[TOKEN REFRESH] refreshed for {tok.business_id}; expires_at={tok.expires_at}"
            )
        except Exception as exc:
            if isinstance(exc, HTTPError) and exc.response is not None:
                msg = _extract_yelp_error(exc.response)
                logger.error(
                    f"[TOKEN REFRESH] HTTP {exc.response.status_code} for {tok.business_id}: {msg}",
                    exc_info=True,
                )
            else:
                logger.error(
                    f"[TOKEN REFRESH] failed for {tok.business_id}: {exc}",
                    exc_info=True,
                )


def reschedule_follow_up_tasks(template: "FollowUpTemplate"):
    """Update next_run for ScheduledMessage objects of this template."""
    from .utils import adjust_due_time
    biz = template.business
    now = timezone.now()
    for sm in ScheduledMessage.objects.filter(template=template, active=True):
        new_run = adjust_due_time(
            now + template.delay,
            biz.time_zone if biz else None,
            template.open_from,
            template.open_to,
        )
        sm.next_run = new_run
        sm.save(update_fields=["next_run"])
        logger.info(
            f"[SCHEDULED] Rescheduled msg #{sm.id} for template {template.id}"
        )

@shared_task
def cleanup_celery_logs(days: int = 30):
    """Remove old CeleryTaskLog entries."""
    from django.core.management import call_command

    call_command("cleanup_celery_logs", days=str(days))

