from django.test import TestCase
from rest_framework.test import APIRequestFactory
from webhooks.lead_views import (
    NotificationSettingListCreateView,
    NotificationSettingDetailView,
)
from webhooks.models import YelpBusiness, NotificationSetting


class NotificationSettingQuerysetTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.list_view = NotificationSettingListCreateView.as_view()
        self.detail_view = NotificationSettingDetailView.as_view()
        self.biz1 = YelpBusiness.objects.create(business_id="b1", name="Biz 1")
        self.biz2 = YelpBusiness.objects.create(business_id="b2", name="Biz 2")
        self.global_setting = NotificationSetting.objects.create(
            business=None,
            phone_number="111",
            message_template="g",
        )
        self.biz1_setting = NotificationSetting.objects.create(
            business=self.biz1,
            phone_number="222",
            message_template="b1",
        )
        self.biz2_setting = NotificationSetting.objects.create(
            business=self.biz2,
            phone_number="333",
            message_template="b2",
        )

    def _get_list(self, bid=None):
        url = "/notifications/"
        if bid:
            url += f"?business_id={bid}"
        request = self.factory.get(url)
        response = self.list_view(request)
        response.render()
        return response

    def _get_detail(self, pk, bid=None):
        url = f"/notifications/{pk}/"
        if bid:
            url += f"?business_id={bid}"
        request = self.factory.get(url)
        response = self.detail_view(request, pk=pk)
        response.render()
        return response

    def test_list_filters_by_business_id(self):
        resp = self._get_list("b1")
        self.assertEqual(resp.status_code, 200)
        ids = [item["id"] for item in resp.data]
        self.assertEqual(ids, [self.biz1_setting.id])

    def test_detail_with_wrong_business_id_returns_404(self):
        resp = self._get_detail(self.biz1_setting.id, "b2")
        self.assertEqual(resp.status_code, 404)

    def test_detail_with_correct_business_id_returns_object(self):
        resp = self._get_detail(self.biz1_setting.id, "b1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.biz1_setting.id)
