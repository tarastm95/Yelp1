# webhooks/tasks.py

import logging
import requests
from requests import HTTPError
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import redis

from .models import (
    LeadDetail,
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

# Prevent concurrent tasks for the same lead
LOCK_TIMEOUT = 60  # seconds


_redis_client = None


def _get_lock(lock_id: str, timeout: int = LOCK_TIMEOUT, blocking_timeout: int = 5):
    """Return a redis-py lock from the configured cache backend."""
    if hasattr(cache, "lock"):
        return cache.lock(lock_id, timeout=timeout, blocking_timeout=blocking_timeout)

    client = getattr(cache, "client", None)
    if client and hasattr(client, "get_client"):
        redis_client = client.get_client(write=True)
    else:
        global _redis_client
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(settings.REDIS_URL)
        redis_client = _redis_client

    return redis_client.lock(lock_id, timeout=timeout, blocking_timeout=blocking_timeout)


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


@shared_task(bind=True)
def send_follow_up(self, lead_id: str, text: str):
    """
    Одноразова відправка follow-up повідомлення без повторних спроб.
    """
    lock_id = f"lead-lock:{lead_id}"
    try:
        with _get_lock(lock_id, timeout=LOCK_TIMEOUT, blocking_timeout=5):
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

            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"[FOLLOW-UP] Sent to lead={lead_id}")
    except Exception as exc:
        if isinstance(exc, HTTPError) and getattr(exc, "response", None) is not None:
            message = _extract_yelp_error(exc.response)
            if exc.response.status_code in (401, 403):
                logger.error(
                    f"[FOLLOW-UP] Invalid or expired token for lead={lead_id}: {message}"
                )
            else:
                logger.error(
                    f"[FOLLOW-UP] HTTP {exc.response.status_code} for lead={lead_id}: {message}"
                )
        elif "acquire" in str(exc):
            logger.info(f"[FOLLOW-UP] Another task running for lead={lead_id}; skipping")
            return
        else:
            logger.error(f"[FOLLOW-UP] Error sending to lead={lead_id}: {exc}")
        raise


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



@shared_task
def cleanup_celery_logs(days: int = 30):
    """Remove old CeleryTaskLog entries."""
    from django.core.management import call_command

    call_command("cleanup_celery_logs", days=str(days))

