from django.contrib import admin
from .models import NotificationSetting, AISettings, TimeBasedGreeting


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


@admin.register(TimeBasedGreeting)
class TimeBasedGreetingAdmin(admin.ModelAdmin):
    """Django Admin для налаштувань часових привітань"""
    
    list_display = [
        'id',
        'business_name',
        'morning_greeting',
        'afternoon_greeting',
        'evening_greeting',
        'night_greeting',
        'created_at'
    ]
    
    list_filter = [
        'created_at',
        'business'
    ]
    
    fieldsets = (
        ('🏢 Business Configuration', {
            'fields': ('business',),
            'description': 'Leave blank for global default settings'
        }),
        ('⏰ Time Ranges', {
            'fields': (
                ('morning_start', 'morning_end'),
                ('afternoon_start', 'afternoon_end'),
                ('evening_start', 'evening_end'),
            ),
        }),
        ('💬 Greetings', {
            'fields': (
                'morning_greeting',
                'afternoon_greeting',
                'evening_greeting',
                'night_greeting',
            ),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def business_name(self, obj):
        """Відображення назви бізнесу або 'Global Default'"""
        if obj.business:
            return obj.business.name
        return "🌍 Global Default"
    business_name.short_description = "Business"
    business_name.admin_order_field = "business__name"
