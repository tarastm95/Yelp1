from django.urls import path
from .views import (
    WebhookView, EventListView, EventRetrieveView,
    yelp_auth_callback_view, save_yelp_state,
    YelpAuthInitView, YelpAuthCallbackView,
    AutoResponseSettingsView, LeadEventsProxyView, LeadIDsProxyView, LeadDetailProxyView, AttachmentProxyView,
    ProcessedLeadListView, LeadEventListAPIView, LeadDetailListAPIView,
    LeadDetailRetrieveAPIView, LeadLastEventAPIView, LeadEventRetrieveAPIView,
    FollowUpTemplateListCreateView, FollowUpTemplateDetailView,
    BusinessListView, BusinessLeadsView, BusinessEventsView,
    SubscriptionProxyView,
    YelpTokenListView,
    NotificationSettingListCreateView,
    NotificationSettingDetailView,
)
from .oauth_views import OAuthProcessingStatusView
from .lead_views import BusinessSMSSettingsView, AIPreviewView, AIGlobalSettingsView, AITestPreviewView, TimeBasedGreetingView, JobMappingListCreateView, JobMappingDetailView, LeadTimeSeriesView
from .task_views import TaskLogListView, TaskStatsView, TaskRevokeView, MessageTaskListView, TaskTimeSeriesView
from .sms_views import SendSMSAPIView, SMSLogListView, SMSStatsView, SMSTimeSeriesView, SMSUpdatePricesView
from .lead_logs_views import lead_activity_history, lead_complete_timeline, lead_logs_search
from .diagnostic_views import (
    system_health_dashboard, error_logs_dashboard, resolve_error,
      performance_metrics_dashboard, diagnostic_action, lead_diagnostic_report, system_status_check
  )

# Sample Replies API Views (Mode 2: AI Generated) + Vector Search
from .sample_replies_views import (
    SampleRepliesFileUploadView,
    SampleRepliesTextSaveView,
    SampleRepliesStatusView,
    VectorSearchTestView,
    VectorChunkListView,
    VectorDocumentDeleteView,
    VectorDocumentBulkDeleteView
)

# ML Classifier API Views
from .ml_classifier_views import (
    MLClassifierStatusView,
    MLClassifierRetrainView,
    MLClassifierTestView
)

