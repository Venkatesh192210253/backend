from django.urls import path
from .views import FAQListView, TicketCreateView, terms_of_service, privacy_policy

urlpatterns = [
    path('faqs/', FAQListView.as_view(), name='faq-list'),
    path('tickets/', TicketCreateView.as_view(), name='ticket-create'),
    path('terms/', terms_of_service, name='terms-of-service'),
    path('privacy/', privacy_policy, name='privacy-policy'),
]
