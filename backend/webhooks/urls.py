from django.urls import path
from .views import (
    WebhookView, EventListView, EventRetrieveView,
    yelp_auth_callback_view, save_yelp_state,
    YelpAuthInitView, YelpAuthCallbackView,
    AutoResponseSettingsView, LeadEventsProxyView, LeadIDsProxyView, LeadDetailProxyView, AttachmentProxyView, ScheduledMessageHistoryList,
    ScheduledMessageListCreate, ScheduledMessageDetail, ProcessedLeadListView, LeadEventListAPIView, LeadDetailListAPIView,
    LeadDetailRetrieveAPIView, LeadLastEventAPIView, LeadEventRetrieveAPIView,
    FollowUpTemplateListCreateView, FollowUpTemplateDetailView,
    AutoResponseSettingsTemplateListCreateView, AutoResponseSettingsTemplateDetailView,
    BusinessListView, BusinessLeadsView, BusinessEventsView,
    SubscriptionProxyView, YelpTokenListView,
)
from .task_views import TaskLogListView, MessageTaskListView, TaskRevokeView

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
        'settings/auto-response/',
        AutoResponseSettingsView.as_view(),
        name='auto-response-settings'
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

    # нові роуты для запланованих
    path(
        'yelp/leads/<str:lead_id>/scheduled_messages/',
        ScheduledMessageListCreate.as_view(),
        name='scheduled-messages'
    ),
    path(
        'yelp/leads/<str:lead_id>/scheduled_messages/history/',
        ScheduledMessageHistoryList.as_view(),
        name='scheduled-messages-history'
    ),
    path(
        'yelp/leads/<str:lead_id>/scheduled_messages/<int:pk>/',
        ScheduledMessageDetail.as_view(),
        name='scheduled-message-detail'
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
    path('settings-templates/', AutoResponseSettingsTemplateListCreateView.as_view(), name='settings-template-list'),
    path('settings-templates/<int:pk>/', AutoResponseSettingsTemplateDetailView.as_view(), name='settings-template-detail'),
    path('tokens/', YelpTokenListView.as_view(), name='token-list'),
    path('tasks/', TaskLogListView.as_view(), name='task-log-list'),
    path('tasks/<str:task_id>/cancel/', TaskRevokeView.as_view(), name='task-revoke'),
    path('message_tasks/', MessageTaskListView.as_view(), name='message-task-list'),
]