urlpatterns = [
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('events/', EventListView.as_view(), name='events'),
    path('events/<int:pk>/', EventRetrieveView.as_view(), name='event-detail'),
    path(
        'yelp/auth/callback/',
        yelp_auth_callback_view,
        name='yelp-auth-callback-simple'
    ),
    path(
        'save-yelp-state/',
        save_yelp_state,
        name='save-yelp-state'
    ),
    path(
        'yelp/auth/init/',
        YelpAuthInitView.as_view(),
        name='yelp-auth-init'
    ),
    path(
        'yelp/auth/callback-advanced/',
        YelpAuthCallbackView.as_view(),
        name='yelp-auth-callback'
    ),
    path(
        'oauth/processing-status/',
        OAuthProcessingStatusView.as_view(),
        name='oauth-processing-status'
    ),
    path(
        'settings/auto-response/',
        AutoResponseSettingsView.as_view(),
        name='auto-response-settings'
    ),
    path(
        'ai/preview/',
        AIPreviewView.as_view(),
        name='ai-preview'
    ),
    path(
        'ai/global-settings/',
        AIGlobalSettingsView.as_view(),
        name='ai-global-settings'
    ),
    path(
        'ai/test-preview/',
        AITestPreviewView.as_view(),
        name='ai-test-preview'
    ),
    path(
        'templates/auto-response/',
        AutoResponseSettingsView.as_view(),
        name='templates-auto-response-settings'
    ),
    path(
        'yelp/leads/<str:lead_id>/events/',
        LeadEventsProxyView.as_view(),
        name='proxy-lead-events'
    ),


    path('yelp/businesses/<str:business_id>/lead_ids/', LeadIDsProxyView.as_view()),
    path('businesses/', BusinessListView.as_view(), name='business-list'),
    path('leads/', BusinessLeadsView.as_view(), name='business-leads'),
    path('events/', BusinessEventsView.as_view(), name='business-events'),
    path('businesses/subscriptions/', SubscriptionProxyView.as_view(), name='business-subscriptions'),
    path('yelp/leads/<str:lead_id>/', LeadDetailProxyView.as_view()),
    path(
        'yelp/leads/<str:lead_id>/attachments/<str:attachment_id>/',
        AttachmentProxyView.as_view(),
        name='proxy-attachment',
    ),
    path('processed_leads/', ProcessedLeadListView.as_view(), name='processed-leads-list'),
    path('lead-details/', LeadDetailListAPIView.as_view(), name='lead-list'),
    path('lead-details/<str:lead_id>/', LeadDetailRetrieveAPIView.as_view(), name='lead-detail'),
    path('lead-events/', LeadEventListAPIView.as_view(), name='lead-event-list'),
    path('lead-events/<str:lead_id>/latest/', LeadLastEventAPIView.as_view(), name='lead-last-event'),
    path('lead-events/<str:event_id>/', LeadEventRetrieveAPIView.as_view(), name='lead-event-detail'),
    path('follow-up-templates/', FollowUpTemplateListCreateView.as_view(), name='followup-list-create'),
    path('follow-up-templates/<int:pk>/', FollowUpTemplateDetailView.as_view(), name='followup-detail'),
    path('tokens/', YelpTokenListView.as_view(), name='token-list'),
    path('tasks/', TaskLogListView.as_view(), name='task-log-list'),
    path('tasks/stats/', TaskStatsView.as_view(), name='task-stats'),
    path('tasks/<str:task_id>/cancel/', TaskRevokeView.as_view(), name='task-revoke'),
    path('message_tasks/', MessageTaskListView.as_view(), name='message-task-list'),
    path('send-sms/', SendSMSAPIView.as_view(), name='send-sms'),
    path('sms-logs/', SMSLogListView.as_view(), name='sms-log-list'),
    path('sms-logs/stats/', SMSStatsView.as_view(), name='sms-stats'),
    path('notifications/', NotificationSettingListCreateView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', NotificationSettingDetailView.as_view(), name='notification-detail'),
    path('business-sms-settings/', BusinessSMSSettingsView.as_view(), name='business-sms-settings'),
    path('time-greetings/', TimeBasedGreetingView.as_view(), name='time-greetings'),
    path('job-mappings/', JobMappingListCreateView.as_view(), name='job-mapping-list'),
    path('job-mappings/<int:id>/', JobMappingDetailView.as_view(), name='job-mapping-detail'),
    # Time-series endpoints for analytics
    path('sms-logs/timeseries/', SMSTimeSeriesView.as_view(), name='sms-timeseries'),
    path('tasks/timeseries/', TaskTimeSeriesView.as_view(), name='task-timeseries'),
    path('leads/timeseries/', LeadTimeSeriesView.as_view(), name='lead-timeseries'),
    # SMS price update endpoint
    path('sms-logs/update-prices/', SMSUpdatePricesView.as_view(), name='sms-update-prices'),
    
    # ===== LEAD ACTIVITY LOGGING ENDPOINTS =====
    path('leads/<str:lead_id>/logs/', lead_activity_history, name='lead-activity-logs'),
    path('leads/<str:lead_id>/timeline/', lead_complete_timeline, name='lead-complete-timeline'),
    path('leads/search/', lead_logs_search, name='lead-logs-search'),
    
    # ===== DIAGNOSTIC & ERROR TRACKING ENDPOINTS =====
    path('system/health/', system_health_dashboard, name='system-health'),
    path('system/errors/', error_logs_dashboard, name='error-logs'),
    path('system/errors/<str:error_id>/resolve/', resolve_error, name='resolve-error'),
    path('system/metrics/', performance_metrics_dashboard, name='performance-metrics'),
    path('system/actions/', diagnostic_action, name='diagnostic-actions'),
    path('system/status/', system_status_check, name='system-status'),
    path('leads/<str:lead_id>/diagnostics/', lead_diagnostic_report, name='lead-diagnostics'),
    
    # Sample Replies Management (Mode 2: AI Generated) + Vector Search
    path('sample-replies/upload/', SampleRepliesFileUploadView.as_view(), name='sample_replies_upload'),
    path('sample-replies/save-text/', SampleRepliesTextSaveView.as_view(), name='sample_replies_save_text'),
    path('sample-replies/status/', SampleRepliesStatusView.as_view(), name='sample_replies_status'),
    path('sample-replies/vector-test/', VectorSearchTestView.as_view(), name='vector_search_test'),
    path('sample-replies/chunks/', VectorChunkListView.as_view(), name='vector_chunks_list'),
    
    # Vector Document Management
    path('sample-replies/documents/<int:document_id>/delete/', VectorDocumentDeleteView.as_view(), name='vector_document_delete'),
    path('sample-replies/documents/bulk-delete/', VectorDocumentBulkDeleteView.as_view(), name='vector_documents_bulk_delete'),
    
    # ML Classifier Management
    path('ml-classifier/status/', MLClassifierStatusView.as_view(), name='ml_classifier_status'),
    path('ml-classifier/retrain/', MLClassifierRetrainView.as_view(), name='ml_classifier_retrain'),
    path('ml-classifier/test/', MLClassifierTestView.as_view(), name='ml_classifier_test'),
]
