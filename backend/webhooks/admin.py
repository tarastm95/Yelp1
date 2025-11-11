from django.contrib import admin
from django import forms
from .models import NotificationSetting, WhatsAppLog, WhatsAppNotificationSetting, AISettings, TimeBasedGreeting


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "business", "message_template"]


@admin.register(WhatsAppLog)
class WhatsAppLogAdmin(admin.ModelAdmin):
    list_display = ["sid", "to_phone", "business_id", "purpose", "status", "sent_at"]
    list_filter = ["status", "purpose", "sent_at"]
    search_fields = ["sid", "to_phone", "business_id", "lead_id"]


@admin.register(WhatsAppNotificationSetting)
class WhatsAppNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "business", "message_template"]


class AISettingsAdminForm(forms.ModelForm):
    """Custom form for AISettings with model choices dropdown"""
    
    MODEL_CHOICES = [
        ('gpt-4o', 'GPT-4o (Default) - Best quality and compliance with instructions'),
        ('gpt-4o-mini', 'GPT-4o Mini (Budget) - Fastest & most cost-effective'),
        ('gpt-4.1', 'GPT-4.1 (Enhanced) - Improved instruction following and reasoning'),
        ('gpt-4.1-mini', 'GPT-4.1 Mini (Efficient) - Fast GPT-4.1 variant'),
        ('gpt-4.1-nano', 'GPT-4.1 Nano (Speed) - Ultra-fast for high-volume'),
        ('gpt-5', 'GPT-5 (Flagship) - Large context window (~400k tokens), reasoning router'),
        ('gpt-5-mini', 'GPT-5 Mini (Fast) - Faster GPT-5 with reasoning capabilities'),
        ('gpt-5-nano', 'GPT-5 Nano (Ultra-Fast) - Lightest GPT-5 variant'),
    ]
    
    openai_model = forms.ChoiceField(
        choices=MODEL_CHOICES,
        initial='gpt-4o',
        help_text='Fallback модель OpenAI (коли не вказана для бізнесу)',
        widget=forms.Select(attrs={'style': 'width: 600px;'})
    )
    
    class Meta:
        model = AISettings
        fields = '__all__'


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    """Django Admin для глобальних AI налаштувань"""
    
    form = AISettingsAdminForm
    
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
