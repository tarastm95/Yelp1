from django.contrib import admin
from .models import NotificationSetting


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "message_template"]
