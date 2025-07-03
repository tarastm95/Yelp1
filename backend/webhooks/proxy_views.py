import logging
import requests
from django.http import HttpResponse
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .utils import (
    get_valid_business_token,
    get_token_for_lead,
)
from .serializers import YelpBusinessSerializer
from .models import YelpToken, YelpBusiness

logger = logging.getLogger(__name__)


class LeadEventsProxyView(APIView):
    """Proxy for Yelp lead events"""

    def get(self, request, lead_id):
        token = get_token_for_lead(lead_id)
        if not token:
            return Response({"detail": "unknown business"}, status=400)
        url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"limit": request.query_params.get("limit", 20)}

        logger.info(
            f"[LEAD EVENTS] GET {url} params={params} token_ending={token[-4:]}"
        )

        resp = requests.get(url, headers=headers, params=params)
        logger.info(
            f"[LEAD EVENTS] Yelp response status={resp.status_code} lead={lead_id}"
        )
        if resp.status_code != 200:
            logger.error(f"[LEAD EVENTS] Error body: {resp.text}")
            try:
                error_data = resp.json()
            except ValueError:
                error_data = {"detail": resp.text}
            return Response(error_data, status=resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            data = {}
        logger.info(
            f"[LEAD EVENTS] Returned {len(data.get('events', []))} event(s) for lead={lead_id}"
        )
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, lead_id):
        token = get_token_for_lead(lead_id)
        if not token:
            return Response({"detail": "unknown business"}, status=400)
        url = f"https://api.yelp.com/v3/leads/{lead_id}/events"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "request_content": request.data.get("request_content"),
            "request_type": request.data.get("request_type", "TEXT"),
        }

        logger.info(
            f"[LEAD EVENTS] POST {url} token_ending={token[-4:]} payload_keys={list(payload.keys())}"
        )

        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info(
            f"[LEAD EVENTS] POST response status={resp.status_code} lead={lead_id}"
        )
        if resp.status_code not in (200, 201):
            logger.error(f"[LEAD EVENTS] POST error body: {resp.text}")
            try:
                error_data = resp.json()
            except ValueError:
                error_data = {"detail": resp.text}
            return Response(error_data, status=resp.status_code)

        try:
            data = resp.json()
        except ValueError:
            data = {}
        return Response(data, status=status.HTTP_201_CREATED)


class LeadIDsProxyView(APIView):
    """Proxy for Yelp lead ids"""

    def get(self, request, business_id):
        token = get_valid_business_token(business_id)
        url = f"https://api.yelp.com/v3/businesses/{business_id}/lead_ids"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error(f"[YELP ERROR] status={resp.status_code} body={resp.text}")
            try:
                error_data = resp.json()
            except ValueError:
                error_data = {"detail": resp.text}
            return Response(error_data, status=resp.status_code)
        return Response(resp.json(), status=status.HTTP_200_OK)


class LeadDetailProxyView(APIView):
    """Proxy for Yelp lead detail"""

    def get(self, request, lead_id):
        token = get_token_for_lead(lead_id)
        if not token:
            return Response({"detail": "unknown business"}, status=400)
        url = f"https://api.yelp.com/v3/leads/{lead_id}"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error(f"[YELP ERROR] status={resp.status_code} body={resp.text}")
            try:
                error_data = resp.json()
            except ValueError:
                error_data = {"detail": resp.text}
            return Response(error_data, status=resp.status_code)
        return Response(resp.json(), status=status.HTTP_200_OK)


class BusinessListView(APIView):
    """Return list of stored Yelp businesses."""

    def get(self, request):
        qs = YelpBusiness.objects.all()
        serializer = YelpBusinessSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BusinessLeadsView(APIView):
    """Proxy to fetch leads for a business."""

    def get(self, request):
        business_id = request.query_params.get("business_id")
        if not business_id:
            return Response({"detail": "business_id required"}, status=400)

        token = get_valid_business_token(business_id)
        url = f"https://partner-api.yelp.com/v3/businesses/{business_id}/leads"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, params=request.query_params)
        if resp.status_code != 200:
            try:
                err = resp.json()
            except ValueError:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)
        return Response(resp.json(), status=status.HTTP_200_OK)


class BusinessEventsView(APIView):
    """Proxy to fetch events for a business."""

    def get(self, request):
        business_id = request.query_params.get("business_id")
        if not business_id:
            return Response({"detail": "business_id required"}, status=400)

        token = get_valid_business_token(business_id)
        url = f"https://partner-api.yelp.com/v3/businesses/{business_id}/events"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, params=request.query_params)
        if resp.status_code != 200:
            try:
                err = resp.json()
            except ValueError:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)
        return Response(resp.json(), status=status.HTTP_200_OK)


class AttachmentProxyView(APIView):
    """Proxy to fetch a lead's attachment binary."""

    def get(self, request, lead_id: str, attachment_id: str):
        token = get_token_for_lead(lead_id)
        if not token:
            return Response({"detail": "unknown business"}, status=400)
        url = f"https://api.yelp.com/v3/leads/{lead_id}/attachments/{attachment_id}"
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(url, headers=headers, stream=True)
        if resp.status_code != 200:
            try:
                err = resp.json()
            except ValueError:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)

        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        return HttpResponse(resp.content, content_type=content_type)

class SubscriptionProxyView(APIView):
    """Proxy for Yelp business subscriptions."""

    base_url = "https://api.yelp.com/v3/businesses/subscriptions"

    def get(self, request):
        sub_type = request.query_params.get("subscription_type", "WEBHOOK")
        headers = {"Authorization": f"Bearer {settings.YELP_API_KEY}"}
        resp = requests.get(self.base_url, headers=headers, params={"subscription_type": sub_type})
        if resp.status_code != 200:
            try:
                err = resp.json()
            except ValueError:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)
        return Response(resp.json(), status=status.HTTP_200_OK)

    def post(self, request):
        headers = {"Authorization": f"Bearer {settings.YELP_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "subscription_types": request.data.get("subscription_types", ["WEBHOOK"]),
            "business_ids": request.data.get("business_ids", []),
        }
        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 201, 202):
            try:
                err = resp.json()
            except ValueError:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            data = {}
        return Response(data, status=resp.status_code)

    def delete(self, request):
        headers = {"Authorization": f"Bearer {settings.YELP_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "subscription_types": request.data.get("subscription_types", ["WEBHOOK"]),
            "business_ids": request.data.get("business_ids", []),
        }
        resp = requests.delete(self.base_url, json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 204):
            try:
                err = resp.json()
            except ValueError:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)
        if resp.text:
            try:
                data = resp.json()
            except ValueError:
                data = {}
            return Response(data, status=resp.status_code)
        return Response(status=resp.status_code)
