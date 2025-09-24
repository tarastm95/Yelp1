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
    CeleryTaskLog,
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
            # Step 1: Exchange code for tokens (FAST - only essential operation)
            logger.info("[OAUTH-CALLBACK] 🚀 Starting OAuth callback processing")
            logger.info(f"[OAUTH-CALLBACK] Code: {code[:10]}...")
            logger.info(f"[OAUTH-CALLBACK] State: {state}")
            
            callback_start_time = time.time()
            
            resp = requests.post(
                settings.YELP_TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,  # Increased timeout for token exchange
            )
            
            if resp.status_code != 200:
                logger.error(f"[OAUTH-CALLBACK] ❌ Token exchange failed: status={resp.status_code}, response={resp.text}")
                return redirect(f"{settings.FRONTEND_URL}/callback?error=token_exchange_failed")

            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)  # Default to 1 hour if not specified

            if not access_token:
                logger.error("[OAUTH-CALLBACK] ❌ No access token in response")
                return redirect(f"{settings.FRONTEND_URL}/callback?error=token_error")

            token_exchange_duration = time.time() - callback_start_time
            logger.info(f"[OAUTH-CALLBACK] ✅ Token exchange successful in {token_exchange_duration:.2f}s")
            logger.info(f"[OAUTH-CALLBACK] Token expires in: {expires_in} seconds")
            logger.info(f"[OAUTH-CALLBACK] Access token: {access_token[:20]}...")
            
            # Step 2: Queue background processing (FAST - just queue the job)
            logger.info("[OAUTH-CALLBACK] 📤 Queuing background OAuth data processing")
            
            try:
                from .tasks import process_oauth_data
                
                # Queue the background job
                job = process_oauth_data.delay(access_token, refresh_token, expires_in)
                
                queue_duration = time.time() - callback_start_time - token_exchange_duration
                total_duration = time.time() - callback_start_time
                
                logger.info(f"[OAUTH-CALLBACK] ✅ Background job queued successfully")
                logger.info(f"[OAUTH-CALLBACK] Job ID: {job.id}")
                logger.info(f"[OAUTH-CALLBACK] Queue duration: {queue_duration:.2f}s")
                logger.info(f"[OAUTH-CALLBACK] Total callback duration: {total_duration:.2f}s")
                
                # Step 3: Return immediately with success
                logger.info("[OAUTH-CALLBACK] 🎉 OAuth callback completed - returning to frontend")
                return redirect(f"{settings.FRONTEND_URL}/callback?access_token={access_token}&processing=background")
                
            except ImportError as e:
                logger.error(f"[OAUTH-CALLBACK] ❌ Failed to import background job: {e}")
                return redirect(f"{settings.FRONTEND_URL}/callback?error=background_job_failed")
            except Exception as e:
                logger.error(f"[OAUTH-CALLBACK] ❌ Failed to queue background job: {e}")
                logger.exception("[OAUTH-CALLBACK] Background job queue exception:")
                return redirect(f"{settings.FRONTEND_URL}/callback?error=background_job_failed")
                
        except requests.RequestException as e:
            duration = time.time() - callback_start_time if 'callback_start_time' in locals() else 0
            logger.error(f"[OAUTH-CALLBACK] ❌ Network error during token exchange: {e}")
            logger.error(f"[OAUTH-CALLBACK] Duration before error: {duration:.2f}s")
            return redirect(f"{settings.FRONTEND_URL}/callback?error=token_request_failed")
        except Exception as e:
            duration = time.time() - callback_start_time if 'callback_start_time' in locals() else 0
            logger.error(f"[OAUTH-CALLBACK] ❌ Unexpected error during OAuth callback: {e}")
            logger.exception("[OAUTH-CALLBACK] Full exception traceback:")
            logger.error(f"[OAUTH-CALLBACK] Duration before error: {duration:.2f}s")
            return redirect(f"{settings.FRONTEND_URL}/callback?error=unexpected_error")


class OAuthProcessingStatusView(APIView):
    """
    Check the status of OAuth background processing.
    Returns processing progress and completion status.
    """
    
    def get(self, request):
        """Get OAuth processing status."""
        try:
            # Check if we have any recent OAuth processing logs (last 30 minutes)
            recent_logs = CeleryTaskLog.objects.filter(
                name__in=['process_oauth_data', 'process_single_business'],
                created_at__gte=timezone.now() - timedelta(minutes=30)
            ).order_by('-created_at')
            
            if not recent_logs.exists():
                return Response({
                    "status": "no_recent_activity",
                    "message": "No recent OAuth processing activity found",
                    "progress": 0,
                    "details": {}
                })
            
            # Count total businesses and processed businesses
            total_tokens = YelpToken.objects.count()
            businesses_with_details = YelpBusiness.objects.count()
            
            # Get job statuses
            oauth_jobs = recent_logs.filter(name='process_oauth_data')
            business_jobs = recent_logs.filter(name='process_single_business')
            
            running_jobs = recent_logs.filter(status__in=['STARTED', 'SCHEDULED']).count()
            completed_jobs = recent_logs.filter(status='SUCCESS').count()
            failed_jobs = recent_logs.filter(status='FAILURE').count()
            total_jobs = recent_logs.count()
            
            # Determine overall status
            if running_jobs > 0:
                overall_status = "processing"
                message = f"Processing {running_jobs} jobs..."
            elif failed_jobs > 0 and completed_jobs == 0:
                overall_status = "failed"
                message = f"Processing failed ({failed_jobs} failed jobs)"
            elif completed_jobs > 0 and running_jobs == 0:
                overall_status = "completed"
                message = f"Processing completed successfully"
            else:
                overall_status = "unknown"
                message = "Processing status unknown"
            
            # Calculate progress percentage
            if total_jobs > 0:
                progress = round((completed_jobs / total_jobs) * 100, 1)
            else:
                progress = 0
            
            # Get latest activity
            latest_log = recent_logs.first()
            
            return Response({
                "status": overall_status,
                "message": message,
                "progress": progress,
                "last_updated": latest_log.created_at if latest_log else None,
                "details": {
                    "total_businesses": total_tokens,
                    "businesses_processed": businesses_with_details,
                    "jobs": {
                        "running": running_jobs,
                        "completed": completed_jobs,
                        "failed": failed_jobs,
                        "total": total_jobs
                    },
                    "recent_oauth_jobs": oauth_jobs.count(),
                    "recent_business_jobs": business_jobs.count()
                }
            })
            
        except Exception as e:
            logger.error(f"[OAUTH-STATUS] ❌ Error checking OAuth status: {e}")
            logger.exception("[OAUTH-STATUS] Full exception traceback:")
            return Response({
                "status": "error",
                "message": f"Failed to check processing status: {str(e)}",
                "progress": 0
            }, status=500)
