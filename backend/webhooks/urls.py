from django.urls import path
from .views import (
    WebhookView, EventListView, EventRetrieveView,
    yelp_auth_callback_view, save_yelp_state,
    YelpAuthInitView, YelpAuthCallbackView,
    AutoResponseSettingsView, LeadEventsProxyView, LeadIDsProxyView, LeadDetailProxyView, AttachmentProxyView, ScheduledMessageHistoryList,
    ScheduledMessageListCreate, ScheduledMessageDetail, ProcessedLeadListView, LeadDetailListAPIView,
    LeadDetailRetrieveAPIView, LeadLastEventAPIView, FollowUpTemplateListCreateView, FollowUpTemplateDestroyView,
    BusinessListView, BusinessLeadsView, BusinessEventsView,
    YelpTokenListView,
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
        'settings/auto-response/',
        AutoResponseSettingsView.as_view(),
        name='auto-response-settings'
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
    path('yelp/leads/<str:lead_id>/', LeadDetailProxyView.as_view()),
    path(
        'yelp/leads/<str:lead_id>/attachments/<str:attachment_id>/',
        AttachmentProxyView.as_view(),
        name='proxy-attachment',
    ),
    path('processed_leads/', ProcessedLeadListView.as_view(), name='processed-leads-list'),
    path('lead-details/', LeadDetailListAPIView.as_view(), name='lead-list'),
    path('lead-details/<str:lead_id>/', LeadDetailRetrieveAPIView.as_view(), name='lead-detail'),
    path('lead-events/<str:lead_id>/latest/', LeadLastEventAPIView.as_view(), name='lead-last-event'),
    path('lead-events/<str:event_id>/', LeadEventRetrieveAPIView.as_view(), name='lead-event-detail'),
    path('follow-up-templates/', FollowUpTemplateListCreateView.as_view(), name='followup-list-create'),
    path('follow-up-templates/<int:pk>/', FollowUpTemplateDestroyView.as_view(), name='followup-destroy'),
    path('tokens/', YelpTokenListView.as_view(), name='token-list'),
]
