from django.contrib import admin
from .models import NotificationSetting, AISettings


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "business", "message_template"]


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    """Django Admin для глобальних AI налаштувань"""
    
    list_display = [
        'id', 
        'openai_model', 
        'max_message_length', 
        'default_temperature',
        'always_include_business_name',
        'fallback_to_template',
        'created_at'
    ]
    
    fieldsets = (
        ('🤖 OpenAI Configuration', {
            'fields': ('openai_model',),
            'description': 'OpenAI API key is managed separately for security'
        }),
        ('📝 Message Generation Settings', {
            'fields': (
                'base_system_prompt',
                'max_message_length',
                'default_temperature',
            )
        }),
        ('⚙️ Business Rules', {
            'fields': (
                'always_include_business_name',
                'always_use_customer_name',
                'fallback_to_template',
            )
        }),
        ('🚦 Rate Limiting', {
            'fields': ('requests_per_minute',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def has_delete_permission(self, request, obj=None):
        """Запобігти видаленню глобальних налаштувань"""
        return False
    
    def has_add_permission(self, request):
        """Дозволити тільки один запис глобальних налаштувань"""
        return not AISettings.objects.exists()
