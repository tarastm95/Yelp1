from django.contrib import admin
from django import forms
from .models import NotificationSetting, AISettings, TimeBasedGreeting


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "business", "message_template"]


class AISettingsAdminForm(forms.ModelForm):
    """Custom form for AISettings with model choices dropdown"""
    
    MODEL_CHOICES = [
        ('gpt-4o', 'GPT-4o (Default) - Best quality and compliance with instructions'),
        ('gpt-4o-mini', 'GPT-4o Mini (Budget) - Fastest & most cost-effective'),
        ('gpt-5', 'GPT-5 (Flagship) - Large context window (~400k tokens), best for RAG'),
        ('gpt-5-mini', 'GPT-5 Mini (Fast) - Faster & cheaper GPT-5 version'),
        ('gpt-5-nano', 'GPT-5 Nano (Ultra-Fast) - Lightest version for high-volume scenarios'),
        ('gpt-4o-realtime', 'GPT-4o Realtime (Low Latency) - Real-time streaming for instant responses'),
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
