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

from .models import YelpOAuthState, AutoResponseSettings, YelpToken, YelpBusiness

logger = logging.getLogger(__name__)


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

            settings_obj, _ = AutoResponseSettings.objects.get_or_create(id=1)
            settings_obj.access_token = access_token
            settings_obj.refresh_token = refresh_token or settings_obj.refresh_token
            settings_obj.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            settings_obj.enabled = True
            settings_obj.save()

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
                            YelpBusiness.objects.update_or_create(
                                business_id=bid,
                                defaults={
                                    "name": name,
                                    "location": loc,
                                    "time_zone": tz,
                                    "details": det,
                                },
                            )
                    except requests.RequestException as e:
                        logger.error(f"Failed to fetch business details for {bid}: {e}")

            return redirect(f"{settings.FRONTEND_URL}/callback?access_token={access_token}")
        except requests.RequestException as e:
            logger.error(f"OAuth request error: {e}")
            return redirect(f"{settings.FRONTEND_URL}/callback?error=token_request_failed")
